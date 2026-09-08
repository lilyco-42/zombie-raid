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

mod content_store;
mod player_repo;
mod world;

use futures_util::{SinkExt, StreamExt};
use protocol::{C2S, S2C, DEFAULT_PORT};
use std::sync::{Arc, Mutex};
use std::time::Duration;
use tokio::sync::broadcast;
use tokio_tungstenite::tungstenite::Message;

const SEED: u64 = 42; // TODO: pass via CLI arg / room config
/// Loopback-only admin listener (README_OPS.md T7 hot-reload).
/// Commands: `reload [dir]` | `status`, one line per connection.
const ADMIN_PORT: u16 = 24566;

#[tokio::main]
async fn main() {
    let (tx, _rx) = broadcast::channel::<S2C>(256);
    // Boot persistence (README_OPS.md T6): the player ledger survives
    // restarts. Session state stays in-memory inside World; every ledger
    // mutation is written through to SQLite.
    let repo: Arc<dyn player_repo::PlayerRepo> = {
        std::fs::create_dir_all("data").expect("create data dir");
        let db = player_repo::SqlitePlayerRepo::open("data/players.db")
            .expect("open data/players.db");
        Arc::new(db)
    };
    // Hot-reload registry (README_OPS.md T7): the World adopts whatever
    // snapshot the admin endpoint swaps in, at the next 20 TPS boundary.
    let store = Arc::new(content_store::ContentStore::new(Arc::new(
        protocol::content::ContentTables::built_in(),
    )));
    let world = Arc::new(Mutex::new(world::World::with_repo(
        SEED,
        Arc::new(protocol::content::ContentTables::built_in()),
        repo,
    )));
    world.lock().unwrap().attach_store(store.clone());

    // Admin listener: loopback only (no auth yet — never expose it).
    {
        let store = store.clone();
        tokio::spawn(async move {
            let listener = tokio::net::TcpListener::bind(("127.0.0.1", ADMIN_PORT))
                .await
                .unwrap_or_else(|e| panic!("cannot bind admin 127.0.0.1:{ADMIN_PORT}: {e}"));
            loop {
                let Ok((mut sock, _)) = listener.accept().await else { continue };
                let store = store.clone();
                tokio::spawn(async move {
                    use tokio::io::{AsyncReadExt, AsyncWriteExt};
                    let mut buf = vec![0u8; 512];
                    let n = sock.read(&mut buf).await.unwrap_or(0);
                    let cmd = String::from_utf8_lossy(&buf[..n]).trim().to_string();
                    let reply = admin_command(&cmd, &store);
                    let _ = sock.write_all(reply.as_bytes()).await;
                });
            }
        });
    }

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

/// Admin one-shot command handling (README_OPS.md T7). `reload` validates
/// the new tables BEFORE the swap; any failure keeps the current snapshot
/// serving (fail-closed).
fn admin_command(cmd: &str, store: &Arc<content_store::ContentStore>) -> String {
    if let Some(dir) = cmd.strip_prefix("reload") {
        let dir = dir.trim();
        let dir = if dir.is_empty() { "content" } else { dir };
        match content_store::load_from_dir(std::path::Path::new(dir)) {
            Ok(tables) => {
                store.swap(tables);
                format!("ok zombies={} items={}\n", store.zombie_count(), store.item_count())
            }
            Err(e) => format!("err {e}\n"),
        }
    } else if cmd == "status" {
        format!("ok zombies={} items={}\n", store.zombie_count(), store.item_count())
    } else {
        "err usage: reload [dir] | status\n".to_string()
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
    // v1 trust model: the client picks its pid; we infer this connection's
    // pid from its first state/hit report so we can clean up on disconnect.
    let mut claimed_pid: Option<u32> = None;
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
                        dispatch(c2s, &addr, &mut binary_out, &mut claimed_pid, &world, &tx)
                            .await;
                    }
                    Err(e) => println!("[{addr}] bad text message: {e}"),
                },
                Some(Ok(Message::Binary(b))) => match protocol::decode_c2s(&b) {
                    Some(c2s) => {
                        dispatch(c2s, &addr, &mut binary_out, &mut claimed_pid, &world, &tx)
                            .await;
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
    if let Some(pid) = claimed_pid {
        world.lock().unwrap().retire_player(pid);
        println!("[{addr}] retired pid {pid}");
    }
}

/// Shared inbound path: negotiate the wire upgrade, remember the
/// connection's claimed pid, hand the message to the World and broadcast
/// every reply (the Hello restart-Seed included).
async fn dispatch(
    c2s: C2S,
    addr: &str,
    binary_out: &mut bool,
    claimed_pid: &mut Option<u32>,
    world: &Arc<Mutex<world::World>>,
    tx: &broadcast::Sender<S2C>,
) {
    if let Some(c2s) = accept(c2s, addr, binary_out) {
        if claimed_pid.is_none() {
            *claimed_pid = claim_pid(&c2s);
        }
        let replies = world.lock().unwrap().handle(&c2s);
        for m in replies {
            let _ = tx.send(m);
        }
    }
}

/// A client's pid rides on its state/hit reports; the first one claims the
/// connection identity for disconnect cleanup.
fn claim_pid(c2s: &C2S) -> Option<u32> {
    match c2s {
        C2S::PlayerState { pid, .. } | C2S::HitZombie { pid, .. } => Some(*pid),
        _ => None,
    }
}

/// Inbound pre-processing: the Hello upgrade flips the wire format and
/// STILL reaches the World — once the previous raid is over, a Hello
/// restarts it with a fresh seed (World::handle_hello). All else passes
/// through untouched.
fn accept(c2s: C2S, addr: &str, binary_out: &mut bool) -> Option<C2S> {
    match c2s {
        C2S::Hello { ver } => {
            if ver >= 2 {
                *binary_out = true;
            }
            println!("[{addr}] hello ver={ver} binary_out={binary_out}");
            Some(C2S::Hello { ver })
        }
        other => {
            println!("[{addr}] {other:?}");
            Some(other)
        }
    }
}
