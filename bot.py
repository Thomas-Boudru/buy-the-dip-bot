import os
import time
import pandas as pd
import yfinance as yf
import ta
from datetime import datetime, timezone
from email.mime.text import MIMEText
import smtplib
from config import *

# --- 1) Récupération des tickers ---
def get_tickers_from_csv(path):
    df = pd.read_csv(path)
    tickers = df["ticker"].dropna().astype(str).str.upper().tolist()
    return [t.replace(".", "-") for t in tickers]


# --- 2) Téléchargement via Yahoo Finance ---
def download_history_safe(ticker):
    """Télécharge 6 mois de données daily, gère les erreurs réseau."""
    for attempt in range(3):
        try:
            df = yf.download(ticker, period="6mo", interval="1d", progress=False, auto_adjust=True)
            if not df.empty:
                return df
        except Exception as e:
            print(f"[{ticker}] Erreur tentative {attempt+1}: {e}")
        time.sleep(2 + attempt)  # backoff progressif
    print(f"[{ticker}] Données introuvables après 3 essais.")
    return None


# --- 3) Analyse technique ---
def analyze_ticker(ticker):
    df = download_history_safe(ticker)
    if df is None or len(df) < MIN_BARS:
        print(f"[SKIP] {ticker} (pas assez de données)")
        return None

    # --- on s'assure que Close est bien une Series 1D ---
    closes = df["Close"]
    if isinstance(closes, pd.DataFrame):
        closes = closes.squeeze()  # convertit (n,1) -> (n,)

    # --- calculs ---
    highest = closes.rolling(window=WINDOW_HIGHEST_DAYS, min_periods=WINDOW_HIGHEST_DAYS).max()
    highest_recent = highest.dropna().iloc[-1]
    last_close = closes.iloc[-1]
    drop_pct = (last_close - highest_recent) / highest_recent * 100

    # Jours depuis plus haut
    date_of_high = closes.iloc[-WINDOW_HIGHEST_DAYS:].idxmax()
    days_since_high = (closes.index[-1] - date_of_high).days

    # RSI
    rsi_series = ta.momentum.RSIIndicator(closes, window=14).rsi()
    rsi_last = rsi_series.iloc[-1] if not rsi_series.empty else None

    print(f"{ticker:<6} | Close: {last_close:>8.2f} | Drop: {drop_pct:>6.2f}% | RSI: {rsi_last:>5.1f}")

    return {
        "ticker": ticker,
        "drop_pct": round(drop_pct, 2),
        "rsi": round(rsi_last, 1) if rsi_last is not None else None,
        "days_since_high": int(days_since_high),
        "last_close": round(last_close, 2)
    }

# --- 4) Filtre ---
def is_opportunity(row):
    if not row: return False
    return row["drop_pct"] <= DROP_PCT and row["rsi"] < RSI_THRESHOLD


# --- 5) Email ---
def send_email(subject, body):
    if not EMAIL_ENABLED:
        print("[INFO] Email désactivé.")
        return
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = MAIL_TO
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
    print("[OK] Email envoyé.")


# --- 6) Main ---
def main():
    print("=== Buy the Dip (Yahoo Finance) ===")
    print(f"Seuils: drop<={DROP_PCT}% | RSI<{RSI_THRESHOLD} | Fenêtre={WINDOW_HIGHEST_DAYS}j")

    sp500 = get_tickers_from_csv("tickers_sp500.csv")
    nas100 = get_tickers_from_csv("tickers_nasdaq100.csv")
    universe = sorted(set(sp500 + nas100))
    print(f"Tickers uniques: {len(universe)}")

    print("[INFO] Analyse complète de tous les tickers.")

    opportunities = []
    for i, t in enumerate(universe, start=1):
        row = analyze_ticker(t)
        if row and is_opportunity(row):
            opportunities.append(row)
        if i % 50 == 0:
            print(f"[PROGRESS] {i}/{len(universe)} traités")
        time.sleep(0.3)

    if opportunities:
        df = pd.DataFrame(opportunities)
        os.makedirs("data", exist_ok=True)
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = f"data/opportunities_{today_str}.csv"
        df.to_csv(path, index=False)
        body = "\n".join([f"{o['ticker']}: {o['drop_pct']}% | RSI {o['rsi']}" for o in opportunities])
        send_email(f"({len(opportunities)}) Opportunités — {today_str}", body)
    else:
        print("[INFO] Aucune opportunité trouvée.")


if __name__ == "__main__":
    main()
