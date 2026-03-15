#!/usr/bin/env python3
"""
database.py — Database layer for cmblaw.ai

SQLite with encryption-at-rest simulation (in production, use SQLCipher or PostgreSQL with TDE).
Handles: API keys, submissions, rate limits, audit logs, abuse tracking.
"""

import sqlite3
import hashlib
import hmac
import os
import json
import time
from datetime import datetime, timezone, timedelta
from contextlib import contextmanager

DB_PATH = os.environ.get("CMBLAW_DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "cmblaw_ai.db"))

# In production, this would come from a secrets manager
HMAC_SECRET = os.environ.get("CMBLAW_HMAC_SECRET", "cmblaw-ai-dev-secret-key-2026")


def get_db():
    """Get a database connection with WAL mode for concurrent reads."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_db():
    """Initialize all database tables."""
    conn = get_db()
    c = conn.cursor()

    # API Keys — hashed, never stored in plaintext
    c.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_hash TEXT UNIQUE NOT NULL,
            key_prefix TEXT NOT NULL,
            org_name TEXT NOT NULL,
            org_email TEXT NOT NULL,
            scopes TEXT DEFAULT '["read","write"]',
            active INTEGER DEFAULT 1,
            paused_for_abuse INTEGER DEFAULT 0,
            allowed_ips TEXT DEFAULT NULL,
            created_at TEXT NOT NULL,
            last_used_at TEXT DEFAULT NULL,
            revoked_at TEXT DEFAULT NULL,
            revoke_reason TEXT DEFAULT NULL,
            webhook_url TEXT DEFAULT NULL
        )
    """)

    # Admin keys — separate auth system
    c.execute("""
        CREATE TABLE IF NOT EXISTS admin_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_hash TEXT UNIQUE NOT NULL,
            key_prefix TEXT NOT NULL,
            admin_name TEXT NOT NULL,
            permissions TEXT DEFAULT '["all"]',
            active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL,
            last_used_at TEXT DEFAULT NULL
        )
    """)

    # Submissions — all service requests
    c.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT UNIQUE NOT NULL,
            matter_id TEXT,
            submission_type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending_payment',
            api_key_id INTEGER NOT NULL,
            org_name TEXT NOT NULL,
            request_data TEXT NOT NULL,
            conflict_check_result TEXT,
            pricing TEXT NOT NULL,
            payment_token TEXT,
            payment_verified INTEGER DEFAULT 0,
            payment_verified_at TEXT,
            ip_address TEXT,
            user_agent TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            processed_at TEXT,
            completed_at TEXT,
            purge_after TEXT,
            FOREIGN KEY (api_key_id) REFERENCES api_keys(id)
        )
    """)

    # Rate limits — persistent, survives restarts
    c.execute("""
        CREATE TABLE IF NOT EXISTS rate_limit_hits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_key_id INTEGER NOT NULL,
            ip_address TEXT,
            endpoint TEXT NOT NULL,
            hit_at REAL NOT NULL,
            FOREIGN KEY (api_key_id) REFERENCES api_keys(id)
        )
    """)

    # Audit log — tamper-evident with hash chain
    c.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            event_type TEXT NOT NULL,
            actor_type TEXT NOT NULL,
            actor_id TEXT,
            ip_address TEXT,
            endpoint TEXT,
            method TEXT,
            request_summary TEXT,
            response_status INTEGER,
            details TEXT,
            prev_hash TEXT,
            entry_hash TEXT NOT NULL
        )
    """)

    # IP tracking — for abuse correlation
    c.execute("""
        CREATE TABLE IF NOT EXISTS ip_tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_address TEXT NOT NULL UNIQUE,
            api_key_id INTEGER,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            total_requests INTEGER DEFAULT 1,
            blocked INTEGER DEFAULT 0,
            block_reason TEXT,
            FOREIGN KEY (api_key_id) REFERENCES api_keys(id)
        )
    """)

    # Consultation messages — async thread between AI agent and attorney
    c.execute("""
        CREATE TABLE IF NOT EXISTS consultation_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            consultation_id TEXT NOT NULL,
            sender_type TEXT NOT NULL CHECK(sender_type IN ('agent', 'attorney')),
            sender_name TEXT,
            message TEXT NOT NULL,
            attachments TEXT DEFAULT '[]',
            created_at TEXT NOT NULL,
            read_at TEXT DEFAULT NULL
        )
    """)

    # Global settings
    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    # Create indexes
    c.execute("CREATE INDEX IF NOT EXISTS idx_rate_limit_key_time ON rate_limit_hits(api_key_id, hit_at)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_rate_limit_ip_time ON rate_limit_hits(ip_address, hit_at)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_submissions_order ON submissions(order_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_submissions_key ON submissions(api_key_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_submissions_type ON submissions(submission_type)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_log(actor_type, actor_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_ip_tracking_ip ON ip_tracking(ip_address)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_ip_tracking_blocked ON ip_tracking(blocked)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_consultation_msgs ON consultation_messages(consultation_id, created_at)")

    # Initialize settings
    now = datetime.now(timezone.utc).isoformat()
    c.execute("INSERT OR IGNORE INTO settings VALUES (?, ?, ?)", ("intake_enabled", "true", now))
    c.execute("INSERT OR IGNORE INTO settings VALUES (?, ?, ?)", ("rate_limit_hourly", "30", now))
    c.execute("INSERT OR IGNORE INTO settings VALUES (?, ?, ?)", ("rate_limit_daily", "200", now))
    c.execute("INSERT OR IGNORE INTO settings VALUES (?, ?, ?)", ("abuse_threshold_per_minute", "10", now))
    c.execute("INSERT OR IGNORE INTO settings VALUES (?, ?, ?)", ("data_retention_days", "2555", now))  # ~7 years

    conn.commit()
    conn.close()


