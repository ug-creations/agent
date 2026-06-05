from config import PATHS
from brain import chat, clear_memory, show_memory_summary, history

print("=" * 40)
print("  AI Agent Ready")
print(f"  Desktop: {PATHS['desktop']}")
print("=" * 40)
print()
print("  Commands:")
print("  'memory'  → see what I remember")
print("  'forget'  → wipe all memory")
print("  'exit'    → quit")
print()

while True:
    user_input = input("You: ").strip()

    if not user_input:
        continue

    # ── Special commands ──────────────────────
    if user_input.lower() == "exit":
        print("Bye!")
        break

    elif user_input.lower() in ("memory", "what do you remember", "show memory"):
        show_memory_summary(history)
        continue

    elif user_input.lower() in ("forget", "clear memory", "wipe memory", "reset"):
        confirm = input("  ⚠  This will delete all memory. Type YES to confirm: ").strip()
        if confirm == "YES":
            clear_memory()
            history.clear()
        else:
            print("  Cancelled.\n")
        continue

    # ── Normal chat ───────────────────────────
    chat(user_input)
    print()