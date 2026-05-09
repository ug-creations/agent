"""
laptop_agent.py — Jarvis Laptop Agent V3
Specialized coding brain — handles all file creation and editing
Hub handles conversation — laptop handles all code
"""

import requests
import time
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools import ACTIONS
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
HUB_IP     = "192.168.1.100"
HUB_URL    = f"http://{HUB_IP}:5000"
DEVICE_ID  = "main_laptop"
POLL_EVERY = 1.5

# ── Local Groq ────────────────────────────────────────────────────────────────
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ── Session memory — remembers last file worked on ────────────────────────────
session = {
    "last_file": None,        # path of last created/edited file
    "last_folder": None,      # last vite/react project folder
    "history": []             # coding conversation history
}

# ── Code generation prompt ────────────────────────────────────────────────────
CODE_SYSTEM_PROMPT = """You are an expert coding AI agent on a Windows PC.
Reply ONLY with a valid JSON array. No text. No markdown. Just the array.

User paths:
Desktop:   C:\\\\Users\\\\rajarajan\\\\Desktop
Documents: C:\\\\Users\\\\rajarajan\\\\Documents

Available actions:

Create or overwrite a file with content:
{"action":"create_file","path":"C:\\\\Users\\\\rajarajan\\\\Desktop\\\\file.html","content":"FULL CODE HERE"}

Create a Vite+React app:
{"action":"create_vite_app","path":"C:\\\\Users\\\\rajarajan\\\\Desktop\\\\myapp"}

Run any terminal command:
{"action":"run_command","command":"pip install flask","cwd":"C:\\\\Users\\\\rajarajan\\\\Desktop"}

Open a file or folder:
{"action":"open_folder","path":"C:\\\\Users\\\\rajarajan\\\\Desktop"}

STRICT RULES:
- Output ONLY a valid JSON array — nothing else
- Always use double backslashes in paths
- ALWAYS write COMPLETE code — never truncate, never use ellipsis, never say 'rest of code here'
- When editing a file — rewrite the ENTIRE file with ALL changes applied
- For multi-file changes — put ALL files in ONE array

HTML/CSS DESIGN RULES:
- Google Fonts: Inter or Poppins
- Hero: full viewport height, gradient background, big bold heading, CTA button
- Nav: sticky, glassmorphism (backdrop-filter: blur)
- Cards: rounded-2xl, shadow-lg, hover lift transform translateY(-8px)
- Buttons: gradient, pill shape, hover glow box-shadow
- Fully responsive: mobile first, CSS grid and flexbox
- Modern gradients: #667eea to #764ba2 or #f093fb to #f5576c
- Smooth transitions: all 0.3s ease
- Animations: fadeIn, slideUp on load
- Always complete full page, never cut short

REACT/VITE RULES:
- After create_vite_app always overwrite src/App.jsx and src/App.css
- Use Tailwind or inline styles
- Always complete components, never truncate
"""

def call_coding_groq(user_request, existing_code=None):
    """Call Groq with coding context and optional existing file content."""
    messages = [{"role": "system", "content": CODE_SYSTEM_PROMPT}]

    # Add existing file content as context if available
    if existing_code:
        messages.append({
            "role": "system",
            "content": f"Current file content to modify:\n```\n{existing_code}\n```\nApply the user's requested changes to this file. Rewrite the complete file."
        })

    # Add coding history for context
    messages.extend(session["history"][-6:])

    # Add current request
    messages.append({"role": "user", "content": user_request})

    res = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.1,
        max_tokens=8000,
    )
    return res.choices[0].message.content.strip()

def parse_and_execute(reply):
    """Parse JSON array from Groq reply and execute all actions."""
    executed_files = []
    try:
        s = reply.index("[")
        e = reply.rindex("]") + 1
        actions = json.loads(reply[s:e])
        print(f"\n  📋 {len(actions)} task(s) to execute...\n")
        for item in actions:
            action = item.get("action", "")
            fn = ACTIONS.get(action)
            if fn:
                print(f"  ✓ {action}")
                fn(**item)
                # Track last file created
                if action == "create_file":
                    session["last_file"] = item.get("path")
                    executed_files.append(item.get("path"))
                elif action == "create_vite_app":
                    session["last_folder"] = item.get("path")
            else:
                print(f"  ✗ Unknown: {action}")
        print(f"\n  ✅ Done!\n")
    except Exception as ex:
        print(f"[Agent] Parse error: {ex}")
        print(f"[Agent] Reply was: {reply[:300]}")
    return executed_files

def read_last_file():
    """Read content of last worked on file."""
    if session["last_file"] and os.path.exists(session["last_file"]):
        try:
            with open(session["last_file"], "r", encoding="utf-8") as f:
                return f.read()
        except:
            return None
    return None

# ── Coding task detection ─────────────────────────────────────────────────────
CODING_KEYWORDS = [
    "create", "make", "build", "write", "generate", "code",
    "html", "css", "react", "python", "javascript", "js",
    "page", "app", "website", "script", "file", "dashboard",
    "add", "change", "modify", "update", "edit", "fix",
    "todo", "list", "form", "button", "colour", "color",
    "animation", "style", "component", "function", "class",
    "landing", "portfolio", "login", "signup", "navbar",
    "vite", "flask", "django", "api", "install"
]

