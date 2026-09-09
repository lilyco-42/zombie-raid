//! Authoritative world state — migration step ③ (SERVER_DEV.md §6).
//! Zombie AI, spawning, hit validation and the raid clock migrate here
//! from `zombie.gd` / `raid_manager.gd` / `net.gd`; presentation (models,
//! animations, sounds) stays on the client, which only replays snapshots.
//!
//! Fidelity contract: every constant below is copied from the game source
//! (file + value in the comment). Same seed -> same spawn sequence; random
//! decisions consume the shared LCG64 so tests can pin them exactly.
//!
//! v1 reductions (documented, harmless to clients):
//! - straight-line steering instead of navmesh paths (zombie.gd already
//!   falls back to this when the navmesh never baked);
//! - no WANDER: idle when no player within DEAGGRO_RANGE;
//! - loot boxes are relayed, not tracked (RemoveBox passthrough);
//! - pid is trusted from the message (netcode auth lands in a later step).

use protocol::content::ContentTables;
use protocol::{Lcg64, S2C};
use std::collections::HashMap;

use crate::player_repo::PlayerRepo;

// ---- pace constants (raid_manager.gd) -----------------------------------
pub const SPAWN_INTERVAL_START: f32 = 5.0;
pub const SPAWN_INTERVAL_END: f32 = 2.2;
pub const MAX_ALIVE_START: f32 = 6.0;
pub const MAX_ALIVE_END: f32 = 14.0;
pub const RAMP_SECONDS: f32 = 360.0;
pub const MIN_SPAWN_DIST: f32 = 18.0;
pub const RUN_LIMIT: f32 = 480.0; // seconds until the moon leaves -> frenzy
pub const FRENZY_GRACE: f32 = 90.0; // after RUN_LIMIT the run is lost
/// Signup bonus for a brand-new account (README_OPS.md T9 onboarding
/// economy): enough to buy the cheapest purchasable item immediately.
pub const SIGNUP_BONUS: i64 = 200;

// ---- hit validation (net.gd MAX_HIT_*) ----------------------------------
pub const MAX_HIT_RATE: f32 = 20.0;
pub const MAX_HIT_DAMAGE: f32 = 80.0;
pub const MAX_HIT_RANGE: f32 = 80.0;

// ---- zombie senses & melee (zombie.gd) ----------------------------------
pub const AGGRO_RANGE: f32 = 20.0;
pub const DEAGGRO_RANGE: f32 = 34.0;
pub const ATTACK_RANGE: f32 = 2.0;
pub const ATTACK_LAND_RANGE: f32 = ATTACK_RANGE + 0.6; // mid-swing grace
pub const ATTACK_COOLDOWN: f32 = 1.3;
pub const ATTACK_HIT_DELAY: f32 = 0.4;

pub const TICK_HZ: f32 = 20.0;
/// Snapshot accumulator mirrors net.gd `_server_tick` exactly (reset-to-zero
/// on fire), which paces one snapshot every 2 ticks at 20 TPS.
const SNAPSHOT_DT: f32 = 1.0 / 15.0;
const TICK_DT: f32 = 1.0 / TICK_HZ;

