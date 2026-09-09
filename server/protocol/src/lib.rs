//! zombie-raid wire protocol — single source of truth (docs/SERVER_DEV.md §4).
//! Each variant translates 1:1 from a net.gd rpc_* endpoint; direction,
//! frequency and reliability guarantees live in the SERVER_DEV message table.
//!
//! Two wire formats share these enums:
//! - v1 JSON (serde externally-tagged; unit variants serialize as bare strings)
//! - v2 bincode legacy over WS binary frames, negotiated per connection with
//!   Hello{ver:2}. The layout is frozen by the golden-byte tests below and
//!   mirrored by the GDScript encoder `game/scripts/net_codec.gd`.

use serde::{Deserialize, Serialize};

pub mod content;

pub const PROTOCOL_ID: u32 = 2;
pub const DEFAULT_PORT: u16 = 24565;

/// Client -> server messages.
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub enum C2S {
    /// connection handshake (joins `join_game` / answers `rpc_seed`).
    /// ver >= 2 (sent as a binary frame) upgrades the connection downlink
    /// to bincode; the server never forwards Hello to the World.
    Hello { ver: u32 },
    /// 15Hz unreliable — was `rpc_player_state`
    PlayerState {
        pid: u32,
        pos: [f32; 3],
        yaw: f32,
        speed: f32,
        on_floor: bool,
        crouch: bool,
    },
    /// was `rpc_hit_zombie` (server validates rate/damage/range; `pid`
    /// declares the shooter so the server can attach its last reported
    /// position — v1 trust model, netcode auth lands later)
    HitZombie { pid: u32, net_id: u32, dmg: f32 },
    /// was `rpc_box_taken` (claim by position, first taker wins)
    BoxTaken { pos: [f32; 3] },
    /// was `rpc_report_extract`
    ReportExtract { in_zone: bool },
    /// was `rpc_report_player_died` (any death fails the raid for the team)
    ReportPlayerDied,
    // ---- shop / inventory (README_OPS.md T5; server-authoritative ledger) --
    /// Shop: buy one unit of `item_id` at its content-table price. The
    /// server keeps the session coin ledger (drop credits + purchases);
    /// clients only display what InventoryUpdate broadcasts.
    BuyItem { pid: u32, item_id: String },
    /// Ask for the shop listing -> S2C::ShopList.
    RequestShop,
    // ---- account identity (README_OPS.md T9; docs/CLIENT_API.md §账号) -----
    /// Device-token sign-in (passwordless accounts, commerce MVP). Sent
    /// any time after Hello; the server finds or creates the player row,
    /// binds this connection's pid to the uid, merges the persisted
    /// ledger into the session and answers AuthOk{uid,name,coins} or
    /// AuthErr{reason}. `token` = client-generated stable GUID. `pid`
    /// rides on the message like every other C2S (v1 trust model).
    Auth { pid: u32, token: String },
    /// Full inventory dump for the signed-in account (bag/warehouse page).
    /// Requires a prior Auth on this connection. `pid` rides on the
    /// message like every other C2S (v1 trust model).
    RequestInventory { pid: u32 },
}

