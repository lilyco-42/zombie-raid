//! zombie-raid authoritative dedicated server — migration steps ③+④
//! (SERVER_DEV.md §6). Listens on WS :24565 for Godot clients, runs the
//! 20 TPS authority tick and broadcasts every S2C the tick produces.
//!
//! Wire format is negotiated per connection: the handshake Seed always
//! goes out as JSON text (it precedes any inbound frame, so v1 JSON
//! clients and v2 binary clients both read it). A client Hello{ver >= 2}
//! sent as a bincode binary frame upgrades that connection's downlink to
//! bincode. Text frames stay JSON, binary frames are bincode (protocol
//! crate encode_s2c / decode_c2s).
//!
//! Wiring: one `Arc<Mutex<World>>` shared by the tick task and every
//! connection task. The broadcast channel carries S2C VALUES — each
//! connection serializes to its own format at flush time.

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
    let (tx, _rx) = broadcast::channel::<S2C>(256);
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
                    let _ = tx.send(m);
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
    tx: broadcast::Sender<S2C>,
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
    let mut binary_out = false; // flips on Hello{ver >= 2}
    println!("[{addr}] connected");

    // Seed handshake first, always as JSON text: it precedes any inbound
    // frame, so v1 JSON clients and v2 binary clients both read it.
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
                        if let Some(c2s) = accept(c2s, &addr, &mut binary_out) {
                            let replies = world.lock().unwrap().handle(&c2s);
                            for m in replies {
                                let _ = tx.send(m);
                            }
                        }
                    }
                    Err(e) => println!("[{addr}] bad text message: {e}"),
                },
                Some(Ok(Message::Binary(b))) => match protocol::decode_c2s(&b) {
                    Some(c2s) => {
                        if let Some(c2s) = accept(c2s, &addr, &mut binary_out) {
                            let replies = world.lock().unwrap().handle(&c2s);
                            for m in replies {
                                let _ = tx.send(m);
                            }
                        }
                    }
                    None => println!("[{addr}] bad binary frame ({} bytes)", b.len()),
                },
                Some(Ok(_)) => {} // ping/pong: accepted, unused
                Some(Err(e)) => {
                    println!("[{addr}] read error: {e}");
                    break;
                }
                None => break,
            },
            outbound = rx.recv() => match outbound {
                Ok(m) => {
                    let msg = if binary_out {
                        Message::binary(protocol::encode_s2c(&m))
                    } else {
                        Message::text(serde_json::to_string(&m).unwrap())
                    };
                    if sink.send(msg).await.is_err() {
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

/// Inbound pre-processing: intercept the binary upgrade handshake (Hello
/// never reaches the World) and pass everything else through.
fn accept(c2s: C2S, addr: &str, binary_out: &mut bool) -> Option<C2S> {
    match c2s {
        C2S::Hello { ver } => {
            if ver >= 2 {
                *binary_out = true;
            }
            println!("[{addr}] hello ver={ver} binary_out={binary_out}");
            None
        }
        other => {
            println!("[{addr}] {other:?}");
            Some(other)
        }
    }
}
