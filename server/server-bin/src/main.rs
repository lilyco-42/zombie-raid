//! zombie-raid authoritative dedicated server — skeleton (SERVER_DEV.md §6
//! steps ②/③). Listens on WS :24565 for Godot clients, runs the 20 TPS
//! authority tick, broadcasts S2C messages as JSON (binary codec lands in
//! step ③). The ENet LAN path in net.gd stays untouched.

mod world;

use futures_util::{SinkExt, StreamExt};
use protocol::{C2S, S2C, DEFAULT_PORT};
use tokio::sync::broadcast;
use tokio_tungstenite::tungstenite::Message;

const SEED: u64 = 42; // TODO: pass via CLI arg / room config

#[tokio::main]
async fn main() {
    let (tx, _rx) = broadcast::channel::<String>(256);

    // Authority heartbeat: 20 TPS fixed tick (Minecraft-style), exactly like
    // net.gd _server_tick() on the host today.
    {
        let tx = tx.clone();
        tokio::spawn(async move {
            let mut w = world::World::new(SEED);
            let mut int = tokio::time::interval(std::time::Duration::from_millis(50));
            int.set_missed_tick_behavior(tokio::time::MissedTickBehavior::Skip);
            loop {
                int.tick().await;
                if let Some(roll) = w.tick() {
                    let msg = S2C::NetState {
                        elapsed: w.tick as f32 / 20.0,
                        frenzy: false,
                    };
                    let _ = tx.send(serde_json::to_string(&msg).unwrap());
                    println!("[tick {:>4}] spawn roll {roll}", w.tick);
                }
            }
        });
    }

    let addr = format!("0.0.0.0:{DEFAULT_PORT}");
    let listener = tokio::net::TcpListener::bind(&addr)
        .await
        .unwrap_or_else(|e| panic!("cannot bind {addr}: {e}"));
    println!("zombie-raid server on {addr} (seed {SEED}, protocol v{})", protocol::PROTOCOL_ID);

    loop {
        let (stream, peer_addr) = match listener.accept().await {
            Ok(x) => x,
            Err(e) => {
                eprintln!("accept failed: {e}");
                continue;
            }
        };
        let rx = tx.subscribe();
        tokio::spawn(handle_connection(stream, peer_addr.to_string(), rx));
    }
}

async fn handle_connection(
    stream: tokio::net::TcpStream,
    addr: String,
    mut rx: broadcast::Receiver<String>,
) {
    let ws = match tokio_tungstenite::accept_async(stream).await {
        Ok(w) => w,
        Err(e) => {
            println!("[{addr}] ws handshake failed: {e}");
            return;
        }
    };
    let (mut sink, mut stream) = ws.split();
    println!("[{addr}] connected");

    // Seed handshake first, mirroring rpc_seed: client builds nothing until
    // it knows the world seed.
    let hello = serde_json::to_string(&S2C::Seed {
        seed: SEED,
        elapsed: 0.0,
    })
    .unwrap();
    if sink.send(Message::text(hello)).await.is_err() {
        return;
    }

    loop {
        tokio::select! {
            inbound = stream.next() => match inbound {
                Some(Ok(Message::Text(t))) => match serde_json::from_str::<C2S>(&t) {
                    Ok(c2s) => println!("[{addr}] {c2s:?}"),
                    Err(e) => println!("[{addr}] bad message: {e}"),
                },
                Some(Ok(_)) => {} // binary/ping: accepted, unused in v1
                Some(Err(e)) => {
                    println!("[{addr}] read error: {e}");
                    break;
                }
                None => break,
            },
            outbound = rx.recv() => match outbound {
                Ok(line) => {
                    if sink.send(Message::text(line)).await.is_err() {
                        break;
                    }
                }
                Err(broadcast::error::RecvError::Lagged(n)) => {
                    println!("[{addr}] lagged, dropped {n} ticks");
                }
                Err(_) => break,
            },
        }
    }
    println!("[{addr}] disconnected");
}