/// Server -> client messages.
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub enum S2C {
    /// world seed handshake — was `rpc_seed`
    Seed { seed: u64, elapsed: f32 },
    /// 15Hz unreliable snapshot — was `rpc_zombie_states`
    /// (ENet path packs this as `[seq, id,x,y,z,yaw,anim,type] * N` floats)
    ZombieStates { seq: u32, ents: Vec<ZombieEnt> },
    /// 1Hz clock — was `rpc_net_state`
    NetState { elapsed: f32, frenzy: bool },
    /// was `rpc_raid_started`
    RaidStarted,
    /// was `rpc_zombie_dead`
    ZombieDead {
        net_id: u32,
        pos: [f32; 3],
        drop_value: i32,
    },
    /// was `rpc_remove_box`
    RemoveBox { pos: [f32; 3] },
    /// was `rpc_extract_success`
    ExtractSuccess,
    /// was `rpc_raid_failed`
    RaidFailed,
    /// was `rpc_damage_player` — `pid` names the target so a broadcast
    /// channel stays safe (client ignores reports for other pids)
    DamagePlayer { pid: u32, dmg: f32 },
    // ---- shop / inventory (README_OPS.md T5) -------------------------------
    /// Shop listing (purchasable, non-deprecated items only):
    /// Vec<(item_id, price)>. Low frequency (on RequestShop / content swap).
    ShopList { entries: Vec<(String, u32)> },
    /// Server-authoritative inventory snapshot for one (pid, item) pair;
    /// the client replaces its local count for that id.
    InventoryUpdate { pid: u32, item_id: String, count: i64 },
    /// Purchase rejected — `reason` is operator-readable, shop UI shows it.
    TradeError { pid: u32, reason: String },
    // ---- account identity (README_OPS.md T9) -------------------------------
    /// Sign-in succeeded: uid is stable across sessions (the ledger key),
    /// `name` is operator-readable (auto "survivor#NNNN" in v1), coins is
    /// the persisted balance at sign-in time. InventoryUpdate/TradeError
    /// frames keep using the connection pid; the mapping lives server-side.
    AuthOk { uid: u32, name: String, coins: i64 },
    /// Sign-in rejected (malformed/empty token). The connection stays
    /// usable unauthenticated (raid works, ledger stays session-only).
    AuthErr { reason: String },
    /// Full account inventory — the bag/warehouse page data source.
    /// Vec<(item_id, count)>; counts are i64 (negative impossible here).
    InventorySnapshot { entries: Vec<(String, i64)> },
}

/// One zombie in the 15Hz snapshot.
#[derive(Serialize, Deserialize, Debug, Clone, Copy, PartialEq)]
pub struct ZombieEnt {
    pub id: u32,
    pub pos: [f32; 3],
    pub yaw: f32,
    /// 1=idle 2=run 4=attack (matches zombie.gd anim codes)
    pub anim: u8,
    /// 0..2 = Runner/Walker/Brute, 3 = Spitter
    pub ztype: u8,
}

/// Serialize a server->client message to bincode (wire format v2).
pub fn encode_s2c(msg: &S2C) -> Vec<u8> {
    bincode::serialize(msg).expect("S2C is infallibly serializable")
}

/// Deserialize a client->server binary frame (wire format v2).
/// Returns None on malformed/out-of-range frames (logged by the caller).
pub fn decode_c2s(bytes: &[u8]) -> Option<C2S> {
    bincode::deserialize(bytes).ok()
}

/// Deterministic 64-bit LCG shared with the GDScript side
/// (`tests/test_lcg.gd`). The state update is mul+add only — signed int64
/// wrap (GDScript) equals wrapping u64 ops (Rust) bit-for-bit; the output
/// is shift+mask, so the arithmetic-vs-logical shift difference cancels.
pub struct Lcg64 {
    state: u64,
}

impl Lcg64 {
    pub fn new(seed: u64) -> Self {
        Self { state: seed }
    }

