//! Player data persistence (README_OPS.md T6).
//!
//! Dual-track split (README_OPS.md): the content catalog lives in Git
//! (content/*.toml), player data lives here in SQLite — the smallest
//! thing that survives `kill -9` today and can be swapped for
//! PostgreSQL in year 10 without touching World or the wire protocol
//! (the `PlayerRepo` trait is the seam).
//!
//! Migrations are append-only by number (README_OPS.md invariant 3):
//! released SQL is a historical archive, never edited.

use rusqlite::Connection;
use std::sync::Mutex;

/// Storage seam: World writes every ledger mutation through to the repo
/// (write-through), reads stay on the in-session HashMap for speed.
///
/// The read methods (`balance`/`inventory`/`purchases`) have no runtime
/// caller yet: cross-session restore needs stable player identities
/// (account system, planned with the purchases-consumption step), and
/// v1 pids are client-asserted per session. They exist so the migration
/// and tooling surface is pinned now — hence the allow below.
#[allow(dead_code)]
pub trait PlayerRepo: Send + Sync {
    fn balance(&self, pid: u32, item_id: &str) -> i64;
    /// Upsert delta; rows at <= 0 are removed, mirroring the in-memory
    /// ledger's bag-cleanup so both sides never disagree on emptiness.
    fn add_item(&self, pid: u32, item_id: &str, delta: i64);
    fn inventory(&self, pid: u32) -> Vec<(String, i64)>;
    /// Append-only purchase flow — the audit trail that makes refunds,
    /// dup-exploits forensics and support tickets answerable in year 10.
    fn record_purchase(&self, pid: u32, item_id: &str, price: i64, coins_before: i64);
    fn purchases(&self, pid: u32) -> Vec<(String, i64, i64)>; // (item, price, coins_before)
    /// Find the account row for a device token (README_OPS.md T9).
    /// None = token never seen; World then calls `register`.
    fn auth(&self, token: &str) -> Option<(u32, String)>;
    /// Auth-or-create: returns the existing (uid, name) for `token` or
    /// inserts a new row with an auto "survivor#NNNN" name. Idempotent.
    fn register(&self, token: &str) -> (u32, String);
}

/// Numbered migrations. ONLY APPEND — editing a released entry breaks
/// every database that already applied it.
const MIGRATIONS: &[&str] = &[
    // 001: inventory snapshot + purchase flow
    "CREATE TABLE inventory (
        pid     INTEGER NOT NULL,
        item_id TEXT    NOT NULL,
        count   INTEGER NOT NULL,
        PRIMARY KEY (pid, item_id)
    );
    CREATE TABLE purchases (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        pid          INTEGER NOT NULL,
        item_id      TEXT    NOT NULL,
        price        INTEGER NOT NULL,
        coins_before INTEGER NOT NULL,
        applied_at   TEXT    NOT NULL DEFAULT (datetime('now'))
    );",
    // 002: account identity (README_OPS.md T9) — device-token accounts,
    // name auto-assigned ("survivor#NNNN") after INSERT OR IGNORE.
    "CREATE TABLE players (
        uid        INTEGER PRIMARY KEY AUTOINCREMENT,
        token      TEXT    NOT NULL UNIQUE,
        name       TEXT    NOT NULL DEFAULT '',
        created_at TEXT    NOT NULL DEFAULT (datetime('now'))
    );",
];

pub struct SqlitePlayerRepo {
    conn: Mutex<Connection>,
}

impl SqlitePlayerRepo {
    pub fn open(path: &str) -> rusqlite::Result<Self> {
        let conn = Connection::open(path)?;
        Self::migrate(&conn)?;
        Ok(Self { conn: Mutex::new(conn) })
    }

    #[cfg(test)]
    pub fn in_memory() -> rusqlite::Result<Self> {
        let conn = Connection::open_in_memory()?;
        Self::migrate(&conn)?;
        Ok(Self { conn: Mutex::new(conn) })
    }