# --- Key Hashing ---

def hash_api_key(key: str) -> str:
    """Hash an API key using HMAC-SHA256. Never store keys in plaintext."""
    return hmac.new(HMAC_SECRET.encode(), key.encode(), hashlib.sha256).hexdigest()


def generate_api_key(prefix: str = "cmb") -> tuple[str, str]:
    """Generate a new API key. Returns (plaintext_key, hash)."""
    random_part = os.urandom(24).hex()
    key = f"{prefix}_live_{random_part}"
    key_hash = hash_api_key(key)
    return key, key_hash


def generate_admin_key() -> tuple[str, str]:
    """Generate a new admin key. Returns (plaintext_key, hash)."""
    random_part = os.urandom(32).hex()
    key = f"cmb_admin_{random_part}"
    key_hash = hash_api_key(key)
    return key, key_hash


# --- Audit Logging ---

def compute_audit_hash(entry: dict, prev_hash: str) -> str:
    """Compute tamper-evident hash for audit log entry."""
    payload = json.dumps({
        "timestamp": entry["timestamp"],
        "event_type": entry["event_type"],
        "actor_type": entry["actor_type"],
        "actor_id": entry.get("actor_id"),
        "details": entry.get("details"),
        "prev_hash": prev_hash
    }, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def log_audit_event(conn, event_type: str, actor_type: str, actor_id: str = None,
                    ip_address: str = None, endpoint: str = None, method: str = None,
                    request_summary: str = None, response_status: int = None,
                    details: str = None):
    """Write a tamper-evident audit log entry."""
    # Get previous hash for chain
    row = conn.execute("SELECT entry_hash FROM audit_log ORDER BY id DESC LIMIT 1").fetchone()
    prev_hash = row["entry_hash"] if row else "GENESIS"

    now = datetime.now(timezone.utc).isoformat()
    entry = {
        "timestamp": now,
        "event_type": event_type,
        "actor_type": actor_type,
        "actor_id": actor_id,
        "details": details
    }
    entry_hash = compute_audit_hash(entry, prev_hash)

    conn.execute("""
        INSERT INTO audit_log (timestamp, event_type, actor_type, actor_id, ip_address,
                              endpoint, method, request_summary, response_status, details,
                              prev_hash, entry_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (now, event_type, actor_type, actor_id, ip_address, endpoint, method,
          request_summary, response_status, details, prev_hash, entry_hash))
    conn.commit()


# --- Rate Limiting (DB-backed) ---

def check_rate_limit(conn, api_key_id: int, ip_address: str, endpoint: str) -> tuple[bool, dict]:
    """Check persistent rate limits. Returns (allowed, limits_info)."""
    now = time.time()

    # Get settings
    hourly_limit = int(conn.execute("SELECT value FROM settings WHERE key='rate_limit_hourly'").fetchone()["value"])
    daily_limit = int(conn.execute("SELECT value FROM settings WHERE key='rate_limit_daily'").fetchone()["value"])

    # Clean old entries (older than 24 hours)
    conn.execute("DELETE FROM rate_limit_hits WHERE hit_at < ?", (now - 86400,))

    # Count hourly
    hourly_count = conn.execute(
        "SELECT COUNT(*) as cnt FROM rate_limit_hits WHERE api_key_id=? AND hit_at > ?",
        (api_key_id, now - 3600)
    ).fetchone()["cnt"]

    # Count daily
    daily_count = conn.execute(
        "SELECT COUNT(*) as cnt FROM rate_limit_hits WHERE api_key_id=? AND hit_at > ?",
        (api_key_id, now - 86400)
    ).fetchone()["cnt"]

    limits = {
        "hourly": {"limit": hourly_limit, "remaining": max(0, hourly_limit - hourly_count)},
        "daily": {"limit": daily_limit, "remaining": max(0, daily_limit - daily_count)}
    }

    if hourly_count >= hourly_limit or daily_count >= daily_limit:
        return False, limits

    # Record hit
    conn.execute(
        "INSERT INTO rate_limit_hits (api_key_id, ip_address, endpoint, hit_at) VALUES (?, ?, ?, ?)",
        (api_key_id, ip_address, endpoint, now)
    )
    conn.commit()

    limits["hourly"]["remaining"] -= 1
    limits["daily"]["remaining"] -= 1
    return True, limits


# --- Abuse Detection ---

def check_abuse(conn, api_key_id: int, ip_address: str) -> tuple[bool, str]:
    """
    Multi-signal abuse detection:
    1. Per-key rapid fire (>threshold in 60s)
    2. Per-IP rapid fire across multiple keys
    3. Key already paused for abuse
    Returns (allowed, reason).
    """
    now = time.time()
    threshold = int(conn.execute(
        "SELECT value FROM settings WHERE key='abuse_threshold_per_minute'"
    ).fetchone()["value"])

    # Check if key is paused
    key_row = conn.execute("SELECT paused_for_abuse FROM api_keys WHERE id=?", (api_key_id,)).fetchone()
    if key_row and key_row["paused_for_abuse"]:
        return False, "API key paused due to abuse detection. Contact info@cmblaw.com."

    # Check if IP is blocked
    ip_row = conn.execute("SELECT blocked, block_reason FROM ip_tracking WHERE ip_address=?", (ip_address,)).fetchone()
    if ip_row and ip_row["blocked"]:
        return False, ip_row["block_reason"] or "IP address blocked."

    # Per-key minute check
    key_minute_count = conn.execute(
        "SELECT COUNT(*) as cnt FROM rate_limit_hits WHERE api_key_id=? AND hit_at > ?",
        (api_key_id, now - 60)
    ).fetchone()["cnt"]

    if key_minute_count >= threshold:
        # Pause the key
        conn.execute("UPDATE api_keys SET paused_for_abuse=1 WHERE id=?", (api_key_id,))
        log_audit_event(conn, "ABUSE_KEY_PAUSED", "system", str(api_key_id),
                       ip_address=ip_address,
                       details=f"Key paused: {key_minute_count} requests in 60s (threshold: {threshold})")
        conn.commit()
        return False, "API key paused due to rapid-fire requests."

    # Per-IP check across all keys
    ip_minute_count = conn.execute(
        "SELECT COUNT(*) as cnt FROM rate_limit_hits WHERE ip_address=? AND hit_at > ?",
        (ip_address, now - 60)
    ).fetchone()["cnt"]

    if ip_minute_count >= threshold * 2:  # Higher threshold for IP (could be shared IP)
        conn.execute("""
            INSERT INTO ip_tracking (ip_address, api_key_id, first_seen, last_seen, blocked, block_reason)
            VALUES (?, ?, ?, ?, 1, 'Rapid-fire requests from IP')
            ON CONFLICT(ip_address) DO UPDATE SET
                blocked=1, block_reason='Rapid-fire requests from IP',
                last_seen=excluded.last_seen, total_requests=total_requests+1
        """, (ip_address, api_key_id, datetime.now(timezone.utc).isoformat(),
              datetime.now(timezone.utc).isoformat()))
        log_audit_event(conn, "ABUSE_IP_BLOCKED", "system", ip_address,
                       ip_address=ip_address,
                       details=f"IP blocked: {ip_minute_count} requests in 60s across keys")
        conn.commit()
        return False, "IP address temporarily blocked due to excessive requests."

    # Update IP tracking
    now_iso = datetime.now(timezone.utc).isoformat()
    conn.execute("""
        INSERT INTO ip_tracking (ip_address, api_key_id, first_seen, last_seen, total_requests)
        VALUES (?, ?, ?, ?, 1)
        ON CONFLICT(ip_address) DO UPDATE SET
            last_seen=excluded.last_seen, total_requests=total_requests+1
    """, (ip_address, api_key_id, now_iso, now_iso))
    conn.commit()

    return True, ""


# --- Data Retention ---

def purge_expired_data(conn):
    """Purge data past its retention period."""
    retention_days = int(conn.execute(
        "SELECT value FROM settings WHERE key='data_retention_days'"
    ).fetchone()["value"])

    cutoff = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat()

    # Purge old submissions
    purged = conn.execute(
        "DELETE FROM submissions WHERE created_at < ? AND purge_after IS NOT NULL AND purge_after < ?",
        (cutoff, datetime.now(timezone.utc).isoformat())
    ).rowcount

    # Purge old rate limit hits (always keep 7 days max)
    conn.execute("DELETE FROM rate_limit_hits WHERE hit_at < ?", (time.time() - 604800,))

    # Log the purge
    if purged > 0:
        log_audit_event(conn, "DATA_PURGE", "system",
                       details=f"Purged {purged} submissions older than {retention_days} days")

    conn.commit()
    return purged


# --- Settings ---

def get_setting(conn, key: str) -> str:
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else None


def set_setting(conn, key: str, value: str):
    conn.execute(
        "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
        (key, value, datetime.now(timezone.utc).isoformat())
    )
    conn.commit()


# --- Seed Demo Data ---

def seed_demo_data():
    """Create demo API key and admin key for testing."""
    conn = get_db()

    # Check if already seeded
    if conn.execute("SELECT COUNT(*) as cnt FROM api_keys").fetchone()["cnt"] > 0:
        conn.close()
        return

    # Create demo API key
    demo_key = "cmb_live_demo_key_for_testing_only"
    demo_hash = hash_api_key(demo_key)
    now = datetime.now(timezone.utc).isoformat()

    conn.execute("""
        INSERT INTO api_keys (key_hash, key_prefix, org_name, org_email, scopes, active, created_at)
        VALUES (?, ?, ?, ?, ?, 1, ?)
    """, (demo_hash, "cmb_live_demo", "Demo Organization", "demo@example.com", '["read","write"]', now))

    # Create admin key
    admin_key = "cmb_admin_master_key_for_testing"
    admin_hash = hash_api_key(admin_key)
    conn.execute("""
        INSERT INTO admin_keys (key_hash, key_prefix, admin_name, permissions, active, created_at)
        VALUES (?, ?, ?, ?, 1, ?)
    """, (admin_hash, "cmb_admin_master", "Brannon McKay", '["all"]', now))

    conn.commit()

    log_audit_event(conn, "SYSTEM_SEED", "system", details="Demo API key and admin key created")

    conn.close()
    print(f"Demo API key: {demo_key}")
    print(f"Admin key: {admin_key}")


if __name__ == "__main__":
    init_db()
    seed_demo_data()
    print("Database initialized successfully.")
