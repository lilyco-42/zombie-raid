//! Content tables — the data-driven half of the server (README_OPS.md).
//!
//! The 10-year contract: gameplay CONTENT (items, zombie kinds, tunable
//! raid rules) lives in versioned TOML under `server/content/`, NOT in
//! compiled code. A collab skin, a new item or a nerf ships as a table
//! row; only new *mechanics* (effect primitives) touch Rust.
//!
//! Fail-closed: any validation violation rejects the whole table set —
//! a broken table must never half-apply to a live server.
//!
//! Baseline guarantee: `built_in()` mirrors the pre-content constants of
//! world.rs exactly, so the same seed produces the same spawn/drop
//! sequences before and after this migration (commercial fairness).

use serde::Deserialize;

/// Shop listing attached to an item (the commercialization hook).
#[derive(Debug, Clone, Default, Deserialize, PartialEq)]
pub struct ShopEntry {
    #[serde(default)]
    pub price: u32,
    #[serde(default)]
    pub purchasable: bool,
}

#[derive(Debug, Clone, Deserialize, PartialEq)]
pub struct ItemDef {
    /// Forever-contract: published ids are never reused (README_OPS.md).
    pub id: String,
    #[serde(default)]
    pub name: String,
    /// currency | consumable | material | weapon | skin
    pub kind: String,
    #[serde(default = "default_stack")]
    pub stack_max: u32,
    #[serde(default)]
    pub sellable: bool,
    /// Retirement flag: deprecated rows stay for old saves, never deleted.
    #[serde(default)]
    pub deprecated: bool,
    #[serde(default)]
    pub shop: ShopEntry,
}

fn default_stack() -> u32 {
    1
}

#[derive(Debug, Clone, Deserialize, PartialEq)]
pub struct ZombieDef {
    /// u8 rides the wire in ZombieStates; same forever-contract as items.
    pub id: u8,
    pub key: String,
    #[serde(default)]
    pub name: String,
    pub walk: f32,
    pub run: f32,
    pub max_hp: f32,
    pub damage: f32,
    /// 0 = not in the auto-spawner pool (e.g. the scripted-only spitter).
    #[serde(default)]
    pub spawn_weight: u32,
    #[serde(default)]
    pub deprecated: bool,
}

#[derive(Debug, Clone, Deserialize, PartialEq)]
pub struct SpawningCfg {
    pub interval_start: f32,
    pub interval_end: f32,
    pub max_alive_start: f32,
    pub max_alive_end: f32,
    pub ramp_seconds: f32,
    pub min_spawn_dist: f32,
}

#[derive(Debug, Clone, Deserialize, PartialEq)]
pub struct ClockCfg {
    pub run_limit: f32,
    pub frenzy_grace: f32,
}

#[derive(Debug, Clone, Deserialize, PartialEq)]
pub struct HitRulesCfg {
    pub max_rate: f32,
    pub max_damage: f32,
    pub max_range: f32,
}

#[derive(Debug, Clone, Deserialize, PartialEq)]
pub struct LootCfg {
    pub coin_chance_pct: u32,
    pub coin_amount_min: i32,
    pub coin_amount_max: i32,
}

#[derive(Debug, Clone, Deserialize, PartialEq)]
pub struct RaidConfig {
    pub spawning: SpawningCfg,
    pub clock: ClockCfg,
    pub hit_rules: HitRulesCfg,
    pub loot: LootCfg,
}

#[derive(Debug, Clone, Deserialize)]
struct ZombiesDoc {
    #[serde(rename = "zombie")]
    zombies: Vec<ZombieDef>,
}

#[derive(Debug, Clone, Deserialize)]
struct ItemsDoc {
    #[serde(rename = "item")]
    items: Vec<ItemDef>,
}

/// The full content surface the server runs on.
#[derive(Debug, Clone, PartialEq)]
pub struct ContentTables {
    pub zombies: Vec<ZombieDef>,
    pub items: Vec<ItemDef>,
    pub raid: RaidConfig,
}

/// Operator-facing error (shown in logs / CI, not just a debug dump).
#[derive(Debug, Clone, PartialEq)]
pub struct ContentError(pub String);

