"""
agents/laptop_agent.py — Runs on Main Laptop (Windows)
Polls hub for commands and executes them using tools.py
This file replaces the old laptop_agent.py completely.
Keep your existing brain.py, tools.py, config.py — this connects to hub now.
"""

import requests
import time
import sys
import os

# ── Add parent dir to path so tools.py and config.py are found ──────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from tools import ACTIONS   # Your existing tools.py — no changes needed

# ── Config ───────────────────────────────────────────────────────────────────
HUB_IP      = "192.168.1.100"   # Your hub static IP
HUB_PORT    = 5000
HUB_URL     = f"http://{HUB_IP}:{HUB_PORT}"
DEVICE_ID   = "main_laptop"
POLL_EVERY  = 1.5   # seconds between polls — fast enough to feel instant

# ── Hub communication ────────────────────────────────────────────────────────
def fetch_command():
    """Ask hub if there's a command waiting for us."""
    try:
        r = requests.get(f"{HUB_URL}/fetch/{DEVICE_ID}", timeout=30)
        return r.json()
    except requests.exceptions.ConnectionError:
        return None
    except Exception as e:
        print(f"[Agent] Fetch error: {e}")
        return None

def ping_hub():
    try:
        r = requests.get(f"{HUB_URL}/ping", timeout=3)
        return r.status_code == 200
    except:
        return False

# ── Command execution ─────────────────────────────────────────────────────────
def execute_command(cmd):
    """
    cmd is a dict like: {"action": "open_app", "detail": "whatsapp"}
    Maps to tools.py ACTIONS dict.
    Handles special cases like file creation with content.
    """
    action = cmd.get("action", "").strip().lower()
    detail = cmd.get("detail", "").strip()

    if not action or action == "none":
        return

    print(f"[Agent] Executing: {action} → {detail}")

    fn = ACTIONS.get(action)
    if not fn:
        print(f"[Agent] Unknown action: {action}")
        return

    try:
        # ── Special cases that need detail split into kwargs ──────────────

        if action == "create_file":
            # detail format: "path|content"
            if "|" in detail:
                path, content = detail.split("|", 1)
                fn(path=path.strip(), content=content.strip())
            else:
                fn(path=detail)

        elif action == "run_command":
            # detail can be "command|cwd" or just "command"
            if "|" in detail:
                command, cwd = detail.split("|", 1)
                fn(command=command.strip(), cwd=cwd.strip())
            else:
                fn(command=detail)

        elif action == "create_vite_app":
            fn(path=detail)

        elif action == "open_app":
            fn(name=detail)

        elif action == "open_url":
            fn(url=detail)

        elif action == "open_folder":
            fn(path=detail)

        elif action == "find_folder":
            fn(name=detail)

        elif action == "create_folder":
            fn(path=detail)

        elif action == "run_npm_install":
            fn(cwd=detail)

        elif action == "run_npm_dev":
            fn(cwd=detail)

        else:
            # Generic fallback — try passing detail as first arg
            fn(detail)

    except Exception as e:
        print(f"[Agent] Error executing {action}: {e}")

# ── Main loop ─────────────────────────────────────────────────────────────────
def main():
    print("="*50)
    print(f"  JARVIS LAPTOP AGENT — Starting up")
    print(f"  Hub: {HUB_URL}")
    print(f"  Device ID: {DEVICE_ID}")
    print("="*50)

    # Wait for hub
    retries = 0
    while not ping_hub():
        retries += 1
        print(f"[Agent] Hub not reachable. Retry {retries}...")
        time.sleep(5)
        if retries >= 5:
            print("[Agent] Hub unreachable after 5 tries. Will keep retrying silently.")
            break

    print(f"[Agent] Connected to hub. Polling every {POLL_EVERY}s...")
    print("[Agent] Waiting for commands...\n")

    consecutive_errors = 0

    while True:
        try:
            cmd = fetch_command()

            if cmd and cmd.get("action"):
                execute_command(cmd)
                consecutive_errors = 0
            else:
                # No command — just wait
                pass

        except KeyboardInterrupt:
            print("\n[Agent] Stopped by user.")
            break
        except Exception as e:
            consecutive_errors += 1
            print(f"[Agent] Unexpected error: {e}")
            if consecutive_errors > 10:
                print("[Agent] Too many errors. Sleeping 30s before retry...")
                time.sleep(30)
                consecutive_errors = 0

        time.sleep(POLL_EVERY)

if __name__ == "__main__":
    main()