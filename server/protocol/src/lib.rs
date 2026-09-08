//! zombie-raid wire protocol v1 — single source of truth (docs/SERVER_DEV.md §4).
//! Each variant translates 1:1 from a net.gd rpc_* endpoint; direction,
//! frequency and reliability guarantees live in the SERVER_DEV message table.

use serde::{Deserialize, Serialize};

pub const PROTOCOL_ID: u32 = 1;
pub const DEFAULT_PORT: u16 = 24565;

/// Client -> server messages (JSON over WS for v1; bincode later).
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub enum C2S {
    /// connection handshake (joins `join_game` / answers `rpc_seed`)
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
            C2S::Hello { ver: 1 },
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
}