impl std::fmt::Display for ContentError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.0)
    }
}

impl std::error::Error for ContentError {}

/// Compiled into the binary: the server boots valid even with no files on
/// disk (deployment hardening — the binary always carries a known-good set).
pub const ZOMBIES_TOML: &str = include_str!("../../content/zombies.toml");
pub const ITEMS_TOML: &str = include_str!("../../content/items.toml");
pub const RAID_TOML: &str = include_str!("../../content/raid.toml");

impl ContentTables {
    /// Parse the three table files. Parsing never validates — chain
    /// `.validate()` (or use `load_validated`).
    pub fn load(zombies_toml: &str, items_toml: &str, raid_toml: &str) -> Result<Self, ContentError> {
        let z: ZombiesDoc =
            toml::from_str(zombies_toml).map_err(|e| ContentError(format!("zombies.toml: {e}")))?;
        let i: ItemsDoc =
            toml::from_str(items_toml).map_err(|e| ContentError(format!("items.toml: {e}")))?;
        let r: RaidConfig =
            toml::from_str(raid_toml).map_err(|e| ContentError(format!("raid.toml: {e}")))?;
        Ok(Self {
            zombies: z.zombies,
            items: i.items,
            raid: r,
        })
    }

    pub fn load_validated(zombies_toml: &str, items_toml: &str, raid_toml: &str) -> Result<Self, ContentError> {
        let t = Self::load(zombies_toml, items_toml, raid_toml)?;
        t.validate()?;
        Ok(t)
    }

    /// The known-good set baked into the binary — the same-seed baseline.
    pub fn built_in() -> Self {
        Self::load_validated(ZOMBIES_TOML, ITEMS_TOML, RAID_TOML)
            .expect("built-in content tables must always be valid")
    }

    /// Fail-closed validation: any violation rejects the whole set.
    pub fn validate(&self) -> Result<(), ContentError> {
        // -- zombies: unique ids/keys, sane kinematics, a spawner exists --
        let mut zids = std::collections::HashSet::new();
        let mut zkeys = std::collections::HashSet::new();
        for z in &self.zombies {
            if !zids.insert(z.id) {
                return Err(ContentError(format!("zombie id {} duplicated", z.id)));
            }
            if !zkeys.insert(z.key.as_str()) {
                return Err(ContentError(format!("zombie key '{}' duplicated", z.key)));
            }
            if !(z.max_hp > 0.0 && z.max_hp.is_finite()) {
                return Err(ContentError(format!("zombie '{}': max_hp must be > 0", z.key)));
            }
            if !(z.damage > 0.0 && z.damage.is_finite()) {
                return Err(ContentError(format!("zombie '{}': damage must be > 0", z.key)));
            }
            if !(z.walk > 0.0 && z.walk <= z.run && z.run.is_finite()) {
                return Err(ContentError(format!(
                    "zombie '{}': walk must be in (0, run]",
                    z.key
                )));
            }
        }
        if !self.zombies.iter().any(|z| z.spawn_weight > 0) {
            return Err(ContentError(
                "at least one zombie must have spawn_weight > 0".into(),
            ));
        }

        // -- items: unique non-empty ids, known kinds, sane shop fields --
        const KINDS: [&str; 5] = ["currency", "consumable", "material", "weapon", "skin"];
        let mut iids = std::collections::HashSet::new();
        for it in &self.items {
            if it.id.is_empty() {
                return Err(ContentError("item id must not be empty".into()));
            }
            if !iids.insert(it.id.as_str()) {
                return Err(ContentError(format!("item id '{}' duplicated", it.id)));
            }
            if !KINDS.contains(&it.kind.as_str()) {
                return Err(ContentError(format!(
                    "item '{}': unknown kind '{}' (allowed: {KINDS:?})",
                    it.id, it.kind
                )));
            }
            if it.stack_max == 0 {
                return Err(ContentError(format!("item '{}': stack_max must be >= 1", it.id)));
            }
            if it.shop.purchasable && it.shop.price == 0 {
                return Err(ContentError(format!(
                    "item '{}': purchasable requires price > 0",
                    it.id
                )));
            }
        }

        // -- raid: sane ranges (fail-closed, mirrors old constant sanity) --
        let s = &self.raid.spawning;
        if !(s.interval_end >= 0.2 && s.interval_start > s.interval_end) {
            return Err(ContentError(
                "spawning: need interval_end >= 0.2 and interval_start > interval_end".into(),
            ));
        }
        if !(s.max_alive_start >= 1.0 && s.max_alive_start <= s.max_alive_end) {
            return Err(ContentError(
                "spawning: need max_alive_start >= 1 and <= max_alive_end".into(),
            ));
        }
        if !(s.ramp_seconds > 0.0 && s.min_spawn_dist >= 0.0) {
            return Err(ContentError(
                "spawning: need ramp_seconds > 0 and min_spawn_dist >= 0".into(),
            ));
        }
        let c = &self.raid.clock;
        if !(c.run_limit > 0.0 && c.frenzy_grace > 0.0) {
            return Err(ContentError("clock: run_limit and frenzy_grace must be > 0".into()));
        }
        let h = &self.raid.hit_rules;
        if !(h.max_rate > 0.0 && h.max_damage > 0.0 && h.max_range > 0.0) {
            return Err(ContentError("hit_rules: all limits must be > 0".into()));
        }
        let l = &self.raid.loot;
        if l.coin_chance_pct > 100 {
            return Err(ContentError("loot: coin_chance_pct must be <= 100".into()));
        }
        if l.coin_amount_min > l.coin_amount_max {
            return Err(ContentError("loot: coin_amount_min must be <= max".into()));
        }
        Ok(())
    }

