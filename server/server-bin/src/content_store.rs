//! Content hot-reload registry (README_OPS.md T7).
//!
//! `RwLock<Arc<ContentTables>>` snapshot swap: readers (World, once per
//! tick) clone the Arc — no blocking beyond the read lock instant; the
//! writer (admin endpoint) validates the new tables FIRST and only then
//! swaps, so a bad deploy keeps the old tables serving (fail-closed).
//!
//! Swap semantics with the raid (10-year invariant 4): a mid-raid swap
//! changes rules for NEW spawns/loot rolls from the next tick on; the
//! same-seed replay tests still pin the pre-content constants, so any
//! accidental table edit breaks CI before it breaks players.

use protocol::content::ContentTables;
use std::path::Path;
use std::sync::{Arc, RwLock};

pub struct ContentStore {
    current: RwLock<Arc<ContentTables>>,
}

impl ContentStore {
    pub fn new(initial: Arc<ContentTables>) -> Self {
        Self { current: RwLock::new(initial) }
    }

    /// Reader side: called once per World tick, returns the live snapshot.
    pub fn snapshot(&self) -> Arc<ContentTables> {
        self.current.read().unwrap().clone()
    }

    /// Writer side: atomic swap; returns the table that was replaced.
    pub fn swap(&self, next: Arc<ContentTables>) -> Arc<ContentTables> {
        let mut guard = self.current.write().unwrap();
        std::mem::replace(&mut *guard, next)
    }

    pub fn zombie_count(&self) -> usize {
        self.snapshot().zombies.len()
    }

    pub fn item_count(&self) -> usize {
        self.snapshot().items.len()
    }
}

/// Read the three TOML tables from `dir` and validate them. Any error
/// (missing file, bad schema, failed validation) returns Err and the
/// caller keeps serving the old snapshot — never a half-loaded state.
pub fn load_from_dir(dir: &Path) -> Result<Arc<ContentTables>, String> {
    let read = |name: &str| -> Result<String, String> {
        std::fs::read_to_string(dir.join(name))
            .map_err(|e| format!("{}: {e}", dir.join(name).display()))
    };
    let zombies = read("zombies.toml")?;
    let items = read("items.toml")?;
    let raid = read("raid.toml")?;
    let tables = ContentTables::load_validated(&zombies, &items, &raid)
        .map_err(|e| format!("validation failed: {e}"))?;
    Ok(Arc::new(tables))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn manifest_content_dir() -> std::path::PathBuf {
        // server-bin's manifest dir -> workspace root -> content/
        Path::new(env!("CARGO_MANIFEST_DIR"))
            .parent()
            .unwrap()
            .join("content")
    }

    #[test]
    fn swap_replaces_snapshot_atomically() {
        let store = ContentStore::new(Arc::new(ContentTables::built_in()));
        assert_eq!(store.snapshot(), Arc::new(ContentTables::built_in()));
        // swap in a modified copy (different max_hp for zombie 1)
        let mut next = ContentTables::built_in();
        next.zombies[1].max_hp = 999.0;
        let old = store.swap(Arc::new(next));
        assert_eq!(old, Arc::new(ContentTables::built_in()), "swap returns the replaced table");
        assert_eq!(store.snapshot().zombies[1].max_hp, 999.0);
    }

    #[test]
    fn load_from_dir_reads_the_real_tables() {
        let tables = load_from_dir(&manifest_content_dir()).expect("repo tables must validate");
        assert_eq!(*tables, ContentTables::built_in(), "disk tables == compiled-in tables");
    }

    #[test]
    fn load_from_dir_fails_closed() {
        assert!(load_from_dir(Path::new("definitely/not/a/dir")).is_err());
        // an empty dir exists but has no toml -> err
        let dir = std::env::temp_dir().join("zraid_store_empty_dir");
        std::fs::create_dir_all(&dir).unwrap();
        assert!(load_from_dir(&dir).is_err());
    }
}