    /// 31-bit output in `[0, 2^31)`.
    pub fn next_u31(&mut self) -> u32 {
        self.state = self
            .state
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        ((self.state >> 33) & 0x7FFF_FFFF) as u32
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn lcg_matches_gdscript_vectors() {
        // Independent reference (python wrap64). tests/test_lcg.gd must
        // produce the identical sequence for seed 42.
        let want: [u32; 8] = [
            1220265334, 484179026, 886563538, 1353769503, 1460606294, 56326156, 46730969,
            327394710,
        ];
        let mut rng = Lcg64::new(42);
        for w in want {
            assert_eq!(rng.next_u31(), w);
        }
    }

    #[test]
    fn c2s_roundtrip_json_and_bincode() {
        let msgs = vec![
            C2S::Hello { ver: 2 },
            C2S::PlayerState {
                pid: 2,
                pos: [1.5, 0.0, -3.25],
                yaw: 0.7,
                speed: 4.2,
                on_floor: true,
                crouch: false,
            },
            C2S::HitZombie {
                pid: 2,
                net_id: 9,
                dmg: 34.5,
            },
            C2S::BoxTaken { pos: [0.0, 1.0, 2.0] },
            C2S::ReportExtract { in_zone: true },
            C2S::ReportPlayerDied,
        ];
        for m in msgs {
            let j = serde_json::to_string(&m).unwrap();
            assert_eq!(serde_json::from_str::<C2S>(&j).unwrap(), m);
            let b = bincode::serialize(&m).unwrap();
            assert_eq!(bincode::deserialize::<C2S>(&b).unwrap(), m);
        }
    }

    #[test]
    fn s2c_roundtrip_json_and_bincode() {
        let msgs = vec![
            S2C::Seed {
                seed: 42,
                elapsed: 12.5,
            },
            S2C::ZombieStates {
                seq: 7,
                ents: vec![ZombieEnt {
                    id: 3,
                    pos: [1.0, 2.0, 3.0],
                    yaw: 1.57,
                    anim: 2,
                    ztype: 1,
                }],
            },
            S2C::NetState {
                elapsed: 60.0,
                frenzy: true,
            },
            S2C::RaidStarted,
            S2C::ZombieDead {
                net_id: 3,
                pos: [1.0, 2.0, 3.0],
                drop_value: 15,
            },
            S2C::RemoveBox { pos: [4.0, 0.0, 5.0] },
            S2C::ExtractSuccess,
            S2C::RaidFailed,
            S2C::DamagePlayer { pid: 2, dmg: 12.0 },
        ];
        for m in msgs {
            let j = serde_json::to_string(&m).unwrap();
            assert_eq!(serde_json::from_str::<S2C>(&j).unwrap(), m);
            let b = bincode::serialize(&m).unwrap();
            assert_eq!(bincode::deserialize::<S2C>(&b).unwrap(), m);
        }
    }

    #[test]
    fn full_snapshot_fits_mtu_budget() {
        // 14 entities at ~15Hz must stay well inside a datagram-sized frame.
        let snap = S2C::ZombieStates {
            seq: 1,
            ents: vec![
                ZombieEnt {
                    id: 0,
                    pos: [0.0; 3],
                    yaw: 0.0,
                    anim: 1,
                    ztype: 0,
                };
                14
            ],
        };
        let bytes = bincode::serialize(&snap).unwrap();
        assert!(bytes.len() < 1200, "snapshot too big: {} bytes", bytes.len());
    }

    // --------------------------------------------------------------- //
    // Golden bytes — computed with python struct.pack and mirrored by   //
    // tests/test_ws_codec.gd section F. These pin the cross-language    //
    // bincode legacy layout: little-endian, u32 enum discriminants,     //
    // u64 vec lengths, 1-byte bools, 4-byte f32s, no struct padding.    //
    // ----------------------------------------------------------------- //

    #[test]
    fn golden_hit_zombie_bytes() {
        // C2S variant 2, pid 2, net_id 9, dmg 34.5 (0x420A0000)
        let b = bincode::serialize(&C2S::HitZombie { pid: 2, net_id: 9, dmg: 34.5 }).unwrap();
        assert_eq!(
            b,
            vec![0x02, 0, 0, 0, 0x02, 0, 0, 0, 0x09, 0, 0, 0, 0x00, 0x00, 0x0a, 0x42]
        );
        // ...and the exact same bytes round-trip back through decode_c2s.
        assert_eq!(
            decode_c2s(&[
                0x02, 0, 0, 0, 0x02, 0, 0, 0, 0x09, 0, 0, 0, 0x00, 0x00, 0x0a, 0x42
            ]),
            Some(C2S::HitZombie {
                pid: 2,
                net_id: 9,
                dmg: 34.5
            })
        );
    }

    #[test]
    fn golden_player_state_bytes() {
        // C2S variant 1, pid 7, pos [1.5,0,-3.25], yaw 0.7, speed 4.2,
        // on_floor true (0x01), crouch false (0x00) — 30 bytes.
        let b = bincode::serialize(&C2S::PlayerState {
            pid: 7,
            pos: [1.5, 0.0, -3.25],
            yaw: 0.7,
            speed: 4.2,
            on_floor: true,
            crouch: false,
        })
        .unwrap();
        assert_eq!(
            b,
            vec![
                0x01, 0, 0, 0, 0x07, 0, 0, 0, // variant + pid
                0x00, 0x00, 0xc0, 0x3f, // 1.5f32
                0x00, 0x00, 0x00, 0x00, // 0.0f32
                0x00, 0x00, 0x50, 0xc0, // -3.25f32
                0x33, 0x33, 0x33, 0x3f, // 0.7f32
                0x66, 0x66, 0x86, 0x40, // 4.2f32
                0x01, 0x00, // on_floor, crouch
            ]
        );
    }

    #[test]
    fn golden_zombie_states_bytes() {
        // S2C variant 1, seq 7, vec len 1 (u64), one ent {id 3,
        // pos [1,2,3], yaw 1.57, anim 2, ztype 1} — 38 bytes.
        let snap = S2C::ZombieStates {
            seq: 7,
            ents: vec![ZombieEnt {
                id: 3,
                pos: [1.0, 2.0, 3.0],
                yaw: 1.57,
                anim: 2,
                ztype: 1,
            }],
        };
        let b = encode_s2c(&snap);
        assert_eq!(
            b,
            vec![
                0x01, 0, 0, 0, 0x07, 0, 0, 0, // variant + seq
                0x01, 0, 0, 0, 0, 0, 0, 0, // vec length u64 = 1
                0x03, 0, 0, 0, // ent.id
                0x00, 0x00, 0x80, 0x3f, // 1.0f32
                0x00, 0x00, 0x00, 0x40, // 2.0f32
                0x00, 0x00, 0x40, 0x40, // 3.0f32
                0xc3, 0xf5, 0xc8, 0x3f, // 1.57f32
                0x02, 0x01, // anim, ztype
            ]
        );
        assert_eq!(decode_c2s(&[0xff, 0xff, 0xff, 0xff]), None); // variant 4294967295
    }

    #[test]
    fn golden_raid_failed_bytes() {
        // Unit variant: discriminant only, no payload — 4 bytes.
        assert_eq!(encode_s2c(&S2C::RaidFailed), vec![0x07, 0, 0, 0]);
    }
}


#[cfg(test)]
mod shop_golden_tests {
    //! T5 golden bytes (README_OPS.md): bincode legacy - u32 LE
    //! discriminants, u64 LE string lengths, UTF-8 bodies. Reference values
    //! computed with python struct.pack; mirrored by game/scripts/net_codec.gd
    //! tests F8-F12. Variants 6/7 (C2S) and 9/10/11 (S2C) are APPEND-ONLY.

