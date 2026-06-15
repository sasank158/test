"""
SQLite storage layer.

Everything is kept in one small file: data/flags.db. There's no separate
database server to install — SQLite ships with Python.
"""

import json
import os
import sqlite3
from typing import List, Optional

from models import FeatureFlag, RolloutRule, ConfigValue

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "flags.db")


def get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables if they don't exist yet, and seed demo data."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS flags (
            name TEXT PRIMARY KEY,
            enabled INTEGER NOT NULL DEFAULT 0,
            rollout_type TEXT NOT NULL DEFAULT 'everyone',
            percentage INTEGER NOT NULL DEFAULT 100,
            beta_user_ids TEXT NOT NULL DEFAULT '[]'
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS configs (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            value_type TEXT NOT NULL DEFAULT 'string'
        )
        """
    )
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM flags")
    if cur.fetchone()[0] == 0:
        _seed_defaults(conn)

    conn.close()


def _seed_defaults(conn: sqlite3.Connection) -> None:
    """Insert the demo flags/configs shown in the project brief."""
    cur = conn.cursor()
    cur.executemany(
        "INSERT INTO flags (name, enabled, rollout_type, percentage, beta_user_ids) "
        "VALUES (?, ?, ?, ?, ?)",
        [
            ("new_checkout_flow", 1, "beta_only", 100, json.dumps(["beta_user_1", "beta_user_2"])),
            ("dark_mode_beta", 0, "everyone", 100, json.dumps([])),
            ("ai_recommendations", 1, "percentage", 10, json.dumps([])),
        ],
    )
    cur.executemany(
        "INSERT INTO configs (key, value, value_type) VALUES (?, ?, ?)",
        [
            ("welcome_message", "Hello, World!", "string"),
            ("max_login_attempts", "5", "number"),
        ],
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Row <-> model conversion
# ---------------------------------------------------------------------------
def _row_to_flag(row: sqlite3.Row) -> FeatureFlag:
    return FeatureFlag(
        name=row["name"],
        enabled=bool(row["enabled"]),
        rollout=RolloutRule(
            type=row["rollout_type"],
            percentage=row["percentage"],
            beta_user_ids=json.loads(row["beta_user_ids"]),
        ),
    )


def _row_to_config(row: sqlite3.Row) -> ConfigValue:
    value_type = row["value_type"]
    raw = row["value"]
    if value_type == "number":
        value: float = float(raw)
        if value.is_integer():
            value = int(value)  # store "5" not "5.0"
    else:
        value = raw
    return ConfigValue(key=row["key"], value=value, value_type=value_type)


# ---------------------------------------------------------------------------
# Flags
# ---------------------------------------------------------------------------
def get_all_flags() -> List[FeatureFlag]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM flags ORDER BY name").fetchall()
    conn.close()
    return [_row_to_flag(r) for r in rows]


def get_flag(name: str) -> Optional[FeatureFlag]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM flags WHERE name = ?", (name,)).fetchone()
    conn.close()
    return _row_to_flag(row) if row else None


def create_flag(flag: FeatureFlag) -> FeatureFlag:
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO flags (name, enabled, rollout_type, percentage, beta_user_ids) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            flag.name,
            int(flag.enabled),
            flag.rollout.type,
            flag.rollout.percentage,
            json.dumps(flag.rollout.beta_user_ids),
        ),
    )
    conn.commit()
    conn.close()
    return flag


def toggle_flag(name: str) -> Optional[FeatureFlag]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM flags WHERE name = ?", (name,)).fetchone()
    if row is None:
        conn.close()
        return None

    new_value = 0 if row["enabled"] else 1
    conn.execute("UPDATE flags SET enabled = ? WHERE name = ?", (new_value, name))
    conn.commit()

    row = conn.execute("SELECT * FROM flags WHERE name = ?", (name,)).fetchone()
    conn.close()
    return _row_to_flag(row)


def update_flag_rollout(name: str, rollout: RolloutRule) -> Optional[FeatureFlag]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM flags WHERE name = ?", (name,)).fetchone()
    if row is None:
        conn.close()
        return None

    conn.execute(
        "UPDATE flags SET rollout_type = ?, percentage = ?, beta_user_ids = ? WHERE name = ?",
        (rollout.type, rollout.percentage, json.dumps(rollout.beta_user_ids), name),
    )
    conn.commit()

    row = conn.execute("SELECT * FROM flags WHERE name = ?", (name,)).fetchone()
    conn.close()
    return _row_to_flag(row)


def delete_flag(name: str) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM flags WHERE name = ?", (name,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Configs
# ---------------------------------------------------------------------------
def get_all_configs() -> List[ConfigValue]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM configs ORDER BY key").fetchall()
    conn.close()
    return [_row_to_config(r) for r in rows]


def get_config(key: str) -> Optional[ConfigValue]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM configs WHERE key = ?", (key,)).fetchone()
    conn.close()
    return _row_to_config(row) if row else None


def create_config(config: ConfigValue) -> ConfigValue:
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO configs (key, value, value_type) VALUES (?, ?, ?)",
        (config.key, str(config.value), config.value_type),
    )
    conn.commit()
    conn.close()
    return config


def update_config(key: str, value, value_type: str) -> Optional[ConfigValue]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM configs WHERE key = ?", (key,)).fetchone()
    if row is None:
        conn.close()
        return None

    conn.execute(
        "UPDATE configs SET value = ?, value_type = ? WHERE key = ?",
        (str(value), value_type, key),
    )
    conn.commit()

    row = conn.execute("SELECT * FROM configs WHERE key = ?", (key,)).fetchone()
    conn.close()
    return _row_to_config(row)


def delete_config(key: str) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM configs WHERE key = ?", (key,))
    conn.commit()
    conn.close()