    /// Apply every migration newer than what the db already has, each in
    /// its own transaction together with its schema_migrations row.
    fn migrate(conn: &Connection) -> rusqlite::Result<()> {
        conn.execute_batch(
            "CREATE TABLE IF NOT EXISTS schema_migrations (
                version    INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT (datetime('now'))
            );",
        )?;
        let applied: Vec<i64> = {
            let mut stmt = conn.prepare("SELECT version FROM schema_migrations")?;
            let rows = stmt.query_map([], |r| r.get(0))?;
            rows.collect::<Result<_, _>>()?
        };
        for (i, sql) in MIGRATIONS.iter().enumerate() {
            let version = (i + 1) as i64;
            if applied.contains(&version) {
                continue;
            }
            conn.execute_batch(&format!(
                "BEGIN; {sql} INSERT INTO schema_migrations(version) VALUES ({version}); COMMIT;"
            ))?;
        }
        Ok(())
    }
}

impl PlayerRepo for SqlitePlayerRepo {
    fn balance(&self, pid: u32, item_id: &str) -> i64 {
        let conn = self.conn.lock().unwrap();
        conn.query_row(
            "SELECT count FROM inventory WHERE pid = ?1 AND item_id = ?2",
            rusqlite::params![pid, item_id],
            |r| r.get(0),
        )
        .unwrap_or(0)
    }

    fn add_item(&self, pid: u32, item_id: &str, delta: i64) {
        let conn = self.conn.lock().unwrap();
        let _ = conn.execute_batch("BEGIN IMMEDIATE;");
        let _ = conn.execute(
            "INSERT INTO inventory(pid, item_id, count) VALUES(?1, ?2, ?3)
             ON CONFLICT(pid, item_id) DO UPDATE SET count = count + ?3",
            rusqlite::params![pid, item_id, delta],
        );
        let _ = conn.execute(
            "DELETE FROM inventory WHERE pid = ?1 AND item_id = ?2 AND count <= 0",
            rusqlite::params![pid, item_id],
        );
        let _ = conn.execute_batch("COMMIT;");
    }

    fn inventory(&self, pid: u32) -> Vec<(String, i64)> {
        let conn = self.conn.lock().unwrap();
        let Ok(mut stmt) =
            conn.prepare("SELECT item_id, count FROM inventory WHERE pid = ?1 ORDER BY item_id")
        else {
            return Vec::new();
        };
        let rows = stmt.query_map([pid], |r| {
            Ok((r.get::<_, String>(0)?, r.get::<_, i64>(1)?))
        });
        match rows {
            Ok(rows) => rows.filter_map(|r| r.ok()).collect(),
            Err(_) => Vec::new(),
        }
    }

    fn record_purchase(&self, pid: u32, item_id: &str, price: i64, coins_before: i64) {
        let conn = self.conn.lock().unwrap();
        let _ = conn.execute(
            "INSERT INTO purchases(pid, item_id, price, coins_before) VALUES(?1, ?2, ?3, ?4)",
            rusqlite::params![pid, item_id, price, coins_before],
        );
    }

    fn purchases(&self, pid: u32) -> Vec<(String, i64, i64)> {
        let conn = self.conn.lock().unwrap();
        let Ok(mut stmt) = conn.prepare(
            "SELECT item_id, price, coins_before FROM purchases WHERE pid = ?1 ORDER BY id",
        ) else {
            return Vec::new();
        };
        let rows = stmt.query_map([pid], |r| {
            Ok((
                r.get::<_, String>(0)?,
                r.get::<_, i64>(1)?,
                r.get::<_, i64>(2)?,
            ))
        });
        match rows {
            Ok(rows) => rows.filter_map(|r| r.ok()).collect(),
            Err(_) => Vec::new(),
        }
    }

    fn auth(&self, token: &str) -> Option<(u32, String)> {
        let conn = self.conn.lock().unwrap();
        conn.query_row(
            "SELECT uid, name FROM players WHERE token = ?1",
            [token],
            |r| Ok((r.get::<_, u32>(0)?, r.get::<_, String>(1)?)),
        )
        .ok()
    }