def is_coding_task(detail):
    detail_lower = detail.lower()
    return any(k in detail_lower for k in CODING_KEYWORDS)

def is_edit_task(detail):
    """Detect if user wants to edit existing file."""
    edit_words = ["add", "change", "modify", "update", "edit", "fix",
                  "remove", "delete", "replace", "convert", "make it",
                  "turn it", "colour", "color", "animation", "style"]
    detail_lower = detail.lower()
    return any(w in detail_lower for w in edit_words)

# ── Handle coding command from hub ────────────────────────────────────────────
def handle_coding(detail):
    """
    Main coding handler.
    Detects if it's a new file or an edit to existing file.
    Reads existing file if editing, passes to Groq, executes result.
    """
    print(f"\n[Coding Agent] Request: {detail}")

    existing_code = None

    # If it looks like an edit and we have a last file — read it
    if is_edit_task(detail) and session["last_file"]:
        existing_code = read_last_file()
        if existing_code:
            print(f"[Coding Agent] Editing existing file: {session['last_file']}")
        else:
            print(f"[Coding Agent] Last file not found, creating new")

    try:
        reply = call_coding_groq(detail, existing_code)

        # Save to coding history
        session["history"].append({"role": "user", "content": detail})
        session["history"].append({"role": "assistant", "content": reply})

        # Keep history manageable
        if len(session["history"]) > 12:
            session["history"] = session["history"][-12:]

        executed = parse_and_execute(reply)
        if executed:
            print(f"[Coding Agent] Files created/modified: {executed}")

    except Exception as e:
        print(f"[Coding Agent] Error: {e}")

# ── Hub communication ─────────────────────────────────────────────────────────
def fetch_command():
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

# ── Execute any command ───────────────────────────────────────────────────────
def execute_command(cmd):
    action = cmd.get("action", "").strip().lower()
    detail = cmd.get("detail", "").strip()

    if not action or action == "none":
        return

    print(f"\n[Agent] Command: {action} → {detail[:80]}")

    # ── Route coding tasks to coding brain ───────────────────────────────
    if action == "create_file":
        if "|" in detail:
            path, content = detail.split("|", 1)
            content = content.strip()
            # If content is real code — save directly
            if len(content) > 100 and "<" in content or "def " in content or "const " in content:
                ACTIONS["create_file"](path=path.strip(), content=content)
                session["last_file"] = path.strip()
            else:
                # Description — route to coding brain
                handle_coding(f"Create file at {path.strip()}. {content}")
        else:
            handle_coding(f"Create file: {detail}")
        return

    if action == "code":
        # Hub sends action="code" for all coding tasks
        handle_coding(detail)
        return

    if action == "create_vite_app":
        session["last_folder"] = detail
        ACTIONS["create_vite_app"](path=detail)
        return

    # ── Standard actions ──────────────────────────────────────────────────
    fn = ACTIONS.get(action)
    if not fn:
        # Unknown action — try coding brain as fallback
        if is_coding_task(detail):
            handle_coding(f"{action} {detail}")
        else:
            print(f"[Agent] Unknown action: {action}")
        return

    try:
        if action == "run_command":
            if "|" in detail:
                command, cwd = detail.split("|", 1)
                fn(command=command.strip(), cwd=cwd.strip())
            else:
                fn(command=detail)
        elif action == "open_app":         fn(name=detail)
        elif action == "open_url":         fn(url=detail)
        elif action == "open_folder":      fn(path=detail)
        elif action == "find_folder":      fn(name=detail)
        elif action == "create_folder":    fn(path=detail)
        elif action == "run_npm_install":  fn(cwd=detail)
        elif action == "run_npm_dev":      fn(cwd=detail)
        else:                              fn(detail)
    except Exception as e:
        print(f"[Agent] Error: {e}")

# ── Main loop ─────────────────────────────────────────────────────────────────
def main():
    print("=" * 50)
    print("  JARVIS LAPTOP AGENT V3 — Coding Specialist")
    print(f"  Hub: {HUB_URL}")
    print("=" * 50)

    retries = 0
    while not ping_hub():
        retries += 1
        print(f"[Agent] Hub not reachable. Retry {retries}...")
        time.sleep(5)
        if retries >= 5:
            print("[Agent] Continuing anyway...")
            break

    print(f"[Agent] Ready! Polling every {POLL_EVERY}s...")
    print("[Agent] Coding specialist active — all code tasks handled locally\n")

    consecutive_errors = 0

    while True:
        try:
            cmd = fetch_command()
            if cmd and cmd.get("action"):
                execute_command(cmd)
                consecutive_errors = 0
        except KeyboardInterrupt:
            print("\n[Agent] Stopped.")
            break
        except Exception as e:
            consecutive_errors += 1
            print(f"[Agent] Error: {e}")
            if consecutive_errors > 10:
                print("[Agent] Too many errors. Sleeping 30s...")
                time.sleep(30)
                consecutive_errors = 0
        time.sleep(POLL_EVERY)

if __name__ == "__main__":
    main()
