#!/usr/bin/env python3
"""
key_admin.py — Secure CLI tool for cmblaw.ai API key provisioning

Usage:
    python key_admin.py create-api-key --org "Acme Corp" --email "admin@acme.com"
    python key_admin.py create-api-key --org "Acme Corp" --email "admin@acme.com" --ips "1.2.3.4,5.6.7.8"
    python key_admin.py create-admin-key --name "Josh Clayton"
    python key_admin.py list-keys
    python key_admin.py revoke-key --prefix "cmb_live_abc123"
    python key_admin.py unpause-key --prefix "cmb_live_abc123"
    python key_admin.py rotate-hmac --new-secret "your-new-secret"
"""

import argparse
import json
import sys
import os
from datetime import datetime, timezone

# Ensure we can import from the same directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import (
    get_db, init_db, hash_api_key, generate_api_key, generate_admin_key,
    log_audit_event
)


def cmd_create_api_key(args):
    """Create a new API key for a client organization."""
    conn = get_db()
    try:
        key, key_hash = generate_api_key()
        now = datetime.now(timezone.utc).isoformat()

        scopes = json.dumps(args.scopes.split(",")) if args.scopes else '["read","write"]'
        allowed_ips = json.dumps(args.ips.split(",")) if args.ips else None

        conn.execute("""
            INSERT INTO api_keys (key_hash, key_prefix, org_name, org_email, scopes, active,
                                 allowed_ips, created_at)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?)
        """, (key_hash, key[:16], args.org, args.email, scopes, allowed_ips, now))
        conn.commit()

        log_audit_event(conn, "API_KEY_PROVISIONED", "cli_admin",
                       details=f"Key created for {args.org} ({args.email})")

        print("\n" + "=" * 60)
        print("  NEW API KEY CREATED")
        print("=" * 60)
        print(f"  Organization: {args.org}")
        print(f"  Email:        {args.email}")
        print(f"  Scopes:       {scopes}")
        if allowed_ips:
            print(f"  Allowed IPs:  {allowed_ips}")
        print(f"  Key Prefix:   {key[:16]}")
        print()
        print(f"  API KEY: {key}")
        print()
        print("  IMPORTANT: Store this key securely.")
        print("  It cannot be retrieved again.")
        print("=" * 60 + "\n")
    finally:
        conn.close()


def cmd_create_admin_key(args):
    """Create a new admin key."""
    conn = get_db()
    try:
        key, key_hash = generate_admin_key()
        now = datetime.now(timezone.utc).isoformat()

        conn.execute("""
            INSERT INTO admin_keys (key_hash, key_prefix, admin_name, permissions, active, created_at)
            VALUES (?, ?, ?, ?, 1, ?)
        """, (key_hash, key[:16], args.name, '["all"]', now))
        conn.commit()

        log_audit_event(conn, "ADMIN_KEY_PROVISIONED", "cli_admin",
                       details=f"Admin key created for {args.name}")

        print("\n" + "=" * 60)
        print("  NEW ADMIN KEY CREATED")
        print("=" * 60)
        print(f"  Admin Name:  {args.name}")
        print(f"  Key Prefix:  {key[:16]}")
        print()
        print(f"  ADMIN KEY: {key}")
        print()
        print("  IMPORTANT: Store this key securely.")
        print("  It cannot be retrieved again.")
        print("=" * 60 + "\n")
    finally:
        conn.close()


def cmd_list_keys(args):
    """List all API keys (without revealing hashes)."""
    conn = get_db()
    try:
        print("\n  API KEYS")
        print("  " + "-" * 80)
        print(f"  {'Prefix':<18} {'Organization':<25} {'Email':<30} {'Active':<8} {'Abuse':<7}")
        print("  " + "-" * 80)

        rows = conn.execute("SELECT * FROM api_keys ORDER BY created_at DESC").fetchall()
        for row in rows:
            active = "Yes" if row["active"] else "REVOKED"
            abuse = "PAUSED" if row["paused_for_abuse"] else "-"
            print(f"  {row['key_prefix']:<18} {row['org_name'][:24]:<25} {row['org_email'][:29]:<30} {active:<8} {abuse:<7}")

        print(f"\n  Total: {len(rows)} keys\n")

        if args.admins:
            print("  ADMIN KEYS")
            print("  " + "-" * 60)
            print(f"  {'Prefix':<18} {'Name':<25} {'Active':<8}")
            print("  " + "-" * 60)

            admin_rows = conn.execute("SELECT * FROM admin_keys ORDER BY created_at DESC").fetchall()
            for row in admin_rows:
                active = "Yes" if row["active"] else "REVOKED"
                print(f"  {row['key_prefix']:<18} {row['admin_name'][:24]:<25} {active:<8}")
            print(f"\n  Total: {len(admin_rows)} admin keys\n")
    finally:
        conn.close()


def cmd_revoke_key(args):
    """Revoke an API key by prefix."""
    conn = get_db()
    try:
        row = conn.execute("SELECT id, org_name, active FROM api_keys WHERE key_prefix=?",
                          (args.prefix,)).fetchone()
        if not row:
            print(f"\n  ERROR: No API key found with prefix '{args.prefix}'\n")
            return

        if not row["active"]:
            print(f"\n  Key for {row['org_name']} is already revoked.\n")
            return

        reason = args.reason or "Revoked via CLI"
        conn.execute("UPDATE api_keys SET active=0, revoked_at=?, revoke_reason=? WHERE id=?",
                     (datetime.now(timezone.utc).isoformat(), reason, row["id"]))
        conn.commit()

        log_audit_event(conn, "API_KEY_REVOKED_CLI", "cli_admin",
                       details=f"Revoked key for {row['org_name']}: {reason}")

        print(f"\n  Key for {row['org_name']} has been REVOKED.")
        print(f"  Reason: {reason}\n")
    finally:
        conn.close()


