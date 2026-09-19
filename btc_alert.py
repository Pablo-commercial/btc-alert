import requests
import os
from datetime import datetime, timezone

THRESHOLD_PCT = 5.0          # umbral de cambio en 24h para alerta "tocha" (%)
DAILY_ALERT_HOUR_UTC = 7      # hora (UTC) a partir de la cual se manda el resumen diario
STATE_FILE = "last_daily_alert.txt"   # guarda la fecha del último resumen enviado

# Se leen de variables de entorno (GitHub Secrets) — nunca hardcodear aquí
PHONE = os.environ["CALLMEBOT_PHONE"]      # ej: 34612345678 (sin '+')
APIKEY = os.environ["CALLMEBOT_APIKEY"]    # el número que te da el bot


def get_btc_24h_change():
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": "bitcoin",
        "vs_currencies": "usd",
        "include_24hr_change": "true",
    }
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()["bitcoin"]
    return data["usd"], data["usd_24h_change"]


def send_whatsapp(message: str):
    url = "https://api.callmebot.com/whatsapp.php"
    params = {"phone": PHONE, "text": message, "apikey": APIKEY}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()


def already_sent_today(today_str: str) -> bool:
    if not os.path.exists(STATE_FILE):
        return False
    with open(STATE_FILE) as f:
        return f.read().strip() == today_str


def mark_sent_today(today_str: str):
    with open(STATE_FILE, "w") as f:
        f.write(today_str)


def main():
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")

    price, change = get_btc_24h_change()
    print(f"[{now.isoformat()}] BTC: ${price:,.0f} | cambio 24h: {change:.2f}%")

    # --- Puerta 1: evento "tocho", dispara siempre que se cumpla, sin límite diario ---
    if abs(change) >= THRESHOLD_PCT:
        direction = "SUBIDA" if change > 0 else "BAJADA"
        msg = (
            f"🚨 BTC {direction} fuerte: {change:+.2f}% en 24h\n"
            f"Precio actual: ${price:,.0f}"
        )
        send_whatsapp(msg)
        print("Alerta de movimiento fuerte enviada.")
        return  # si ya hubo alerta fuerte, no hace falta además el resumen de hoy

    # --- Puerta 2: resumen diario, solo 1 vez por día natural (UTC) ---
    if now.hour >= DAILY_ALERT_HOUR_UTC and not already_sent_today(today_str):
        msg = f"📊 Resumen diario BTC\nPrecio: ${price:,.0f}\nCambio 24h: {change:+.2f}%"
        send_whatsapp(msg)
        mark_sent_today(today_str)
        print("Resumen diario enviado.")
    else:
        print("Sin alerta esta vez (ni evento fuerte, ni toca resumen diario todavía).")


if __name__ == "__main__":
    main()