    // ------------------------------------------------ lookup helpers --

    pub fn zombie(&self, id: u8) -> Option<&ZombieDef> {
        self.zombies.iter().find(|z| z.id == id)
    }

    pub fn item(&self, id: &str) -> Option<&ItemDef> {
        self.items.iter().find(|i| i.id == id)
    }

    /// (ztype, weight) in ascending id order — the auto-spawner pool.
    /// Ascending order keeps the pre-content roll sequence byte-identical.
    pub fn spawn_weights(&self) -> Vec<(u8, u32)> {
        let mut v: Vec<(u8, u32)> = self
            .zombies
            .iter()
            .filter(|z| z.spawn_weight > 0)
            .map(|z| (z.id, z.spawn_weight))
            .collect();
        v.sort_unstable_by_key(|e| e.0);
        v
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn built_in_tables_parse_and_validate() {
        let t = ContentTables::built_in();
        assert_eq!(t.zombies.len(), 4, "runner/walker/brute/spitter");
        assert_eq!(t.items.len(), 4, "coin/bandage/ammo_box/scrap_metal");
    }

    /// The migration baseline: the tables must mirror world.rs's former
    /// hard-coded constants exactly, or same-seed runs would drift.
    #[test]
    fn built_in_matches_pre_content_constants() {
        let t = ContentTables::built_in();
        let stats = |id: u8| {
            let z = t.zombie(id).unwrap();
            (z.walk, z.run, z.max_hp, z.damage)
        };
        assert_eq!(stats(0), (2.2, 5.4, 40.0, 10.0), "runner");
        assert_eq!(stats(1), (1.7, 4.0, 60.0, 15.0), "walker");
        assert_eq!(stats(2), (1.3, 3.1, 150.0, 26.0), "brute");
        assert_eq!(stats(3), (1.3, 3.4, 45.0, 12.0), "spitter");
        assert_eq!(t.spawn_weights(), vec![(0, 3), (1, 5), (2, 2)]);
        assert_eq!(t.raid.spawning.interval_start, 5.0);
        assert_eq!(t.raid.spawning.interval_end, 2.2);
        assert_eq!(t.raid.spawning.max_alive_start, 6.0);
        assert_eq!(t.raid.spawning.max_alive_end, 14.0);
        assert_eq!(t.raid.spawning.ramp_seconds, 360.0);
        assert_eq!(t.raid.spawning.min_spawn_dist, 18.0);
        assert_eq!(t.raid.clock.run_limit, 480.0);
        assert_eq!(t.raid.clock.frenzy_grace, 90.0);
        assert_eq!(t.raid.hit_rules.max_rate, 20.0);
        assert_eq!(t.raid.hit_rules.max_damage, 80.0);
        assert_eq!(t.raid.hit_rules.max_range, 80.0);
        assert_eq!(t.raid.loot.coin_chance_pct, 30);
        assert_eq!(t.raid.loot.coin_amount_min, 30);
        assert_eq!(t.raid.loot.coin_amount_max, 79);
    }

    #[test]
    fn shop_items_are_purchasable() {
        // commercialization hook: the shop table is queryable by id
        let t = ContentTables::built_in();
        let bandage = t.item("bandage").expect("bandage exists");
        assert!(bandage.shop.purchasable && bandage.shop.price > 0);
        let coin = t.item("coin").expect("coin exists");
        assert!(!coin.shop.purchasable, "drop currency is not for sale");
    }

    #[test]
    fn duplicate_zombie_id_rejected() {
        let mut z = ZOMBIES_TOML.to_string();
        z.push_str("\n[[zombie]]\nid = 1\nkey = \"dupe\"\nwalk = 1.0\nrun = 2.0\nmax_hp = 10.0\ndamage = 1.0\n");
        let err = ContentTables::load_validated(&z, ITEMS_TOML, RAID_TOML).unwrap_err();
        assert!(err.0.contains("duplicated"), "{err}");
    }

    #[test]
    fn duplicate_item_id_rejected() {
        let mut i = ITEMS_TOML.to_string();
        i.push_str("\n[[item]]\nid = \"coin\"\nname = \"dupe\"\nkind = \"currency\"\n");
        let err = ContentTables::load_validated(ZOMBIES_TOML, &i, RAID_TOML).unwrap_err();
        assert!(err.0.contains("duplicated"), "{err}");
    }

    #[test]
    fn unknown_item_kind_rejected() {
        let mut i = ITEMS_TOML.to_string();
        i.push_str("\n[[item]]\nid = \"new_thing\"\nname = \"x\"\nkind = \"pet\"\n");
        let err = ContentTables::load_validated(ZOMBIES_TOML, &i, RAID_TOML).unwrap_err();
        assert!(err.0.contains("unknown kind"), "{err}");
    }

    #[test]
    fn purchasable_requires_positive_price() {
        let i = ITEMS_TOML.replace("price = 120", "price = 0");
        assert!(i.contains("price = 0"), "sanity: mutation applied");
        let err = ContentTables::load_validated(ZOMBIES_TOML, &i, RAID_TOML).unwrap_err();
        assert!(err.0.contains("purchasable requires price > 0"), "{err}");
    }

    #[test]
    fn walk_must_not_exceed_run() {
        let mut z = ZOMBIES_TOML.to_string();
        z.push_str("\n[[zombie]]\nid = 9\nkey = \"too_fast\"\nwalk = 5.0\nrun = 2.0\nmax_hp = 10.0\ndamage = 1.0\n");
        let err = ContentTables::load_validated(&z, ITEMS_TOML, RAID_TOML).unwrap_err();
        assert!(err.0.contains("walk must be in (0, run]"), "{err}");
    }

    #[test]
    fn bad_spawn_interval_rejected() {
        let r = RAID_TOML.replace("interval_start = 5.0", "interval_start = 2.0");
        assert!(r.contains("interval_start = 2.0"), "sanity: mutation applied");
        let err = ContentTables::load_validated(ZOMBIES_TOML, ITEMS_TOML, &r).unwrap_err();
        assert!(err.0.contains("interval_start > interval_end"), "{err}");
    }

    #[test]
    fn all_zero_weights_rejected() {
        let z = ZOMBIES_TOML
            .replace("spawn_weight = 3", "spawn_weight = 0")
            .replace("spawn_weight = 5", "spawn_weight = 0")
            .replace("spawn_weight = 2", "spawn_weight = 0");
        let err = ContentTables::load_validated(&z, ITEMS_TOML, RAID_TOML).unwrap_err();
        assert!(err.0.contains("spawn_weight > 0"), "{err}");
    }

    #[test]
    fn non_spawner_zombies_are_excluded_from_weights() {
        let t = ContentTables::built_in();
        assert!(t.spawn_weights().iter().all(|(id, _)| *id != 3));
    }
}
