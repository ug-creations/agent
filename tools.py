import os
import subprocess
import winreg
import threading
from config import USERNAME, PATHS


# ─────────────────────────────────────────────
#  FOLDER ACTIONS
# ─────────────────────────────────────────────

def create_folder(path, **_):
    os.makedirs(path, exist_ok=True)
    print(f"  ✓ Folder created: {path}")
    return f"✓ Folder created: {path}"

def open_folder(path, **_):
    if os.path.exists(path):
        subprocess.Popen(f'explorer "{path}"', shell=True)
        print(f"  ✓ Opened folder: {path}")
        return f"✓ Opened: {path}"
    return f"✗ Not found: {path}"

def find_folder(name, **_):
    print(f"  ⟳ Searching for folder: {name}...")
    skip = {"appdata", "python", "node_modules", "site-packages",
            ".git", "typeshed", "jedi", "__pycache__"}
    for root, dirs, _ in os.walk(f"C:\\Users\\{USERNAME}"):
        dirs[:] = [d for d in dirs if d.lower() not in skip]
        for d in dirs:
            if name.lower() in d.lower():
                path = os.path.join(root, d)
                subprocess.Popen(f'explorer "{path}"', shell=True)
                print(f"  ✓ Found and opened: {path}")
                return f"✓ Opened: {path}"
    return f"✗ Folder not found: {name}"


# ─────────────────────────────────────────────
#  FILE ACTIONS
# ─────────────────────────────────────────────

def create_file(path, content="", **_):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  ✓ File created: {path}")
    return f"✓ File created: {path}"

def read_file(path, **_):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ─────────────────────────────────────────────
#  APP OPENING  ← FIXED
# ─────────────────────────────────────────────

def open_app(name, **_):
    """
    Opens any app by name. Search order:
    1. Microsoft Store apps (AppX) — Instagram, WhatsApp, Netflix, etc.
    2. Start Menu shortcuts (.lnk) — Spotify, Discord, Steam, etc.
    3. Registry App Paths — Chrome, Firefox, VS Code, etc.
    4. Known apps dict — built-in Windows apps
    5. Direct exe search in Program Files
    """
    raw   = name.strip()
    clean = raw.lower().replace(" ", "").replace("-", "").replace("_", "")
    print(f"  ⟳ Looking for: {raw}")

    # ── 1. Microsoft Store / AppX apps ──────────────────────────────────────
    # Instagram, WhatsApp (Store version), Netflix, TikTok, etc. are AppX packages.
    # PowerShell can list them and give us the exact AppUserModelId to launch.
    try:
        ps_cmd = (
            "powershell -NoProfile -Command \""
            "Get-AppxPackage | Select-Object Name, PackageFamilyName | ConvertTo-Json\""
        )
        result = subprocess.run(ps_cmd, shell=True, capture_output=True, text=True, timeout=15)
        if result.returncode == 0 and result.stdout.strip():
            import json as _json
            packages = _json.loads(result.stdout.strip())
            if isinstance(packages, dict):
                packages = [packages]  # single result comes as dict not list
            for pkg in packages:
                pkg_name   = (pkg.get("Name") or "").lower().replace(" ", "").replace("-", "").replace("_", "")
                pkg_family = (pkg.get("PackageFamilyName") or "")
                if clean in pkg_name or pkg_name in clean:
                    # Launch via explorer shell:appid
                    launch_cmd = f'explorer.exe shell:appsFolder\\{pkg_family}!App'
                    subprocess.Popen(launch_cmd, shell=True)
                    print(f"  ✓ Opened Store app: {pkg.get('Name')}")
                    return f"✓ Opened: {pkg.get('Name')}"
    except Exception as e:
        print(f"  ⚠ AppX search failed: {e}")

    # ── 2. Start Menu shortcuts ──────────────────────────────────────────────
    # This is where WhatsApp (desktop), Spotify, Discord, etc. live on Windows
    start_menu_paths = [  # ── 2. Start Menu .lnk shortcuts
        f"C:\\Users\\{USERNAME}\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs",
        "C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs",
    ]
    for sm_root in start_menu_paths:
        if not os.path.exists(sm_root):
            continue
        for root, dirs, files in os.walk(sm_root):
            for f in files:
                if not f.endswith(".lnk"):
                    continue
                f_clean = f.lower().replace(" ", "").replace("-", "").replace("_", "").replace(".lnk", "")
                # Match if either contains the other
                if clean in f_clean or f_clean in clean:
                    full = os.path.join(root, f)
                    subprocess.Popen(f'start "" "{full}"', shell=True)
                    print(f"  ✓ Opened via Start Menu: {f}")
                    return f"✓ Opened: {f}"

    # ── 3. Registry App Paths ────────────────────────────────────────────────
    try:
        reg_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path)
        count = winreg.QueryInfoKey(key)[0]
        for i in range(count):
            k_name = winreg.EnumKey(key, i)
            k_clean = k_name.lower().replace(" ", "").replace(".exe", "")
            if clean in k_clean or k_clean in clean:
                try:
                    exe_path = winreg.QueryValue(winreg.OpenKey(key, k_name), None)
                    exe_path = exe_path.strip().strip('"')
                    if exe_path and os.path.exists(exe_path):
                        subprocess.Popen([exe_path])
                        print(f"  ✓ Opened via registry: {k_name}")
                        return f"✓ Opened: {k_name}"
                except:
                    pass
    except Exception as e:
        print(f"  ⚠ Registry check failed: {e}")

    # ── 4. Known built-in Windows apps ──────────────────────────────────────
    known_apps = {
        # System tools
        "notepad":          "notepad.exe",
        "calculator":       "calc.exe",
        "calc":             "calc.exe",
        "paint":            "mspaint.exe",
        "wordpad":          "wordpad.exe",
        "taskmanager":      "taskmgr.exe",
        "cmd":              "cmd.exe",
        "terminal":         "wt.exe",          # Windows Terminal
        "powershell":       "powershell.exe",
        "explorer":         "explorer.exe",
        "fileexplorer":     "explorer.exe",
        "controlpanel":     "control.exe",
        "settings":         "ms-settings:",    # Windows Settings
        "snipping":         "SnippingTool.exe",
        "snippingtool":     "SnippingTool.exe",

        # Browsers
        "chrome":           "chrome",
        "googlechrome":     "chrome",
        "edge":             "msedge",
        "microsoftedge":    "msedge",
        "firefox":          "firefox",

        # Dev tools
        "vscode":           "code",
        "visualstudiocode": "code",
        "code":             "code",
        "git":              "git-bash.exe",
        "gitbash":          "git-bash.exe",

        # Microsoft Office
        "word":             "winword",
        "excel":            "excel",
        "powerpoint":       "powerpnt",
        "outlook":          "outlook",

        # Media
        "vlc":              "vlc",
        "spotify":          "spotify",
    }

    if clean in known_apps:
        cmd = known_apps[clean]
        subprocess.Popen(cmd, shell=True)
        print(f"  ✓ Opened known app: {cmd}")
        return f"✓ Opened: {raw}"

    # ── 5. Search Program Files for .exe ────────────────────────────────────
    skip_dirs = {"python", "node_modules", "site-packages", "jedi",
                 "typeshed", "__pycache__", "temp", "tmp"}
    search_roots = [
        f"C:\\Users\\{USERNAME}\\AppData\\Local",
        f"C:\\Users\\{USERNAME}\\AppData\\Roaming",
        "C:\\Program Files",
        "C:\\Program Files (x86)",
    ]
    for base in search_roots:
        if not os.path.exists(base):
            continue
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d.lower() not in skip_dirs]
            for f in files:
                if not f.lower().endswith(".exe"):
                    continue
                f_clean = f.lower().replace(" ", "").replace(".exe", "")
                if clean in f_clean or f_clean in clean:
                    full = os.path.join(root, f)
                    subprocess.Popen(full)
                    print(f"  ✓ Opened via file search: {f}")
                    return f"✓ Opened: {f}"

    print(f"  ✗ Could not find app: {raw}")
    print(f"  ℹ  Tip: Make sure '{raw}' is installed on this PC")
    return f"✗ App not found: {raw}"


