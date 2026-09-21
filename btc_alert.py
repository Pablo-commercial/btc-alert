import requests
import os
from datetime import datetime
from zoneinfo import ZoneInfo

THRESHOLD_1H_PCT = 3.0          # umbral de cambio en la ultima hora para alerta "tocha" (%)
DAILY_ALERT_HOUR_MADRID = 9     # a partir de esta hora LOCAL de Espana se manda el resumen
STATE_FILE = "last_daily_alert.txt"   # guarda la fecha del ultimo resumen enviado

# Se leen de variables de entorno (GitHub Secrets) - nunca hardcodear aqui
PHONE = os.environ["CALLMEBOT_PHONE"]      # ej: 34612345678 (sin '+')
APIKEY = os.environ["CALLMEBOT_APIKEY"]    # el numero que te da el bot


def get_btc_data_eur():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "eur",
        "ids": "bitcoin",
        "price_change_percentage": "1h,24h",
    }
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()[0]
    price = data["current_price"]
    change_1h = data["price_change_percentage_1h_in_currency"]
    change_24h = data["price_change_percentage_24h_in_currency"]
    return price, change_1h, change_24h


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
    now_madrid = datetime.now(ZoneInfo("Europe/Madrid"))
    today_str = now_madrid.strftime("%Y-%m-%d")

    price, change_1h, change_24h = get_btc_data_eur()
    print(
        f"[{now_madrid.isoformat()}] BTC: {price:,.0f}EUR | "
        f"cambio 1h: {change_1h:.2f}% | cambio 24h: {change_24h:.2f}%"
    )

    # --- Puerta 1: movimiento fuerte en la ULTIMA HORA, sin limite diario ---
    if abs(change_1h) >= THRESHOLD_1H_PCT:
        if change_1h > 0:
            msg = (
                f"🚀 Eh tio, BTC se ha pegado un subidon de +{change_1h:.2f}% en la ultima hora!\n"
                f"Ahora mismo va a {price:,.0f}€."
            )
        else:
            msg = (
                f"📉 Eh, BTC ha caido {change_1h:.2f}% en la ultima hora.\n"
                f"Precio actual: {price:,.0f}€. Aguanta el tipon 💪"
            )
        send_whatsapp(msg)
        print("Alerta de movimiento fuerte (1h) enviada.")
        # sin return: si ademas toca el resumen del dia, tambien se manda

    # --- Puerta 2: resumen diario, primera ejecucion A PARTIR de las 9:00 hora de Espana ---
    if now_madrid.hour >= DAILY_ALERT_HOUR_MADRID and not already_sent_today(today_str):
        msg = (
            f"👋 Buenas! Resumen del dia de BTC:\n"
            f"Precio: {price:,.0f}€ (cambio 24h: {change_24h:+.2f}%)"
        )
        send_whatsapp(msg)
        mark_sent_today(today_str)
        print("Resumen diario enviado.")
    else:
        print("No toca resumen diario (ya enviado hoy o antes de las 9:00).")


if __name__ == "__main__":
    main()