    use super::*;

    #[test]
    fn golden_buy_item_bytes() {
        let msg = C2S::BuyItem { pid: 357, item_id: "bandage".into() };
        let bytes = bincode::serialize(&msg).unwrap();
        assert_eq!(
            bytes,
            vec![0x06, 0, 0, 0, 0x65, 0x01, 0, 0,
                 0x07, 0, 0, 0, 0, 0, 0, 0,
                 0x62, 0x61, 0x6e, 0x64, 0x61, 0x67, 0x65],
            "buy pid=357 'bandage' = 23 bytes"
        );
        assert_eq!(bincode::deserialize::<C2S>(&bytes).unwrap(), msg);
    }

    #[test]
    fn golden_request_shop_bytes() {
        assert_eq!(bincode::serialize(&C2S::RequestShop).unwrap(), vec![0x07, 0, 0, 0]);
    }

    #[test]
    fn golden_shop_list_bytes() {
        let msg = S2C::ShopList { entries: vec![("bandage".into(), 120u32)] };
        let bytes = bincode::serialize(&msg).unwrap();
        assert_eq!(
            bytes,
            vec![0x09, 0, 0, 0,
                 0x01, 0, 0, 0, 0, 0, 0, 0,
                 0x07, 0, 0, 0, 0, 0, 0, 0,
                 0x62, 0x61, 0x6e, 0x64, 0x61, 0x67, 0x65,
                 0x78, 0, 0, 0],
            "one entry ('bandage',120) = 31 bytes"
        );
    }

    #[test]
    fn golden_inventory_update_bytes() {
        let msg = S2C::InventoryUpdate { pid: 357, item_id: "coin".into(), count: 1250 };
        let bytes = bincode::serialize(&msg).unwrap();
        assert_eq!(
            bytes,
            vec![0x0a, 0, 0, 0, 0x65, 0x01, 0, 0,
                 0x04, 0, 0, 0, 0, 0, 0, 0,
                 0x63, 0x6f, 0x69, 0x6e,
                 0xe2, 0x04, 0, 0, 0, 0, 0, 0],
            "coin balance 1250 = 28 bytes"
        );
        assert_eq!(bincode::deserialize::<S2C>(&bytes).unwrap(), msg);
    }