# ─────────────────────────────────────────────
#  WEB
# ─────────────────────────────────────────────

def open_url(url, **_):
    # Make sure url has a scheme
    if not url.startswith("http"):
        url = "https://" + url
    subprocess.Popen(f'start "" "{url}"', shell=True)
    print(f"  ✓ Opened: {url}")
    return f"✓ Opened: {url}"


# ─────────────────────────────────────────────
#  TERMINAL COMMANDS
# ─────────────────────────────────────────────

def run_command(command, cwd=None, **_):
    print(f"\n  ⟳ Running: {command}")
    if cwd:
        print(f"  📁 In folder: {cwd}")
    print("  " + "─" * 50)

    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=cwd if cwd and os.path.exists(cwd) else None,
        bufsize=1,
        universal_newlines=True,
    )

    output_lines = []
    for line in process.stdout:
        line = line.rstrip()
        if line:
            print(f"  {line}")
            output_lines.append(line)

    process.wait()
    print("  " + "─" * 50)
    if process.returncode == 0:
        print(f"  ✓ Done!\n")
    else:
        print(f"  ✗ Finished with errors (code {process.returncode})\n")

    return "\n".join(output_lines[-5:]) or "✓ Done"


def run_npm_install(cwd, **_):
    return run_command("npm install", cwd=cwd)


def run_npm_dev(cwd, **_):
    print(f"\n  ⟳ Starting dev server in: {cwd}")
    print(f"  ℹ  Press CTRL+C to stop\n")
    print("  " + "─" * 50)

    process = subprocess.Popen(
        "npm run dev",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=cwd,
        bufsize=1,
        universal_newlines=True,
    )
    for line in process.stdout:
        line = line.rstrip()
        if line:
            print(f"  {line}")
        if "localhost" in line.lower() or "local:" in line.lower():
            print(f"\n  ✓ Server is running! Open the link above\n")
    process.wait()
    return "✓ Dev server stopped"


def create_vite_app(path, template="react", **_):
    folder_name = os.path.basename(path)
    parent = os.path.dirname(path)
    os.makedirs(parent, exist_ok=True)
    print(f"\n  ⟳ Creating Vite + React app: {folder_name}")
    run_command(
        f"npm create vite@latest {folder_name} -- --template {template}",
        cwd=parent,
    )
    print(f"  ⟳ Installing dependencies...")
    run_command("npm install", cwd=path)
    print(f"  ✓ Vite app ready at: {path}")
    return f"✓ Vite app created at: {path}"


# ─────────────────────────────────────────────
#  ACTIONS MAP
# ─────────────────────────────────────────────

ACTIONS = {
    "create_folder":   create_folder,
    "create_file":     create_file,
    "read_file":       read_file,
    "open_folder":     open_folder,
    "find_folder":     find_folder,
    "open_app":        open_app,
    "open_url":        open_url,
    "run_command":     run_command,
    "run_npm_install": run_npm_install,
    "run_npm_dev":     run_npm_dev,
    "create_vite_app": create_vite_app,
}