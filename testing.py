# testing.py

import sqlite3
import asyncio
import config
from telegram import Bot

DB_PATH = "subscribers.db"

def init_db():
    """Create subscribers table if it doesn’t exist."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS subscribers (chat_id INTEGER PRIMARY KEY)"
    )
    conn.commit()
    conn.close()

def add_subscriber(chat_id: int):
    """Record a chat_id if new."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR IGNORE INTO subscribers (chat_id) VALUES (?)",
        (chat_id,),
    )
    conn.commit()
    conn.close()

def get_subscribers() -> list[int]:
    """Return all recorded chat_ids."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("SELECT chat_id FROM subscribers")
    ids = [row[0] for row in cur]
    conn.close()
    return ids

async def main():
    init_db()
    bot = Bot(token=config.BOT_TOKEN)
    offset = None

    print("🚀 Bot is polling for updates...")
    while True:
        # fetch updates with long-polling
        updates = await bot.get_updates(offset=offset, timeout=30)
        for upd in updates:
            offset = upd.update_id + 1
            msg = upd.message
            if not msg or not msg.text:
                continue

            chat_id = msg.chat.id
            text = msg.text.strip()

            if text == "/start":
                add_subscriber(chat_id)
                await bot.send_message(
                    chat_id=chat_id,
                    text="✅ Anda telah terdaftar untuk menerima broadcast!"
                )
            elif text.startswith("/broadcast "):
                # only allow broadcast from your own chat? Optional:
                # if chat_id != config.ADMIN_CHAT_ID: continue

                payload = text[len("/broadcast "):].strip()
                sent = 0
                for cid in get_subscribers():
                    try:
                        await bot.send_message(chat_id=cid, text=payload)
                        sent += 1
                    except:
                        pass
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"📣 Pesan terkirim ke {sent} subscriber."
                )

        # a short pause before next long-poll
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