def cmd_unpause_key(args):
    """Remove abuse pause from an API key."""
    conn = get_db()
    try:
        row = conn.execute("SELECT id, org_name, paused_for_abuse FROM api_keys WHERE key_prefix=?",
                          (args.prefix,)).fetchone()
        if not row:
            print(f"\n  ERROR: No API key found with prefix '{args.prefix}'\n")
            return

        if not row["paused_for_abuse"]:
            print(f"\n  Key for {row['org_name']} is not currently paused.\n")
            return

        conn.execute("UPDATE api_keys SET paused_for_abuse=0 WHERE id=?", (row["id"],))
        conn.commit()

        log_audit_event(conn, "API_KEY_UNPAUSED_CLI", "cli_admin",
                       details=f"Unpaused key for {row['org_name']}")

        print(f"\n  Key for {row['org_name']} has been UNPAUSED.\n")
    finally:
        conn.close()


def cmd_remove_demo_seeds(args):
    """Remove demo/test API keys from the database."""
    conn = get_db()
    try:
        # Find demo keys
        demo_keys = conn.execute(
            "SELECT id, key_prefix, org_name FROM api_keys WHERE org_name LIKE '%demo%' OR org_name LIKE '%test%' OR key_prefix LIKE '%demo%' OR key_prefix LIKE '%test%'"
        ).fetchall()

        demo_admin_keys = conn.execute(
            "SELECT id, key_prefix, admin_name FROM admin_keys WHERE key_prefix LIKE '%test%' OR admin_name LIKE '%test%'"
        ).fetchall()

        if not demo_keys and not demo_admin_keys:
            print("\n  No demo/test keys found.\n")
            return

        print("\n  The following demo/test keys will be removed:")
        for key in demo_keys:
            print(f"    API Key: {key['key_prefix']} ({key['org_name']})")
        for key in demo_admin_keys:
            print(f"    Admin Key: {key['key_prefix']} ({key['admin_name']})")

        if not args.force:
            confirm = input("\n  Type 'yes' to confirm removal: ")
            if confirm.lower() != "yes":
                print("  Aborted.\n")
                return

        for key in demo_keys:
            conn.execute("DELETE FROM api_keys WHERE id=?", (key["id"],))
        for key in demo_admin_keys:
            conn.execute("DELETE FROM admin_keys WHERE id=?", (key["id"],))

        conn.commit()

        log_audit_event(conn, "DEMO_SEEDS_REMOVED", "cli_admin",
                       details=f"Removed {len(demo_keys)} demo API keys and {len(demo_admin_keys)} demo admin keys")

        print(f"\n  Removed {len(demo_keys)} API key(s) and {len(demo_admin_keys)} admin key(s).")
        print("  Run 'python key_admin.py create-admin-key' to create a production admin key.\n")
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="cmblaw.ai — Secure Key Provisioning CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python key_admin.py create-api-key --org "Acme Corp" --email "admin@acme.com"
  python key_admin.py create-api-key --org "Acme Corp" --email "admin@acme.com" --ips "1.2.3.4,5.6.7.8"
  python key_admin.py create-admin-key --name "Josh Clayton"
  python key_admin.py list-keys --admins
  python key_admin.py revoke-key --prefix "cmb_live_abc123" --reason "Client offboarded"
  python key_admin.py unpause-key --prefix "cmb_live_abc123"
  python key_admin.py remove-demo-seeds --force
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # create-api-key
    p_create = subparsers.add_parser("create-api-key", help="Create a new API key")
    p_create.add_argument("--org", required=True, help="Organization name")
    p_create.add_argument("--email", required=True, help="Organization contact email")
    p_create.add_argument("--ips", help="Comma-separated allowed IP addresses (optional)")
    p_create.add_argument("--scopes", help="Comma-separated scopes (default: read,write)")

    # create-admin-key
    p_admin = subparsers.add_parser("create-admin-key", help="Create a new admin key")
    p_admin.add_argument("--name", required=True, help="Admin name (e.g., 'Brannon McKay')")

    # list-keys
    p_list = subparsers.add_parser("list-keys", help="List all API keys")
    p_list.add_argument("--admins", action="store_true", help="Also show admin keys")

    # revoke-key
    p_revoke = subparsers.add_parser("revoke-key", help="Revoke an API key")
    p_revoke.add_argument("--prefix", required=True, help="Key prefix (first 16 chars)")
    p_revoke.add_argument("--reason", help="Reason for revocation")

    # unpause-key
    p_unpause = subparsers.add_parser("unpause-key", help="Remove abuse pause from a key")
    p_unpause.add_argument("--prefix", required=True, help="Key prefix (first 16 chars)")

    # remove-demo-seeds
    p_demo = subparsers.add_parser("remove-demo-seeds", help="Remove demo/test keys")
    p_demo.add_argument("--force", action="store_true", help="Skip confirmation prompt")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Ensure database is initialized
    init_db()

    commands = {
        "create-api-key": cmd_create_api_key,
        "create-admin-key": cmd_create_admin_key,
        "list-keys": cmd_list_keys,
        "revoke-key": cmd_revoke_key,
        "unpause-key": cmd_unpause_key,
        "remove-demo-seeds": cmd_remove_demo_seeds,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
