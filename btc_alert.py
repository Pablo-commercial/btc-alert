import requests
import os
from datetime import datetime, timezone

THRESHOLD_PCT = 5.0          # umbral de cambio en 24h para alerta "tocha" (%)
DAILY_ALERT_HOUR_UTC = 7      # hora (UTC) a partir de la cual se manda el resumen diario
STATE_FILE = "last_daily_alert.txt"   # guarda la fecha del ultimo resumen enviado

# Se leen de variables de entorno (GitHub Secrets) - nunca hardcodear aqui
PHONE = os.environ["CALLMEBOT_PHONE"]      # ej: 34612345678 (sin '+')
APIKEY = os.environ["CALLMEBOT_APIKEY"]    # el numero que te da el bot


def get_btc_24h_change_eur():
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": "bitcoin",
        "vs_currencies": "eur",
        "include_24hr_change": "true",
    }
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()["bitcoin"]
    return data["eur"], data["eur_24h_change"]


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

    price, change = get_btc_24h_change_eur()
    print(f"[{now.isoformat()}] BTC: {price:,.0f}EUR | cambio 24h: {change:.2f}%")

    # --- Puerta 1: evento gordo, dispara siempre que se cumpla, sin limite diario ---
    if abs(change) >= THRESHOLD_PCT:
        if change > 0:
            msg = (
                f"🚀 Eh tio, BTC se ha pegado un subidon de +{change:.2f}% en 24h!\n"
                f"Ahora mismo va a {price:,.0f}€. Que ganas de que sigas asi jaja"
            )
        else:
            msg = (
                f"📉 Eh, malas noticias: BTC ha caido {change:.2f}% en 24h.\n"
                f"Precio actual: {price:,.0f}€. Aguanta el tipon 💪"
            )
        send_whatsapp(msg)
        print("Alerta de movimiento fuerte enviada.")
        return  # si ya hubo alerta fuerte, no hace falta ademas el resumen de hoy

    # --- Puerta 2: resumen diario, solo 1 vez por dia natural (UTC) ---
    if now.hour >= DAILY_ALERT_HOUR_UTC and not already_sent_today(today_str):
        msg = (
            f"👋 Buenas! Resumen del dia de BTC:\n"
            f"Precio: {price:,.0f}€ (cambio 24h: {change:+.2f}%)\n"
            f"Todo tranqui, ningun movimiento raro."
        )
        send_whatsapp(msg)
        mark_sent_today(today_str)
        print("Resumen diario enviado.")
    else:
        print("Sin alerta esta vez (ni evento fuerte, ni toca resumen diario todavia).")


if __name__ == "__main__":
    main()
