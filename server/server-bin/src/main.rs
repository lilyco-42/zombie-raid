//! zombie-raid authoritative dedicated server — migration step ③
//! (SERVER_DEV.md §6). Listens on WS :24565 for Godot clients, runs the
//! 20 TPS authority tick and broadcasts every S2C the tick produces as
//! JSON. The ENet LAN path in net.gd stays untouched.
//!
//! Wiring: one `Arc<Mutex<World>>` shared by the tick task and every
//! connection task. Tick task: World::tick(0.05) -> serialize Vec<S2C> ->
//! broadcast channel. Connection task: inbound C2S -> World::handle ->
//! broadcast the replies; outbound -> forward channel lines to the socket.

mod world;

use futures_util::{SinkExt, StreamExt};
use protocol::{C2S, S2C, DEFAULT_PORT};
use std::sync::{Arc, Mutex};
use std::time::Duration;
use tokio::sync::broadcast;
use tokio_tungstenite::tungstenite::Message;

const SEED: u64 = 42; // TODO: pass via CLI arg / room config

#[tokio::main]
async fn main() {
    let (tx, _rx) = broadcast::channel::<String>(256);
    let world = Arc::new(Mutex::new(world::World::new(SEED)));

    // Authority heartbeat: 20 TPS fixed tick (Minecraft-style), exactly like
    // net.gd _server_tick() on the host today.
    {
        let tx = tx.clone();
        let world = Arc::clone(&world);
        tokio::spawn(async move {
            let mut int = tokio::time::interval(Duration::from_millis(50));
            int.set_missed_tick_behavior(tokio::time::MissedTickBehavior::Skip);
            loop {
                int.tick().await;
                let msgs = world.lock().unwrap().tick(1.0 / world::TICK_HZ);
                for m in msgs {
                    let _ = tx.send(serde_json::to_string(&m).unwrap());
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
        let tx = tx.clone();
        let world = Arc::clone(&world);
        tokio::spawn(handle_connection(stream, peer_addr.to_string(), tx, world));
    }
}

async fn handle_connection(
    stream: tokio::net::TcpStream,
    addr: String,
    tx: broadcast::Sender<String>,
    world: Arc<Mutex<world::World>>,
) {
    let ws = match tokio_tungstenite::accept_async(stream).await {
        Ok(w) => w,
        Err(e) => {
            println!("[{addr}] ws handshake failed: {e}");
            return;
        }
    };
    let (mut sink, mut stream) = ws.split();
    let mut rx = tx.subscribe();
    println!("[{addr}] connected");

    // Seed handshake first, mirroring rpc_seed: the client builds nothing
    // until it knows the world seed, and late joiners restore the clock.
    let seed = {
        let w = world.lock().unwrap();
        S2C::Seed {
            seed: SEED,
            elapsed: w.elapsed,
        }
    };
    let hello = serde_json::to_string(&seed).unwrap();
    if sink.send(Message::text(hello)).await.is_err() {
        return;
    }

    loop {
        tokio::select! {
            inbound = stream.next() => match inbound {
                Some(Ok(Message::Text(t))) => match serde_json::from_str::<C2S>(&t) {
                    Ok(c2s) => {
                        println!("[{addr}] {c2s:?}");
                        let replies = world.lock().unwrap().handle(&c2s);
                        for m in replies {
                            let _ = tx.send(serde_json::to_string(&m).unwrap());
                        }
                    }
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
