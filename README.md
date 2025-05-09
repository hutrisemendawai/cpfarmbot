
---

## 📊 CP-FarmBot

A **Python-based Telegram bot** that ingests your daily CSV exports of chick performance, stores raw data in a database, and broadcasts concise barn-by-barn summaries to every subscriber.

---

## 🔍 Features

- **CSV Parsing**  
  - Handles multi-line, two-row headers exported from your farm management system  
  - Automatically flattens nested headers into human-readable column names  
- **Data Storage**  
  - Saves raw CSV data and summaries in any SQLAlchemy-compatible database (SQLite by default)  
- **Broadcasting**  
  - Sends emoji-rich reports via Telegram to all registered users  
  - Auto-chunks messages to respect Telegram’s 4 096-character limit  
- **Extensible**  
  - Easily adapt to auto-fetch data via API/FTP with an APScheduler hook  

---

## 🚀 Getting Started

### 1. Prerequisites

- **Python ≥ 3.8**  
- A Telegram bot token (create one with [@BotFather](https://t.me/BotFather))  
- SQLite (or any other SQL database supported by SQLAlchemy)  

### 2. Installation

```bash
# Clone the repo
git clone https://github.com/your-username/cp-farmbot.git
cd cp-farmbot

# Create and activate a virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

Your `requirements.txt` should include at least:

```
pandas
SQLAlchemy
python-telegram-bot==22.0
APScheduler       # Optional: for scheduled auto-fetching
```

### 3. Configuration

1. Copy the example config:
   ```bash
   cp config.example.py config.py
   ```
2. Open **config.py** and fill in your values:
   ```python
   BOT_TOKEN = "123456789:ABCDEF..."    # Your Telegram Bot API token
   MODE      = "manual"                 # "manual" or "auto" (when fetch_data() is implemented)
   DB_URL    = "sqlite:///data.db"      # SQLAlchemy URL for your database
   ```

### 4. Initialize Subscribers Database

Create the SQLite file and `subscribers` table to record `/start` users:

```bash
python init_subscribers.py
```

*(This script simply creates `subscribers.db` with a `subscribers(chat_id INTEGER PRIMARY KEY)` table.)*

### 5. Usage

#### Manual Mode

Parse a local CSV and broadcast summaries:

```bash
python main.py --mode manual --file ./data.csv
```

- **Reads** and flattens `data.csv`  
- **Stores** raw rows in `raw_data` table  
- **Generates** per-barn summaries  
- **Sends** emoji-rich messages to all `/start` subscribers  
- **Logs** summaries to `summaries` table  

#### Auto Mode (Future)

- Implement `fetch_data()` in `main.py` to pull from an API or FTP  
- In **config.py**, set:
  ```python
  MODE = "auto"
  ```
- Schedule executions with APScheduler or cron to run `main.py`

---

## 🛠️ How It Works

1. **`parse_csv()`**  
   - Locates the two header rows by matching “House Code”  
   - Loads headers as a Pandas `MultiIndex`  
2. **`flatten_columns()`**  
   - Forward-fills top-level header names  
   - Merges with sub-labels to create columns like  
     `Feed Used (Kg) | Qty`, `Feed Used (Kg) | Name`, etc.  
3. **`build_summaries()`**  
   - Drops extraneous header/total rows  
   - Fills barn codes into sub-rows (S00, S11, S12G)  
   - Computes key metrics per barn: live birds, mortality %, feed kg, avg BW, FCR, EEF  
   - Renders a human-friendly, emoji-rich text block  
4. **`broadcast()`**  
   - Retrieves all chat IDs from `subscribers`  
   - Splits large messages into ≤ 4 096-character chunks  
   - Sends via `telegram.Bot.send_message()`  

---

## 📱 Bot Commands

- `/start` – Register to receive daily barn summaries  
- `/stop`  – (Optional) Unregister and stop receiving messages  

> Ensure your `testing.py` hooks these commands to insert/remove chat IDs in `subscribers.db`.

---

## 🏗️ Project Layout

```
.
├── main.py                # CSV → DB → Broadcast core logic
├── testing.py             # Telegram handlers & /start command
├── init_subscribers.py    # One-off script to create subscribers DB
├── config.example.py      # Copy to config.py and customize
├── requirements.txt       # Project dependencies
└── README.md              # This document
```

---

## 🤝 Contributing

1. Fork the repo  
2. Create a new branch (`git checkout -b feature/my-feature`)  
3. Commit your changes (`git commit -am "Add my feature"`)  
4. Push to the branch (`git push origin feature/my-feature`)  
5. Open a Pull Request  

Please ensure any new code is covered by tests where applicable.

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for more details.