    #[test]
    fn golden_trade_error_bytes() {
        let msg = S2C::TradeError { pid: 357, reason: "insufficient coins".into() };
        let bytes = bincode::serialize(&msg).unwrap();
        assert_eq!(
            bytes,
            vec![0x0b, 0, 0, 0, 0x65, 0x01, 0, 0,
                 0x12, 0, 0, 0, 0, 0, 0, 0,
                 0x69, 0x6e, 0x73, 0x75, 0x66, 0x66, 0x69, 0x63, 0x69, 0x65,
                 0x6e, 0x74, 0x20, 0x63, 0x6f, 0x69, 0x6e, 0x73],
            "34 bytes"
        );
        assert_eq!(bincode::deserialize::<S2C>(&bytes).unwrap(), msg);
    }

    // ---- account identity golden bytes (README_OPS.md T9) ------------------

    #[test]
    fn golden_auth_bytes() {
        let msg = C2S::Auth { pid: 357, token: "abc12345".into() };
        let bytes = bincode::serialize(&msg).unwrap();
        assert_eq!(
            bytes,
            vec![0x08, 0, 0, 0, 0x65, 0x01, 0, 0,
                 0x08, 0, 0, 0, 0, 0, 0, 0,
                 0x61, 0x62, 0x63, 0x31, 0x32, 0x33, 0x34, 0x35],
            "auth pid=357 token 'abc12345' = 24 bytes"
        );
        assert_eq!(bincode::deserialize::<C2S>(&bytes).unwrap(), msg);
    }

    #[test]
    fn golden_request_inventory_bytes() {
        let msg = C2S::RequestInventory { pid: 357 };
        let bytes = bincode::serialize(&msg).unwrap();
        assert_eq!(bytes, vec![0x09, 0, 0, 0, 0x65, 0x01, 0, 0], "8 bytes");
        assert_eq!(bincode::deserialize::<C2S>(&bytes).unwrap(), msg);
    }

    #[test]
    fn golden_auth_ok_bytes() {
        let msg = S2C::AuthOk { uid: 1, name: "survivor#0001".into(), coins: 1250 };
        let bytes = bincode::serialize(&msg).unwrap();
        assert_eq!(
            bytes,
            vec![0x0c, 0, 0, 0, 0x01, 0, 0, 0,
                 0x0d, 0, 0, 0, 0, 0, 0, 0,
                 0x73, 0x75, 0x72, 0x76, 0x69, 0x76, 0x6f, 0x72,
                 0x23, 0x30, 0x30, 0x30, 0x31,
                 0xe2, 0x04, 0, 0, 0, 0, 0, 0],
            "uid=1 name='survivor#0001' coins=1250 = 37 bytes"
        );
        assert_eq!(bincode::deserialize::<S2C>(&bytes).unwrap(), msg);
    }

    #[test]
    fn golden_auth_err_bytes() {
        let msg = S2C::AuthErr { reason: "invalid token".into() };
        let bytes = bincode::serialize(&msg).unwrap();
        assert_eq!(
            bytes,
            vec![0x0d, 0, 0, 0,
                 0x0d, 0, 0, 0, 0, 0, 0, 0,
                 0x69, 0x6e, 0x76, 0x61, 0x6c, 0x69, 0x64, 0x20,
                 0x74, 0x6f, 0x6b, 0x65, 0x6e],
            "25 bytes"
        );
        assert_eq!(bincode::deserialize::<S2C>(&bytes).unwrap(), msg);
    }

    #[test]
    fn golden_inventory_snapshot_bytes() {
        let msg = S2C::InventorySnapshot {
            entries: vec![("coin".into(), 1250), ("bandage".into(), 2)],
        };
        let bytes = bincode::serialize(&msg).unwrap();
        assert_eq!(
            bytes,
            vec![0x0e, 0, 0, 0,
                 0x02, 0, 0, 0, 0, 0, 0, 0,
                 0x04, 0, 0, 0, 0, 0, 0, 0, 0x63, 0x6f, 0x69, 0x6e,
                 0xe2, 0x04, 0, 0, 0, 0, 0, 0,
                 0x07, 0, 0, 0, 0, 0, 0, 0, 0x62, 0x61, 0x6e, 0x64,
                 0x61, 0x67, 0x65,
                 0x02, 0, 0, 0, 0, 0, 0, 0],
            "two entries ('coin',1250) ('bandage',2) = 47 bytes"
        );
        assert_eq!(bincode::deserialize::<S2C>(&bytes).unwrap(), msg);
    }
}
