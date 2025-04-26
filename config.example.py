# config.py

# ── Telegram & Database Configuration ────────────────────────────────────────

BOT_TOKEN = "yourtoken"
CHAT_ID   = "yourchatidfortesting"   # ← your chat_id from testing.py
DB_URL    = "yourdburl"  # e.g. sqlite:///yourdb.db

# ── Mode ─────────────────────────────────────────────────────────────────────

# "manual" = upload a CSV via --file  
# "auto"   = fetch_data() stub will run (not yet implemented)
MODE      = "manual"