    fn register(&self, token: &str) -> (u32, String) {
        let conn = self.conn.lock().unwrap();
        // INSERT OR IGNORE makes this idempotent: a re-join with the same
        // device token finds its row instead of duplicating it.
        let _ = conn.execute(
            "INSERT OR IGNORE INTO players(token) VALUES(?1)",
            [token],
        );
        let uid: u32 = conn
            .query_row("SELECT uid FROM players WHERE token = ?1", [token], |r| r.get(0))
            .unwrap_or(0);
        // lazily backfill the display name once the uid exists
        let name: String = match conn
            .query_row("SELECT name FROM players WHERE uid = ?1", [uid], |r| {
                r.get::<_, String>(0)
            }) {
            Ok(n) if !n.is_empty() => n,
            _ => {
                let auto = format!("survivor#{uid:04}");
                let _ = conn.execute(
                    "UPDATE players SET name = ?1 WHERE uid = ?2",
                    rusqlite::params![auto, uid],
                );
                auto
            }
        };
        (uid, name)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn migrations_are_idempotent() {
        // exercise the real reopen() path via a temp file: the second
        // open must not duplicate tables nor re-apply 001.
        let dir = std::env::temp_dir().join("zraid_repo_test_migrations");
        std::fs::create_dir_all(&dir).unwrap();
        let db = dir.join("idempotent.db");
        let _ = std::fs::remove_file(&db);
        {
            let _first = SqlitePlayerRepo::open(db.to_str().unwrap()).unwrap();
        }
        let second = SqlitePlayerRepo::open(db.to_str().unwrap()).unwrap();
        // the schema still works after reopen: write + read back
        second.add_item(1, "coin", 50);
        assert_eq!(second.balance(1, "coin"), 50);
        let _ = std::fs::remove_file(&db);
    }

    #[test]
    fn add_and_balance_roundtrip() {
        let repo = SqlitePlayerRepo::in_memory().unwrap();
        assert_eq!(repo.balance(7, "coin"), 0, "missing row reads as 0");
        repo.add_item(7, "coin", 100);
        repo.add_item(7, "coin", 23);
        assert_eq!(repo.balance(7, "coin"), 123);
        assert_eq!(repo.balance(8, "coin"), 0, "per-pid isolation");
    }

    #[test]
    fn zero_and_negative_rows_are_cleaned() {
        let repo = SqlitePlayerRepo::in_memory().unwrap();
        repo.add_item(1, "bandage", 2);
        repo.add_item(1, "bandage", -2);
        assert_eq!(repo.balance(1, "bandage"), 0);
        assert!(
            repo.inventory(1).is_empty(),
            "the in-memory ledger drops empty bags; the repo must match"
        );
        repo.add_item(1, "coin", -5); // delta below zero also cleans up
        assert_eq!(repo.balance(1, "coin"), 0);
    }

    #[test]
    fn purchase_flow_is_append_only() {
        let repo = SqlitePlayerRepo::in_memory().unwrap();
        repo.record_purchase(3, "bandage", 120, 1000);
        repo.record_purchase(3, "ammo_box", 250, 880);
        assert_eq!(
            repo.purchases(3),
            vec![
                ("bandage".into(), 120, 1000),
                ("ammo_box".into(), 250, 880)
            ]
        );
        assert!(repo.purchases(4).is_empty(), "per-pid isolation");
    }
}

#[cfg(test)]
mod account_tests {
    use super::*;

    #[test]
    fn register_is_idempotent_per_token() {
        let repo = SqlitePlayerRepo::in_memory().unwrap();
        let (uid1, name1) = repo.register("device-token-a");
        let (uid2, name2) = repo.register("device-token-a");
        assert_eq!(uid1, uid2, "same token -> same account");
        assert_eq!(name1, name2);
        assert_eq!(name1, "survivor#0001");
        assert_eq!(repo.auth("device-token-a"), Some((uid1, name1)));
        assert_eq!(repo.auth("never-seen"), None);
    }

    #[test]
    fn register_assigns_distinct_uids_and_names() {
        let repo = SqlitePlayerRepo::in_memory().unwrap();
        let (a, _) = repo.register("tok-a");
        let (b, _) = repo.register("tok-b");
        assert_ne!(a, b, "uids never collide");
        assert_eq!(repo.auth("tok-b"), Some((b, format!("survivor#{b:04}"))));
    }
}
