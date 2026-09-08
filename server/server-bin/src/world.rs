//! Authoritative world state. Skeleton for migration step ③: zombie AI,
//! spawning, hit validation and the raid clock migrate here from
//! `zombie.gd` / `raid_manager.gd` (state machine logic, presentation stays
//! on the client). Determinism contract: same seed -> same spawn sequence.

use protocol::Lcg64;

pub struct World {
    pub seed: u64,
    pub tick: u64,
    rng: Lcg64,
}

impl World {
    pub fn new(seed: u64) -> Self {
        Self {
            seed,
            tick: 0,
            rng: Lcg64::new(seed),
        }
    }

    /// Advance one 20 TPS tick. Demo behavior for the skeleton: every 20th
    /// tick (1s) rolls a deterministic "spawn decision" from the seeded LCG.
    /// Real spawning replaces this in step ③.
    pub fn tick(&mut self) -> Option<u32> {
        self.tick += 1;
        if self.tick % 20 == 0 {
            Some(self.rng.next_u31())
        } else {
            None
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn rolls(seed: u64, ticks: usize) -> Vec<u32> {
        let mut w = World::new(seed);
        (0..ticks).filter_map(|_| w.tick()).collect()
    }

    #[test]
    fn same_seed_same_sequence() {
        assert_eq!(rolls(42, 100), rolls(42, 100));
    }

    #[test]
    fn different_seed_different_sequence() {
        assert_ne!(rolls(42, 100), rolls(43, 100));
    }

    #[test]
    fn roll_rate_is_one_per_second() {
        // 20 TPS * 100 ticks = 5s -> exactly 5 rolls
        assert_eq!(rolls(42, 100).len(), 5);
    }

    #[test]
    fn world_rolls_come_from_protocol_lcg() {
        // The world must consume the shared LCG in order: first 5 next_u31().
        let mut rng = Lcg64::new(42);
        let want: Vec<u32> = (0..5).map(|_| rng.next_u31()).collect();
        assert_eq!(rolls(42, 100), want);
    }
}