/// Per-type stats: (walk, run, max_hp, damage). Indices 0..2 = raid_manager
/// VARIANTS (Runner/Walker/Brute), 3 = spitter (_make_spitter).
pub fn ztype_stats(ztype: u8) -> (f32, f32, f32, f32) {
    match ztype {
        0 => (2.2, 5.4, 40.0, 10.0),
        1 => (1.7, 4.0, 60.0, 15.0),
        2 => (1.3, 3.1, 150.0, 26.0),
        _ => (1.3, 3.4, 45.0, 12.0),
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct Zombie {
    pub id: u32,
    pub pos: [f32; 3],
    pub yaw: f32,
    pub ztype: u8,
    pub hp: f32,
    /// seconds until the next swing may start (also the ATTACK anim window)
    pub attack_cd: f32,
    /// Some((target_pid, t)) — mid-swing damage check lands when t hits 0
    pub hit_pending: Option<(u32, f32)>,
    pub moving: bool,
}

pub struct World {
    pub seed: u64,
    pub tick: u64,
    /// raid clock — public so tests can fast-forward and the server can
    /// hand it to late joiners in the Seed handshake
    pub elapsed: f32,
    pub raid_active: bool,
    rng: Lcg64,
    zombies: Vec<Zombie>,
    next_id: u32,
    players: HashMap<u32, [f32; 3]>,
    hit_times: HashMap<u32, f32>,
    snap_acc: f32,
    snap_seq: u32,
    spawn_acc: f32,
    netstate_acc: f32,
    /// Content tables (zombie kinds / items / raid rules). Boots on the
    /// built-in set; hot-reload swaps the Arc (see README_OPS.md T7).
    pub content: std::sync::Arc<ContentTables>,
    /// Server-authoritative session ledger: pid -> item_id -> count.
    /// Drop credits and purchases land here; every mutation is also
    /// written through to `repo` when one is attached (T6, main.rs).
    inventory: HashMap<u32, HashMap<String, i64>>,
    /// Connection pid -> account uid (README_OPS.md T9). Unauthenticated
    /// pids have no entry and their ledger stays session-only (repo keys
    /// fall back to the raw pid). Survives raid resets: the mapping is a
    /// property of the connection, not of the raid.
    session_uid: HashMap<u32, u32>,
    /// Persistence seam (README_OPS.md T6). None in most unit tests
    /// (in-memory ledger only); main.rs attaches a SQLite repo.
    pub repo: Option<std::sync::Arc<dyn PlayerRepo>>,
    /// Hot-reload registry (README_OPS.md T7). None in most unit tests
    /// (content snapshot stays fixed); main.rs attaches the store whose
    /// admin endpoint swaps the snapshot mid-raid.
    store: Option<std::sync::Arc<crate::content_store::ContentStore>>,
}

impl World {
    pub fn new(seed: u64) -> Self {
        Self::with_content(seed, std::sync::Arc::new(ContentTables::built_in()))
    }

    /// Boot the world on an explicit content snapshot (hot-reload path).
    pub fn with_content(seed: u64, content: std::sync::Arc<ContentTables>) -> Self {
        Self::base(seed, content, None)
    }

    /// Boot with a persistence backend attached (README_OPS.md T6).
    pub fn with_repo(
        seed: u64,
        content: std::sync::Arc<ContentTables>,
        repo: std::sync::Arc<dyn PlayerRepo>,
    ) -> Self {
        Self::base(seed, content, Some(repo))
    }

    fn base(
        seed: u64,
        content: std::sync::Arc<ContentTables>,
        repo: Option<std::sync::Arc<dyn PlayerRepo>>,
    ) -> Self {
        Self {
            seed,
            tick: 0,
            elapsed: 0.0,
            raid_active: true, // the dedicated server boots into a live raid
            rng: Lcg64::new(seed),
            zombies: Vec::new(),
            next_id: 1,
            players: HashMap::new(),
            hit_times: HashMap::new(),
            snap_acc: 0.0,
            snap_seq: 0,
            spawn_acc: 0.0,
            netstate_acc: 0.0,
            content,
            inventory: HashMap::new(),
            session_uid: HashMap::new(),
            repo,
            store: None,
        }
    }

    /// Attach the hot-reload registry (README_OPS.md T7). Once attached,
    /// every tick() pulls the store's current snapshot first, so an
    /// admin swap takes effect at the next 20 TPS boundary — no restart.
    pub fn attach_store(&mut self, store: std::sync::Arc<crate::content_store::ContentStore>) {
        self.store = Some(store);
    }

    // ------------------------------------------------------- inspection --
    pub fn zombies(&self) -> &[Zombie] {
        &self.zombies
    }

    /// Per-kind stats from the content tables; unknown ids fall back to
    /// the legacy spitter row (the former `_ =>` arm) so snapshots in
    /// flight survive a table swap mid-raid.
    fn zstats(&self, ztype: u8) -> (f32, f32, f32, f32) {
        match self.content.zombie(ztype) {
            Some(z) => (z.walk, z.run, z.max_hp, z.damage),
            None => ztype_stats(ztype),
        }
    }

    pub fn player_count(&self) -> usize {
        self.players.len()
    }

    // -------------------------------------------------------- lifecycle --
    /// Fresh seed for the next raid: LCG output xor'd with the elapsed
    /// clock's bit pattern. Two raids never end at the exact same f32, so
    /// this differentiates rounds even with the fixed boot seed (v1 has no
    /// CLI seed arg yet). Pure function -> unit-testable.
    fn next_seed(&mut self) -> u64 {
        (self.rng.next_u31() as u64) ^ ((self.elapsed.to_bits() as u64) << 1)
    }

    /// Wipe every raid-local field and reseed. `*self = Self::new(..)` keeps
    /// the reset exhaustive by construction: add a field to World and the
    /// compiler makes you decide whether Self::new resets it.
    pub fn reset(&mut self, seed: u64) {
        let repo = self.repo.take();
        let store = self.store.take();
        let session_uid = std::mem::take(&mut self.session_uid);
        *self = Self::with_content(seed, self.content.clone());
        self.repo = repo; // persistence outlives raids (ledger is not session state)
        self.store = store; // hot-reload registry outlives raids too
        self.session_uid = session_uid; // identity is per-connection, not per-raid
    }

    /// Hello handler. A Hello during a live raid is a no-op (the Seed
    /// handshake in main.rs already restored the joiner's clock). A Hello
    /// once the previous raid is OVER starts the next one: reset with a
    /// fresh seed and broadcast the new Seed so every connected client
    /// (including stale ones from the finished raid) rebuilds — net.gd's
    /// rpc_seed reloads the scene whenever raid_seed changes.
    pub fn handle_hello(&mut self) -> Vec<S2C> {
        if self.raid_active {
            return vec![];
        }
        let seed = self.next_seed();
        self.reset(seed);
        vec![S2C::Seed {
            seed,
            elapsed: 0.0,
        }]
    }

    // ------------------------------------------------------ inputs (C2S) --
    pub fn player_state(&mut self, pid: u32, pos: [f32; 3]) {
        self.players.insert(pid, pos);
    }

    /// Disconnect cleanup: the connection task infers this peer's pid from
    /// its first reported state/hit and hands it over on close. Drops the
    /// position (zombies stop chasing the ghost) and the hit-rate clock.
    /// The ledger's currency: the first non-deprecated `currency` item.
    fn coin_id(&self) -> &str {
        self.content
            .items
            .iter()
            .find(|i| i.kind == "currency" && !i.deprecated)
            .map(|i| i.id.as_str())
            .unwrap_or("coin")
    }

    fn balance(&self, pid: u32, item_id: &str) -> i64 {
        self.inventory
            .get(&pid)
            .and_then(|bag| bag.get(item_id))
            .copied()
            .unwrap_or(0)
    }

    fn add_item(&mut self, pid: u32, item_id: &str, delta: i64) {
        let bag = self.inventory.entry(pid).or_default();
        *bag.entry(item_id.to_string()).or_insert(0) += delta;
        if bag.get(item_id).copied().unwrap_or(0) <= 0 {
            bag.remove(item_id);
        }
        // Write-through (README_OPS.md T6): the ledger must not vanish
        // with the session (invariant 5 — sessions are droppable, the
        // ledger is not). Authenticated connections key the repo by their
        // stable uid (T9); anonymous ones keep the raw pid (session noise,
        // never promoted to an account).
        if let Some(repo) = &self.repo {
            let key = self.session_uid.get(&pid).copied().unwrap_or(pid);
            repo.add_item(key, item_id, delta);
        }
    }

    /// Repo-side ledger key for `pid` (uid when authenticated, else pid).
    fn ledger_key(&self, pid: u32) -> u32 {
        self.session_uid.get(&pid).copied().unwrap_or(pid)
    }

    /// C2S::BuyItem - server-authoritative purchase (README_OPS.md T5).
    /// Every failure mode answers TradeError so the shop UI can react.
    fn buy_item(&mut self, pid: u32, item_id: &str) -> Vec<S2C> {
        if !self.raid_active {
            return vec![S2C::TradeError { pid, reason: "raid is over".into() }];
        }
        let Some(def) = self.content.item(item_id) else {
            return vec![S2C::TradeError {
                pid,
                reason: format!("unknown item '{item_id}'"),
            }];
        };
        if !def.shop.purchasable {
            return vec![S2C::TradeError { pid, reason: "not for sale".into() }];
        }
        let coin = self.coin_id().to_string();
        let price = def.shop.price as i64;
        let coins_before = self.balance(pid, &coin);
        if coins_before < price {
            return vec![S2C::TradeError { pid, reason: "insufficient coins".into() }];
        }
        self.add_item(pid, &coin, -price);
        self.add_item(pid, item_id, 1);
        // audit trail (README_OPS.md T6): every accepted trade lands in
        // purchases so dup-exploit forensics stay answerable in year 10
        if let Some(repo) = &self.repo {
            repo.record_purchase(self.ledger_key(pid), item_id, price, coins_before);
        }
        let coin_bal = self.balance(pid, &coin);
        let bought = self.balance(pid, item_id);
        vec![
            S2C::InventoryUpdate { pid, item_id: coin, count: coin_bal },
            S2C::InventoryUpdate { pid, item_id: item_id.to_string(), count: bought },
        ]
    }

    /// C2S::RequestShop - purchasable, non-deprecated items only.
    fn shop_list(&mut self) -> Vec<S2C> {
        let entries: Vec<(String, u32)> = self
            .content
            .items
            .iter()
            .filter(|i| i.shop.purchasable && !i.deprecated)
            .map(|i| (i.id.clone(), i.shop.price))
            .collect();
        vec![S2C::ShopList { entries }]
    }

    // ------------------------------------------------- account (T9/T10) --
    /// C2S::Auth - device-token sign-in. Finds or creates the account
    /// row, binds pid -> uid, merges the persisted ledger into the
    /// session (persisted values win — Auth means "restore my account")
    /// and answers AuthOk{uid,name,coins}. Malformed tokens answer
    /// AuthErr; the connection stays usable unauthenticated.
    fn auth(&mut self, pid: u32, token: &str) -> Vec<S2C> {
        let token = token.trim();
        if token.is_empty() || token.len() > 64 {
            return vec![S2C::AuthErr { reason: "invalid token".into() }];
        }
        let Some(repo) = self.repo.clone() else {
            // no persistence attached (unit tests): accept but stay ephemeral
            return vec![S2C::AuthErr { reason: "persistence unavailable".into() }];
        };
        let known = repo.auth(token);
        let (uid, name) = match &known {
            Some(found) => found.clone(),
            None => repo.register(token),
        };
        self.session_uid.insert(pid, uid);
        if known.is_none() {
            // Brand-new account: signup bonus seeds the first purchase —
            // onboarding economy: a fresh player gets to feel the shop
            // loop before their first kill (commercialization first).
            // TODO: move into raid.toml as an ops-tunable when the UI
            // needs a "welcome gift" screen.
            self.add_item(pid, &self.coin_id().to_string(), SIGNUP_BONUS);
        }
        // merge persisted inventory under the session pid; persisted
        // values WIN (this is a restore, not a sum — prevents re-join
        // dupe loops where session gains would double-count)
        for (item_id, count) in repo.inventory(uid) {
            let bag = self.inventory.entry(pid).or_default();
            bag.insert(item_id, count);
        }
        let coin = self.coin_id().to_string();
        let coins = self.balance(pid, &coin);
        vec![S2C::AuthOk { uid, name, coins }]
    }

    /// C2S::RequestInventory - full bag/warehouse dump from the session
    /// ledger (which the write-through keeps identical to the repo).
    /// Anonymous connections dump their session-only bag; authenticated
    /// ones see the restored account inventory.
    fn request_inventory(&mut self, pid: u32) -> Vec<S2C> {
        let mut entries: Vec<(String, i64)> = self
            .inventory
            .get(&pid)
            .map(|bag| {
                bag.iter()
                    .map(|(k, v)| (k.clone(), *v))
                    .collect::<Vec<_>>()
            })
            .unwrap_or_default();
        entries.sort(); // stable shape for UI diffs and golden tests
        vec![S2C::InventorySnapshot { entries }]
    }

    pub fn retire_player(&mut self, pid: u32) {
        self.players.remove(&pid);
        self.hit_times.remove(&pid);
        self.session_uid.remove(&pid); // identity dies with the connection
        // Everyone left a raid that actually ran: stop the clock now
        // instead of letting it coast to the 570s team-kill with no audience.
        if self.players.is_empty() && self.raid_active && self.elapsed > 0.0 {
            self.raid_active = false;
        }
    }

    /// net.gd rpc_hit_zombie: rate gate (clock untouched on reject) ->
    /// unknown id silent -> range gate -> clamp -> hp -= dmg -> death roll.
    pub fn validate_hit(&mut self, pid: u32, net_id: u32, dmg: f32) -> Vec<S2C> {
        let now = self.elapsed;
        let last = self.hit_times.get(&pid).copied().unwrap_or(-99.0);
        if now - last < 1.0 / MAX_HIT_RATE {
            return vec![]; // flooding: reject, do NOT refresh the clock
        }
        self.hit_times.insert(pid, now);
        let Some(idx) = self.zombies.iter().position(|z| z.id == net_id) else {
            return vec![]; // unknown entity: ignore silently
        };
        if let Some(&sp) = self.players.get(&pid) {
            if dist2(sp, self.zombies[idx].pos) > MAX_HIT_RANGE {
                return vec![]; // impossible shot
            }
        }
        let dmg = dmg.clamp(0.0, MAX_HIT_DAMAGE);
        let z = &mut self.zombies[idx];
        z.hp -= dmg;
        if z.hp > 0.0 {
            return vec![];
        }
        let z = self.zombies.remove(idx);
        // Loot drop roll mirrors raid_manager._on_zombie_died:
        // 30% chance of 30 + randi()%50; drawn from the LCG for determinism.
        let roll = self.rng.next_u31();
        let loot = &self.content.raid.loot;
        let span = (loot.coin_amount_max - loot.coin_amount_min + 1) as u32;
        let drop_value = if roll % 100 < loot.coin_chance_pct {
            loot.coin_amount_min + (roll % span) as i32
        } else {
            0
        };
        if drop_value > 0 {
            // server-side coin ledger: the last hitter gets the drop (v1
            // simplification; the client stash stays display-only until T6)
            let coin = self.coin_id().to_string();
            self.add_item(pid, &coin, drop_value as i64);
        }
        vec![S2C::ZombieDead {
            net_id: z.id,
            pos: z.pos,
            drop_value,
        }]
    }

    /// net.gd rpc_report_extract -> host ends the raid with success.
    pub fn report_extract(&mut self) -> Vec<S2C> {
        if !self.raid_active {
            return vec![];
        }
        self.raid_active = false;
        vec![S2C::ExtractSuccess]
    }

    /// net.gd rpc_report_player_died: any death fails the raid for the team.
    pub fn report_player_died(&mut self) -> Vec<S2C> {
        if !self.raid_active {
            return vec![];
        }
        self.raid_active = false;
        vec![S2C::RaidFailed]
    }

    /// Central C2S dispatcher — keeps main.rs thin and is unit-testable.
    /// `Hello` restarts a finished raid (see `handle_hello`); main.rs logs it.
    pub fn handle(&mut self, msg: &protocol::C2S) -> Vec<S2C> {
        use protocol::C2S;
        match msg {
            C2S::Hello { .. } => self.handle_hello(),
            C2S::BuyItem { pid, item_id } => self.buy_item(*pid, item_id),
            C2S::RequestShop => self.shop_list(),
            C2S::Auth { pid, token } => self.auth(*pid, token),
            C2S::RequestInventory { pid } => self.request_inventory(*pid),
            C2S::PlayerState { pid, pos, .. } => {
                self.player_state(*pid, *pos);
                vec![]
            }
            C2S::HitZombie { pid, net_id, dmg } => self.validate_hit(*pid, *net_id, *dmg),
            C2S::BoxTaken { pos } => {
                // v1 relay: the map owns box nodes; the server just fans the
                // claim out as RemoveBox (sender receives it too, matching
                // the ENet host relay).
                vec![S2C::RemoveBox { pos: *pos }]
            }
            C2S::ReportExtract { .. } => self.report_extract(),
            C2S::ReportPlayerDied => self.report_player_died(),
        }
    }

    // -------------------------------------------------------- authority --
    /// Advance one fixed tick (1/TICK_HZ seconds). Returns every S2C the
    /// tick produced: mid-swing DamagePlayer, 1 Hz NetState, paced
    /// ZombieStates snapshots, one-shot RaidFailed.
    pub fn tick(&mut self, dt: f32) -> Vec<S2C> {
        // hot-reload pull (README_OPS.md T7): adopt the store's current
        // snapshot before anything consumes the tables this tick
        if let Some(store) = &self.store {
            self.content = store.snapshot();
        }
        let mut out = Vec::new();
        if !self.raid_active {
            return out; // raid over: freeze the world, keep answering pings
        }
        self.tick += 1;
        self.elapsed += dt;

        // ---- raid clock (raid_manager: frenzy at RUN_LIMIT, lost at +GRACE)
        if self.elapsed >= RUN_LIMIT + FRENZY_GRACE {
            self.raid_active = false;
            out.push(S2C::RaidFailed);
            return out;
        }

        // ---- spawner (raid_manager._run_spawner pacing curve) ------------
        self.spawn_acc += dt;
        let diff = (self.elapsed / RAMP_SECONDS).clamp(0.0, 1.0);
        let interval = lerp(SPAWN_INTERVAL_START, SPAWN_INTERVAL_END, diff);
        let max_alive = lerp(MAX_ALIVE_START, MAX_ALIVE_END, diff) as usize;
        if self.spawn_acc >= interval && self.zombies.len() < max_alive {
            self.spawn_acc = 0.0;
            self.try_spawn_near_a_player();
        }

        // ---- zombie AI (zombie.gd _physics_process, host path) -----------
        for i in 0..self.zombies.len() {
            let (_walk, run, _hp, dmg) = self.zstats(self.zombies[i].ztype);
            // cooldown / pending swing timers first
            self.zombies[i].attack_cd = (self.zombies[i].attack_cd - dt).max(0.0);
            if let Some((pid, t)) = self.zombies[i].hit_pending {
                let t = t - dt;
                self.zombies[i].hit_pending = if t <= 0.0 { None } else { Some((pid, t)) };
                if t <= 0.0 {
                    if let (Some(&pp), Some(&zp)) =
                        (self.players.get(&pid), Some(&self.zombies[i].pos))
                    {
                        if dist2(pp, zp) <= ATTACK_LAND_RANGE {
                            out.push(S2C::DamagePlayer { pid, dmg });
                        }
                    }
                }
            }
            // pick the nearest player (zombie.gd _find_player)
            let target = self.nearest_player_to(self.zombies[i].pos);
            let Some((pid, pp)) = target else {
                self.zombies[i].moving = false;
                continue;
            };
            let d = dist2(pp, self.zombies[i].pos);
            if d <= ATTACK_RANGE {
                if self.zombies[i].attack_cd <= 0.0 {
                    // start a swing: face the target, damage lands mid-swing
                    self.zombies[i].attack_cd = ATTACK_COOLDOWN;
                    self.zombies[i].hit_pending = Some((pid, ATTACK_HIT_DELAY));
                    self.zombies[i].yaw = yaw_to(self.zombies[i].pos, pp);
                    self.zombies[i].moving = false;
                }
            } else if d <= DEAGGRO_RANGE {
                // chase: straight-line steering (zombie.gd no-navmesh fallback)
                let dir = [pp[0] - self.zombies[i].pos[0], pp[2] - self.zombies[i].pos[2]];
                let len = (dir[0] * dir[0] + dir[1] * dir[1]).sqrt().max(1e-6);
                self.zombies[i].pos[0] += dir[0] / len * run * dt;
                self.zombies[i].pos[2] += dir[1] / len * run * dt;
                // godot yaw = atan2(dir.x, dir.z) (zombie.gd _face_dir)
                self.zombies[i].yaw = dir[0].atan2(dir[1]).to_degrees();
                self.zombies[i].moving = true;
            } else {
                self.zombies[i].moving = false;
            }
        }

        // ---- 1 Hz clock broadcast (net.gd _server_tick netstate branch) --
        self.netstate_acc += dt;
        if self.netstate_acc >= 1.0 {
            self.netstate_acc = 0.0;
            out.push(S2C::NetState {
                elapsed: self.elapsed,
                frenzy: self.elapsed >= RUN_LIMIT,
            });
        }

        // ---- snapshot pacing (net.gd _server_tick, reset-to-zero) --------
        self.snap_acc += dt;
        if self.snap_acc >= SNAPSHOT_DT {
            self.snap_acc = 0.0;
            self.snap_seq += 1;
            out.push(self.snapshot());
        }

        out
    }

    /// 15 Hz-ish entity snapshot: `[seq, id,x,y,z,yaw,anim,ztype] * N`
    /// packed as ZombieStates (net.gd _broadcast_zombie_states layout).
    fn snapshot(&self) -> S2C {
        let ents = self
            .zombies
            .iter()
            .map(|z| protocol::ZombieEnt {
                id: z.id,
                pos: z.pos,
                yaw: z.yaw,
                // anim codes match net.gd _broadcast_zombie_states:
                // ATTACK window (cooldown running) wins, then moving, else idle
                anim: if z.attack_cd > 0.0 {
                    4
                } else if z.moving {
                    2
                } else {
                    1
                },
                ztype: z.ztype,
            })
            .collect();
        S2C::ZombieStates {
            seq: self.snap_seq,
            ents,
        }
    }

    // --------------------------------------------------------- spawning --
    /// Auto-spawn: ring around a deterministic player pick, 20 m out
    /// (MIN_SPAWN_DIST + margin; the real host uses map SpawnPoint nodes,
    /// which the dedicated server does not have in v1).
    fn try_spawn_near_a_player(&mut self) {
        if self.players.is_empty() {
            return;
        }
        // sorted ids keep the pick deterministic across HashMap orders
        let mut ids: Vec<u32> = self.players.keys().copied().collect();
        ids.sort_unstable();
        let pick = ids[(self.rng.next_u31() as usize) % ids.len()];
        let angle = (self.rng.next_u31() as f32 / u32::MAX as f32) * std::f32::consts::TAU;
        let radius = MIN_SPAWN_DIST + 2.0;
        let base = self.players[&pick];
        let pos = [
            base[0] + angle.sin() * radius,
            base[1],
            base[2] + angle.cos() * radius,
        ];
        let ztype = self.pick_variant();
        self.force_spawn(ztype, pos);
    }

    /// Weighted variant roll (raid_manager._pick_variant_index).
    fn pick_variant(&mut self) -> u8 {
        let weights = self.content.spawn_weights();
        let total: u32 = weights.iter().map(|e| e.1).sum();
        if total == 0 {
            return 0;
        }
        let mut roll = self.rng.next_u31() % total;
        for (zt, w) in &weights {
            if roll < *w {
                return *zt;
            }
            roll -= *w;
        }
        0
    }

    /// Test/spawn helper: register a zombie of `ztype` at `pos`.
    pub fn force_spawn(&mut self, ztype: u8, pos: [f32; 3]) -> u32 {
        let (_walk, _run, hp, _dmg) = self.zstats(ztype);
        let id = self.next_id;
        self.next_id += 1;
        self.zombies.push(Zombie {
            id,
            pos,
            yaw: 0.0,
            ztype,
            hp,
            attack_cd: 0.0,
            hit_pending: None,
            moving: false,
        });
        id
    }

    fn nearest_player_to(&self, pos: [f32; 3]) -> Option<(u32, [f32; 3])> {
        self.players
            .iter()
            .min_by(|a, b| dist2(*a.1, pos).total_cmp(&dist2(*b.1, pos)))
            .map(|(&pid, &p)| (pid, p))
    }
}

/// 2D (x,z) distance — the server has no vertical gameplay; y is carried
/// through the protocol untouched for client-side use.
fn dist2(a: [f32; 3], b: [f32; 3]) -> f32 {
    let dx = a[0] - b[0];
    let dz = a[2] - b[2];
    (dx * dx + dz * dz).sqrt()
}

/// Godot yaw convention (zombie.gd _face_dir): atan2(dir.x, dir.z).
/// Kept in one place because the snapshot consumer must match it.
fn yaw_to(from: [f32; 3], to: [f32; 3]) -> f32 {
    (to[0] - from[0]).atan2(to[2] - from[2])
}

/// Godot lerp(a, b, t) — the stdlib has no stable f32::lerp.
fn lerp(a: f32, b: f32, t: f32) -> f32 {
    a + (b - a) * t
}

#[cfg(test)]
mod tests {
    use super::*;
    use protocol::C2S;

    const DT: f32 = TICK_DT;

    fn msgs_of(world: &mut World, ticks: usize) -> Vec<S2C> {
        let mut all = Vec::new();
        for _ in 0..ticks {
            all.extend(world.tick(DT));
        }
        all
    }

    // ---- determinism ----

    #[test]
    fn same_seed_same_spawn_sequence() {
        let mut a = World::new(42);
        let mut b = World::new(42);
        for w in [&mut a, &mut b] {
            w.player_state(2, [0.0, 0.0, 0.0]);
        }
        let ra = msgs_of(&mut a, 400);
        let rb = msgs_of(&mut b, 400);
        let last_ents = |msgs: &[S2C]| -> Vec<(u32, [f32; 3], u8)> {
            msgs.iter()
                .filter_map(|m| match m {
                    S2C::ZombieStates { ents, .. } => Some(
                        ents.iter()
                            .map(|e| (e.id, e.pos, e.ztype))
                            .collect::<Vec<_>>(),
                    ),
                    _ => None,
                })
                .next_back()
                .unwrap_or_default()
        };
        assert_eq!(last_ents(&ra), last_ents(&rb));
        assert!(!last_ents(&ra).is_empty(), "20s with a player must spawn");
    }

    #[test]
    fn different_seed_different_spawn_sequence() {
        let mut a = World::new(42);
        let mut b = World::new(43);
        for w in [&mut a, &mut b] {
            w.player_state(2, [0.0, 0.0, 0.0]);
        }
        let fa = format!("{:?}", msgs_of(&mut a, 600));
        let fb = format!("{:?}", msgs_of(&mut b, 600));
        assert_ne!(fa, fb);
    }

    // ---- pacing ----

    #[test]
    fn spawn_pacing_follows_host_curve() {
        let mut w = World::new(7);
        w.player_state(2, [0.0, 0.0, 0.0]);
        // first 4s (80 ticks): interval starts at 5s -> nothing yet
        msgs_of(&mut w, 80);
        assert!(w.zombies().is_empty(), "no spawn before the first interval");
        // by 30s the curve (5.0 -> 2.2 ramping) must have spawned several;
        // max_alive caps at int(lerp(6,14,30/360)) = 6 and nothing dies
        msgs_of(&mut w, 520); // +26s
        let n = w.zombies().len();
        assert!((5..=7).contains(&n), "expected 5..=7 zombies after 30s, got {n}");
    }

    #[test]
    fn snapshot_paces_like_host_every_2nd_tick() {
        // net.gd resets the accumulator to 0 on fire: 20 TPS + 1/15s
        // threshold = exactly one snapshot every 2 ticks.
        let mut w = World::new(1);
        let mut snaps = 0;
        for _ in 0..100 {
            if w.tick(DT)
                .into_iter()
                .any(|m| matches!(m, S2C::ZombieStates { .. }))
            {
                snaps += 1;
            }
        }
        assert_eq!(snaps, 50);
    }

    // ---- AI ----

    #[test]
    fn zombie_chases_nearest_player() {
        let mut w = World::new(5);
        let id = w.force_spawn(0, [10.0, 0.0, 0.0]); // Runner, run 5.4
        w.player_state(2, [16.0, 0.0, 0.0]); // 6m: outside melee, inside aggro
        w.player_state(3, [50.0, 0.0, 0.0]); // far
        w.tick(DT);
        let z = w.zombies().iter().find(|z| z.id == id).unwrap();
        // one tick at run 5.4 * 0.05s = 0.27m closed
        assert!((z.pos[0] - 10.27).abs() < 1e-4, "moved {:?}", z.pos);
        assert!(z.moving);
        assert_eq!(z.yaw as i32, 90); // atan2(dx=1, dz=0) in degrees
    }

    #[test]
    fn zombie_swing_lands_damage_after_delay() {
        let mut w = World::new(5);
        w.force_spawn(1, [1.0, 0.0, 0.0]); // Walker vs player at origin
        w.player_state(2, [0.0, 0.0, 0.0]);
        // swing starts tick 1; damage lands 0.4s (8 ticks) later
        let mut hit = None;
        for i in 0..20 {
            for m in w.tick(DT) {
                if let S2C::DamagePlayer { pid, dmg } = m {
                    hit = Some((i, pid, dmg));
                }
            }
        }
        let (i, pid, dmg) = hit.expect("swing must land");
        assert_eq!(pid, 2);
        assert_eq!(dmg, 15.0); // Walker damage
        assert!(
            (i as f32 * DT - ATTACK_HIT_DELAY).abs() < DT,
            "lands at ~0.4s, got {}",
            i as f32 * DT
        );
        // walking out of the grace ring dodges: mid-swing check is 2.6m
        let mut w = World::new(5);
        w.force_spawn(1, [1.0, 0.0, 0.0]);
        w.player_state(2, [0.0, 0.0, 0.0]);
        w.tick(DT); // swing starts
        w.player_state(2, [50.0, 0.0, 0.0]); // dash away
        let dodged = !msgs_of(&mut w, 10)
            .iter()
            .any(|m| matches!(m, S2C::DamagePlayer { .. }));
        assert!(dodged, "mid-swing check must respect ATTACK_LAND_RANGE");
    }

    // ---- hit validation (net.gd rpc_hit_zombie matrix) ----

    #[test]
    fn hit_validation_full_matrix() {
        let mut w = World::new(42);
        w.player_state(2, [0.0, 0.0, 0.0]);
        let id = w.force_spawn(1, [5.0, 0.0, 0.0]); // Walker, 60hp
        // unknown id: silent — but net.gd refreshes the hit clock BEFORE the
        // id lookup, so this first call burns the rate window
        assert!(w.validate_hit(2, 999, 10.0).is_empty());
        // immediate second shot: rate gate rejects (clock was refreshed)
        assert!(w.validate_hit(2, id, 10.0).is_empty());
        assert_eq!(w.zombies()[0].hp, 60.0, "rejected shot deals no damage");
        // 51ms later: accepted, 500 dmg clamps to 80 -> 60hp Walker DIES
        w.elapsed += 0.051;
        let out = w.validate_hit(2, id, 500.0);
        match &out[..] {
            [S2C::ZombieDead { net_id, drop_value, .. }] => {
                assert_eq!(*net_id, id);
                assert!(*drop_value == 0 || (30..80).contains(drop_value));
            }
            _ => panic!("80 dmg must kill a 60hp walker, got {out:?}"),
        }
        assert!(w.zombies().iter().all(|z| z.id != id), "dead zombie leaves the world");
    }

    #[test]
    fn kill_emits_zombie_dead_with_deterministic_drop() {
        let mut a = World::new(42);
        let mut b = World::new(42);
        for w in [&mut a, &mut b] {
            w.player_state(2, [0.0, 0.0, 0.0]);
            w.force_spawn(2, [5.0, 0.0, 0.0]); // Brute, 150hp
        }
        // Brute 150hp: shot 1 (80) -> 70 alive; 51ms later shot 2 (80) kills
        let mut drops = Vec::new();
        for w in [&mut a, &mut b] {
            let id = w.zombies()[0].id;
            assert!(w.validate_hit(2, id, 80.0).is_empty(), "first shot wounds only");
            w.elapsed += 0.051;
            let out = w.validate_hit(2, id, 80.0);
            drops.push(
                out.into_iter()
                    .filter_map(|m| match m {
                        S2C::ZombieDead { drop_value, .. } => Some(drop_value),
                        _ => None,
                    })
                    .next()
                    .expect("second 80dmg shot kills the 150hp brute"),
            );
        }
        assert_eq!(drops[0], drops[1], "same seed -> same drop roll");
        assert!(
            drops[0] == 0 || (30..80).contains(&drops[0]),
            "drop mirrors 30% -> 30+r%50, got {}",
            drops[0]
        );
    }

    #[test]
    fn out_of_range_shot_rejected() {
        let mut w = World::new(42);
        w.player_state(2, [0.0, 0.0, 0.0]);
        let id = w.force_spawn(1, [80.5, 0.0, 0.0]); // just past the 80m clamp
        assert!(w.validate_hit(2, id, 10.0).is_empty());
        assert_eq!(w.zombies()[0].hp, 60.0, "hp untouched on impossible shot");
        // and the rate gate DID burn (net.gd refreshes the clock first):
        assert!(w.validate_hit(2, id, 10.0).is_empty());
    }

    // ---- raid lifecycle ----

    #[test]
    fn player_death_and_extract_end_the_raid() {
        let mut w = World::new(42);
        assert_eq!(w.handle(&C2S::ReportPlayerDied), vec![S2C::RaidFailed]);
        assert!(!w.raid_active);
        assert!(w.handle(&C2S::ReportPlayerDied).is_empty(), "second report is a no-op");
        assert!(w.tick(DT).is_empty(), "frozen world emits nothing");

        let mut w = World::new(42);
        assert_eq!(
            w.handle(&C2S::ReportExtract { in_zone: true }),
            vec![S2C::ExtractSuccess]
        );
        assert!(!w.raid_active);
    }

    #[test]
    fn clock_frenzy_then_raid_lost() {
        let mut w = World::new(42);
        w.player_state(2, [0.0, 0.0, 0.0]);
        w.elapsed = RUN_LIMIT - 0.1;
        let mut saw_frenzy = false;
        let mut failed = false;
        for _ in 0..(FRENZY_GRACE as usize * 20 + 40) {
            for m in w.tick(DT) {
                match m {
                    S2C::NetState { frenzy: true, .. } => saw_frenzy = true,
                    S2C::RaidFailed => failed = true,
                    _ => {}
                }
            }
            if failed {
                break;
            }
        }
        assert!(saw_frenzy, "NetState flags frenzy at RUN_LIMIT");
        assert!(failed, "raid fails after RUN_LIMIT + FRENZY_GRACE");
        assert!(!w.raid_active);
    }

    // ---- session lifecycle (step 5) ----

    #[test]
    fn hello_restarts_a_finished_raid() {
        let mut w = World::new(42);
        w.player_state(2, [0.0, 0.0, 0.0]);
        let id = w.force_spawn(1, [5.0, 0.0, 0.0]);
        assert!(w.handle(&C2S::ReportPlayerDied).len() == 1);
        assert!(!w.raid_active);
        // the next Hello starts raid #2 on a fresh seed and broadcasts it
        let out = w.handle(&C2S::Hello { ver: 2 });
        match &out[..] {
            [S2C::Seed { seed, elapsed }] => {
                assert_ne!(*seed, 42, "next raid must get a fresh seed");
                assert_eq!(*seed, w.seed);
                assert_eq!(*elapsed, 0.0);
            }
            other => panic!("expected one Seed, got {other:?}"),
        }
        assert!(w.raid_active, "raid #2 is live");
        assert_eq!(w.elapsed, 0.0);
        assert!(w.zombies().is_empty(), "raid #2 starts clean");
        assert!(w.zombies().iter().all(|z| z.id != id));
        assert_eq!(w.player_count(), 0, "roster clears; clients re-report state");
        // and the new world actually runs: 20s with a player spawns again
        w.player_state(2, [0.0, 0.0, 0.0]);
        assert!(msgs_of(&mut w, 400).iter().any(|m| matches!(
            m, S2C::ZombieStates { ents, .. } if !ents.is_empty()
        )), "raid #2 must spawn zombies");
    }

    #[test]
    fn hello_during_live_raid_is_noop() {
        let mut w = World::new(42);
        w.player_state(2, [0.0, 0.0, 0.0]);
        w.elapsed = 12.5; // mid-raid
        assert!(w.handle(&C2S::Hello { ver: 2 }).is_empty());
        assert!(w.raid_active);
        assert_eq!(w.elapsed, 12.5, "live raid is untouched by a Hello");
    }

    #[test]
    fn retire_player_cleans_up_and_freezes_an_empty_raid() {
        let mut w = World::new(42);
        w.player_state(2, [0.0, 0.0, 0.0]);
        w.player_state(3, [9.0, 0.0, 9.0]);
        let id = w.force_spawn(1, [5.0, 0.0, 0.0]);
        msgs_of(&mut w, 5); // elapsed > 0: this raid actually ran
        // one player leaves: raid keeps running for the survivor
        w.retire_player(2);
        assert_eq!(w.player_count(), 1);
        assert!(w.raid_active);
        // their hit-rate clock dies with them: same-elapsed shot accepted
        w.player_state(2, [0.0, 0.0, 0.0]);
        assert!(w.validate_hit(2, id, 10.0).is_empty(), "shot must pass the gates");
        assert_eq!(w.zombies()[0].hp, 50.0, "fresh hit clock after retire");
        // the last player leaves a raid that ran: clock stops immediately
        w.retire_player(2);
        w.retire_player(3);
        assert_eq!(w.player_count(), 0);
        assert!(!w.raid_active, "empty raid freezes instead of coasting");
        assert!(w.tick(DT).is_empty());
        let _ = id;
    }

    #[test]
    fn everyone_leaving_then_hello_starts_next_raid() {
        let mut w = World::new(42);
        w.player_state(2, [0.0, 0.0, 0.0]);
        msgs_of(&mut w, 100); // 5s of raid time (elapsed > 0)
        w.retire_player(2);
        assert!(!w.raid_active);
        let out = w.handle(&C2S::Hello { ver: 2 });
        assert!(matches!(out[..], [S2C::Seed { .. }]), "restart on rejoin");
        assert!(w.raid_active);
        assert_eq!(w.elapsed, 0.0);
    }

    #[test]
    fn restart_seed_differs_across_two_finished_raids() {
        let mut w = World::new(42);
        w.player_state(2, [0.0, 0.0, 0.0]);
        msgs_of(&mut w, 200); // raid #1 runs ~10s
        w.handle(&C2S::ReportPlayerDied);
        let seed2 = match &w.handle(&C2S::Hello { ver: 2 })[..] {
            [S2C::Seed { seed, .. }] => *seed,
            other => panic!("{other:?}"),
        };
        // raid #2 runs a different length -> a third raid gets another seed
        w.player_state(2, [0.0, 0.0, 0.0]);
        msgs_of(&mut w, 500); // ~25s
        w.handle(&C2S::ReportPlayerDied);
        let seed3 = match &w.handle(&C2S::Hello { ver: 2 })[..] {
            [S2C::Seed { seed, .. }] => *seed,
            other => panic!("{other:?}"),
        };
        assert_ne!(seed2, seed3, "each raid gets its own seed");
    }
}


#[cfg(test)]
mod shop_tests {
    //! T5: server-authoritative shop loop (README_OPS.md).

    use super::*;
    use protocol::C2S;

    fn w_with_coins(coins: i64) -> World {
        let mut w = World::new(42);
        w.player_state(2, [0.0, 0.0, 0.0]);
        if coins > 0 {
            let c = w.coin_id().to_string();
            w.add_item(2, &c, coins);
        }
        w
    }

    #[test]
    fn kill_credits_coins_to_last_hitter() {
        let mut w = World::new(42);
        w.player_state(2, [0.0, 0.0, 0.0]);
        let id = w.force_spawn(1, [5.0, 0.0, 0.0]);
        let coin = w.coin_id().to_string();
        let msgs = w.validate_hit(2, id, 80.0); // kills the 60hp walker
        let drop = match &msgs[..] {
            [S2C::ZombieDead { drop_value, .. }] => *drop_value as i64,
            other => panic!("{other:?}"),
        };
        assert_eq!(w.balance(2, &coin), drop, "ledger mirrors the drop roll");
    }

    #[test]
    fn happy_purchase_deducts_and_credits() {
        let mut w = w_with_coins(1000);
        let out = w.handle(&C2S::BuyItem { pid: 2, item_id: "bandage".into() });
        let coin = w.coin_id().to_string();
        match &out[..] {
            [S2C::InventoryUpdate { pid: p1, item_id: c, count: cc },
             S2C::InventoryUpdate { pid: p2, item_id: b, count: bc }] => {
                assert_eq!((*p1, *p2), (2, 2), "both updates target the buyer");
                assert_eq!(c, &coin, "first update is the coin deduction");
                assert_eq!(*cc, 1000 - 120);
                assert_eq!(b, "bandage");
                assert_eq!(*bc, 1);
            }
            other => panic!("{other:?}"),
        }
        assert_eq!(w.balance(2, &coin), 880);
        assert_eq!(w.balance(2, "bandage"), 1);
    }

    #[test]
    fn insufficient_coins_rejected() {
        let mut w = w_with_coins(0);
        let out = w.handle(&C2S::BuyItem { pid: 2, item_id: "bandage".into() });
        assert!(
            matches!(&out[..], [S2C::TradeError { reason, .. }] if reason == "insufficient coins"),
            "{out:?}"
        );
        assert_eq!(w.balance(2, "bandage"), 0, "rejected trade mutates nothing");
    }

    #[test]
    fn unknown_item_rejected() {
        let mut w = w_with_coins(500);
        let out = w.handle(&C2S::BuyItem { pid: 2, item_id: "ghost".into() });
        assert!(matches!(&out[..], [S2C::TradeError { reason, .. }] if reason.contains("unknown item")));
    }

    #[test]
    fn not_for_sale_rejected() {
        let mut w = w_with_coins(500);
        let out = w.handle(&C2S::BuyItem { pid: 2, item_id: "scrap_metal".into() });
        assert!(matches!(&out[..], [S2C::TradeError { reason, .. }] if reason == "not for sale"));
    }

    #[test]
    fn shop_lists_purchasable_only() {
        let mut w = World::new(42);
        let out = w.handle(&C2S::RequestShop);
        match &out[..] {
            [S2C::ShopList { entries }] => {
                assert_eq!(
                    entries,
                    &vec![("bandage".to_string(), 120u32), ("ammo_box".to_string(), 250u32)],
                    "coin/scrap_metal are not purchasable"
                );
            }
            other => panic!("{other:?}"),
        }
    }

    #[test]
    fn trade_after_raid_over_rejected() {
        let mut w = w_with_coins(1000);
        w.handle(&C2S::ReportPlayerDied);
        let out = w.handle(&C2S::BuyItem { pid: 2, item_id: "bandage".into() });
        assert!(matches!(&out[..], [S2C::TradeError { reason, .. }] if reason == "raid is over"));
    }
}

#[cfg(test)]
mod repo_tests {
    //! T6: write-through persistence (README_OPS.md). The in-session
    //! ledger stays the read path; these tests pin that every mutation
    //! also lands in the PlayerRepo and survives a raid reset.

    use super::*;
    use crate::player_repo::{PlayerRepo, SqlitePlayerRepo};
    use protocol::C2S;

    fn w_with_repo(repo: std::sync::Arc<dyn PlayerRepo>) -> World {
        let mut w = World::with_repo(
            42,
            std::sync::Arc::new(ContentTables::built_in()),
            repo,
        );
        w.player_state(2, [0.0, 0.0, 0.0]);
        w
    }

    #[test]
    fn kill_credits_persist_through_repo() {
        let repo = std::sync::Arc::new(SqlitePlayerRepo::in_memory().unwrap());
        let mut w = w_with_repo(repo.clone());
        let id = w.force_spawn(1, [5.0, 0.0, 0.0]);
        let coin = w.coin_id().to_string();
        let msgs = w.validate_hit(2, id, 80.0); // kills the 60hp walker
        let drop = match &msgs[..] {
            [S2C::ZombieDead { drop_value, .. }] => *drop_value as i64,
            other => panic!("{other:?}"),
        };
        assert_eq!(repo.balance(2, &coin), drop, "repo mirrors the drop roll");
    }

    #[test]
    fn purchase_writes_flow_record() {
        let repo = std::sync::Arc::new(SqlitePlayerRepo::in_memory().unwrap());
        let mut w = w_with_repo(repo.clone());
        let coin = w.coin_id().to_string();
        w.add_item(2, &coin, 1000);
        w.handle(&C2S::BuyItem { pid: 2, item_id: "bandage".into() });
        assert_eq!(
            repo.purchases(2),
            vec![("bandage".into(), 120, 1000)],
            "accepted trades land in the purchases audit trail"
        );
        assert_eq!(repo.balance(2, &coin), 880);
        assert_eq!(repo.balance(2, "bandage"), 1);
    }

    #[test]
    fn reset_keeps_repo_attached_and_data() {
        let repo = std::sync::Arc::new(SqlitePlayerRepo::in_memory().unwrap());
        let mut w = w_with_repo(repo.clone());
        let coin = w.coin_id().to_string();
        w.add_item(2, &coin, 777);
        w.reset(100);
        assert!(w.repo.is_some(), "reset must not drop the repo");
        assert_eq!(
            repo.balance(2, &coin),
            777,
            "ledger data survives the raid reset (invariant 5)"
        );
        // the NEW world still writes through
        w.add_item(2, "bandage", 2);
        assert_eq!(repo.balance(2, "bandage"), 2);
    }

    #[test]
    fn rejected_trade_writes_nothing() {
        let repo = std::sync::Arc::new(SqlitePlayerRepo::in_memory().unwrap());
        let mut w = w_with_repo(repo.clone());
        w.handle(&C2S::BuyItem { pid: 2, item_id: "bandage".into() }); // zero coins
        assert!(repo.purchases(2).is_empty());
        assert_eq!(repo.balance(2, "bandage"), 0);
        assert_eq!(repo.balance(2, &w.coin_id()), 0);
    }
}

#[cfg(test)]
mod hotswap_tests {
    //! T7: admin snapshot swap takes effect at the next tick boundary.

    use super::*;
    use crate::content_store::ContentStore;

    #[test]
    fn admin_swap_takes_effect_next_tick() {
        let store = std::sync::Arc::new(ContentStore::new(std::sync::Arc::new(
            ContentTables::built_in(),
        )));
        let mut w = World::new(42);
        w.player_state(2, [0.0, 0.0, 0.0]);
        w.attach_store(store.clone());
        // swap in a table where the walker (ztype 1) has 999 hp
        let mut next = ContentTables::built_in();
        next.zombies[1].max_hp = 999.0;
        store.swap(std::sync::Arc::new(next));
        w.tick(1.0 / 20.0); // adopts the new snapshot
        let id = w.force_spawn(1, [5.0, 0.0, 0.0]);
        let msgs = w.validate_hit(2, id, 80.0); // lethal to the 60hp walker
        assert!(
            !msgs.iter().any(|m| matches!(m, S2C::ZombieDead { .. })),
            "swapped 999hp walker survives a would-be lethal hit"
        );
    }

    #[test]
    fn no_store_means_fixed_snapshot() {
        let mut w = World::new(42);
        w.player_state(2, [0.0, 0.0, 0.0]);
        w.tick(1.0 / 20.0);
        let id = w.force_spawn(1, [5.0, 0.0, 0.0]);
        let msgs = w.validate_hit(2, id, 80.0);
        assert!(
            msgs.iter().any(|m| matches!(m, S2C::ZombieDead { .. })),
            "without a store the boot snapshot rules (60hp walker dies)"
        );
    }
}

#[cfg(test)]
mod auth_tests {
    //! T9/T10: account identity + full inventory dump (docs/CLIENT_API.md).

    use super::*;
    use crate::player_repo::{PlayerRepo, SqlitePlayerRepo};
    use protocol::C2S;

    fn make_world() -> (World, std::sync::Arc<SqlitePlayerRepo>) {
        let repo = std::sync::Arc::new(SqlitePlayerRepo::in_memory().unwrap());
        let w = World::with_repo(
            42,
            std::sync::Arc::new(ContentTables::built_in()),
            repo.clone(),
        );
        (w, repo)
    }

    fn kill_one(w: &mut World) -> i64 {
        let id = w.force_spawn(1, [5.0, 0.0, 0.0]);
        match &w.validate_hit(2, id, 80.0)[..] {
            [S2C::ZombieDead { drop_value, .. }] => *drop_value as i64,
            other => panic!("{other:?}"),
        }
    }

    #[test]
    fn auth_ok_binds_pid_and_restores_persisted_balance() {
        let (mut w, repo) = make_world();
        w.player_state(2, [0.0, 0.0, 0.0]);
        let uid = repo.register("tok").0;
        repo.add_item(uid, "coin", 500);

        let out = w.handle(&C2S::Auth { pid: 2, token: "tok".into() });
        match &out[..] {
            [S2C::AuthOk { uid: u, name, coins }] => {
                assert_eq!(*u, uid);
                assert_eq!(name, "survivor#0001");
                assert_eq!(*coins, 500, "AuthOk carries the persisted balance");
            }
            other => panic!("{other:?}"),
        }
        assert_eq!(w.balance(2, &w.coin_id()), 500, "session ledger restored");

        // post-auth kill credits the UID key in the repo (not the raw pid)
        let drop = kill_one(&mut w);
        assert_eq!(repo.balance(uid, &w.coin_id()), 500 + drop);
    }

    #[test]
    fn rejoin_with_same_token_restores_balance() {
        let (mut w, repo) = make_world();
        w.player_state(2, [0.0, 0.0, 0.0]);
        repo.register("tok"); // pre-register: no signup bonus in this test
        w.handle(&C2S::Auth { pid: 2, token: "tok".into() });
        let drop = kill_one(&mut w);
        let coins_after_raid1 = 0 + drop;

        // session 2: fresh World, same repo (server restart simulation)
        let repo2: std::sync::Arc<dyn PlayerRepo> = repo.clone();
        let mut w2 = World::with_repo(
            42,
            std::sync::Arc::new(ContentTables::built_in()),
            repo2,
        );
        w2.player_state(9, [0.0, 0.0, 0.0]); // different session pid!
        let out = w2.handle(&C2S::Auth { pid: 9, token: "tok".into() });
        match &out[..] {
            [S2C::AuthOk { coins, .. }] => assert_eq!(*coins, coins_after_raid1),
            other => panic!("{other:?}"),
        }
        assert_eq!(w2.balance(9, &w2.coin_id()), coins_after_raid1);
    }

    #[test]
    fn invalid_token_rejected_connection_stays_usable() {
        let (mut w, _repo) = make_world();
        w.player_state(2, [0.0, 0.0, 0.0]);
        let out = w.handle(&C2S::Auth { pid: 2, token: "  ".into() });
        assert!(matches!(&out[..], [S2C::AuthErr { reason, .. }] if reason == "invalid token"));
        // the raid keeps working unauthenticated
        let drop = kill_one(&mut w);
        assert_eq!(w.balance(2, &w.coin_id()), drop);
    }

    #[test]
    fn signup_bonus_seeds_the_first_purchase() {
        let (mut w, repo) = make_world();
        w.player_state(2, [0.0, 0.0, 0.0]);
        let out = w.handle(&C2S::Auth { pid: 2, token: "brand-new".into() });
        let coins = match &out[..] {
            [S2C::AuthOk { coins, .. }] => *coins,
            other => panic!("{other:?}"),
        };
        assert_eq!(coins, SIGNUP_BONUS, "fresh account starts with the bonus");
        // the bonus must cover the cheapest purchasable item
        let bandage_price = w.content.item("bandage").unwrap().shop.price as i64;
        assert!(coins >= bandage_price, "onboarding economy: first buy reachable");
        // and the purchase actually succeeds right after sign-in
        let out = w.handle(&C2S::BuyItem { pid: 2, item_id: "bandage".into() });
        assert!(
            matches!(&out[..],
                [S2C::InventoryUpdate { .. }, S2C::InventoryUpdate { .. }]),
            "new player can complete a purchase before their first kill"
        );
        assert_eq!(repo.balance(repo.auth("brand-new").unwrap().0, "bandage"), 1);
    }

    #[test]
    fn request_inventory_lists_sorted_session_ledger() {
        let (mut w, repo) = make_world();
        w.player_state(2, [0.0, 0.0, 0.0]);
        repo.register("tok"); // pre-register: no signup bonus in this test
        w.handle(&C2S::Auth { pid: 2, token: "tok".into() });
        w.add_item(2, "bandage", 1);
        w.add_item(2, &w.coin_id().to_string(), 77);

        let out = w.handle(&C2S::RequestInventory { pid: 2 });
        match &out[..] {
            [S2C::InventorySnapshot { entries }] => {
                assert_eq!(
                    entries,
                    &vec![
                        ("bandage".to_string(), 1),
                        ("coin".to_string(), 77),
                    ],
                    "sorted by item_id, full bag"
                );
            }
            other => panic!("{other:?}"),
        }
    }
}
