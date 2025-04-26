# main.py

import argparse
import asyncio
import sqlite3

import pandas as pd
from sqlalchemy import create_engine
from telegram import Bot
from telegram.error import RetryAfter

import config

DB_PATH      = "subscribers.db"
TELEGRAM_MAX = 4000  # safely under Telegram’s 4096-char limit

def get_subscribers() -> list[int]:
    with sqlite3.connect(DB_PATH) as conn:
        return [row[0] for row in conn.execute("SELECT chat_id FROM subscribers")]

def parse_csv(path: str) -> pd.DataFrame:
    # find the two-row header start
    raw = pd.read_csv(path, header=None, dtype=str)
    header_idx = (
        raw
        .apply(lambda r: r.str.contains("House Code", na=False).any(), axis=1)
        .idxmax()
    )
    # read with a 2-row header
    return pd.read_csv(path, header=[header_idx, header_idx+1], dtype=str)

def flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    # forward-fill the “top” names, then flatten to single level
    last = ""
    out = []
    for top, sub in df.columns:
        top = (top or "").strip()
        if top and not top.lower().startswith("unnamed"):
            last = top
        sub = (sub or "").strip()
        if sub and not sub.lower().startswith("unnamed"):
            out.append(f"{last} | {sub}")
        else:
            out.append(last)
    df.columns = out
    return df

def store_df(df: pd.DataFrame, table: str, replace: bool=False):
    engine = create_engine(config.DB_URL)
    df.to_sql(table, engine,
              if_exists="replace" if replace else "append",
              index=False)

def to_int(x) -> int:
    try:
        return int(str(x).replace(",", "").strip())
    except:
        return 0

def safe_str(x) -> str:
    return "" if pd.isna(x) else str(x).strip()

def build_summaries(df: pd.DataFrame) -> list[str]:
    df = df.copy()

    # 1) Forward-fill House Code so sub-rows inherit it
    df["House Code"] = df["House Code"].ffill()

    # 2) Drop the two header rows + any “Batch ID” / “All Total” junk
    df = df[df["House Code"].ne("House Code")]  
    if "Batch ID" in df.columns:
        df = df[~df["Batch ID"].isin(["Batch ID", "All Total"])]

    # 3) Keep only real numeric barn codes
    df = df[df["House Code"].str.match(r"^\d", na=False)]

    # 4) Find & sum every “Qty” under the Feed Used (Kg) block
    feed_cols = [
        c for c in df.columns
        if c.lower().startswith("feed used (kg)") and "| qty" in c.lower()
    ]
    # convert them to ints
    df[feed_cols] = df[feed_cols].fillna(0).applymap(lambda x: int(str(x).replace(",", "").strip() or 0))
    # sum per barn
    feed_sums = df.groupby("House Code")[feed_cols].sum().sum(axis=1).to_dict()

    # 5) Pick the first “main” data-row for each barn
    main = (
        df[df["Batch ID"].notna() & df["Batch ID"].str.strip().astype(bool)]
        .drop_duplicates(subset=["House Code"], keep="first")
    )

    out = []
    for _, row in main.iterrows():
        code  = row["House Code"].strip()
        breed = (row.get("Breed - Grade","") or "").strip()
        age   = (row.get("Age Days","") or "0").strip()

        ci   = int(str(row.get("Qty Chick In (no tolerancy) /Tot Order",0)).replace(",","") or 0)
        mort = int(str(row.get("MORTALITY | Dead", row.get("MORTALITY",0))).replace(",","") or 0)
        live = ci - mort
        pct  = (mort/ci*100) if ci else 0.0

        feed_kg = feed_sums.get(code, 0)

        # you can keep your AvgBW/FCR/EEF logic here …
        abw_g = float(str(row.get("Avg BW",0)).replace(",","") or 0.0)
        abw_kg = abw_g/1000

        fcr = (row.get("FCR | Act","") or "—").strip()
        eef = (row.get("EEF | Act","") or "—").strip()

        out.append(
            f"📈 Kandang {code} ({breed}) – Day {age}\n"
            f"🐣 Live birds: {live:,} (CI {ci:,} │ Mort {mort:,} │ {pct:.2f} %)\n"
            f"🌾 Feed: {feed_kg:,} kg total\n"
            f"⚖️ Avg BW: {abw_kg:.2f} kg │ FCR: {fcr} │ EEF: {eef}"
        )

    return out


def chunk_messages(lines: list[str]) -> list[str]:
    chunks, cur, length = [], [], 0
    for l in lines:
        L = len(l) + 2
        if length + L > TELEGRAM_MAX:
            chunks.append("\n\n".join(cur))
            cur, length = [], 0
        cur.append(l); length += L
    if cur:
        chunks.append("\n\n".join(cur))
    return chunks

async def broadcast(chunks: list[str]):
    subs = get_subscribers()
    if not subs:
        print("⚠️ No subscribers. Ask them to /start first.")
        return
    async with Bot(token=config.BOT_TOKEN) as bot:
        for text in chunks:
            for cid in subs:
                try:
                    await bot.send_message(chat_id=cid,
                                           text=f"<pre>{text}</pre>",
                                           parse_mode="HTML")
                except RetryAfter as e:
                    await asyncio.sleep(e.retry_after)
                    await bot.send_message(chat_id=cid,
                                           text=f"<pre>{text}</pre>",
                                           parse_mode="HTML")

async def main():
    p = argparse.ArgumentParser(description="Broadcast barn report")
    p.add_argument("--mode", choices=["manual","auto"], default=config.MODE)
    p.add_argument("--file", help="Path to CSV (required in manual mode)")
    args = p.parse_args()

    if args.mode=="manual":
        if not args.file:
            p.error("--file is required in manual mode")
        raw = parse_csv(args.file)
    else:
        raise NotImplementedError("Auto mode not implemented")

    flat = flatten_columns(raw)
    store_df(flat, "raw_data", replace=True)

    msgs   = build_summaries(flat)
    chunks = chunk_messages(msgs)
    await broadcast(chunks)

    store_df(pd.DataFrame({"summary": chunks}), "summaries")
    print("✅ Broadcast complete.")

if __name__=="__main__":
    asyncio.run(main())
