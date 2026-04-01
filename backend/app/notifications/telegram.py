"""Notificaciones por Telegram usando la API oficial (Bots)."""

import httpx
from loguru import logger
from app.core.config import get_settings

settings = get_settings()

async def send_telegram_notification(
    subject: str,
    product_name: str,
    product_url: str,
    checkout_url: str | None = None,
    price: str | None = None,
    stock_change_msg: str | None = None,
):
    """Envía un mensaje de Telegram cuando se detecta stock."""
    token = settings.telegram_bot_token
    chat_id = settings.telegram_chat_id

    if not token or not chat_id:
        return

    chat_ids = [c.strip() for c in chat_id.split(",") if c.strip()]
    if not chat_ids:
        return

    message = f"🎯 <b>DofiMall Sniper: {subject}</b>\n\n"
    message += f"📦 {product_name}\n"
    if stock_change_msg:
        message += f"{stock_change_msg}\n"
    if price:
        message += f"💵 {price}\n"
    
    url_to_use = checkout_url if checkout_url else product_url
    message += f"\n👉 <a href='{url_to_use}'>{'🛒 Completar Pago' if checkout_url else 'Ver Producto'}</a>"

    api_url = f"https://api.telegram.org/bot{token}/sendMessage"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            for c_id in chat_ids:
                payload = {
                    "chat_id": c_id,
                    "text": message,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": False
                }
                try:
                    response = await client.post(api_url, json=payload)
                    response.raise_for_status()
                    logger.info(f"✈️ Telegram enviado a {c_id}")
                except httpx.HTTPError as e:
                    logger.error(f"❌ Error HTTP enviando Telegram a {c_id}: {e}")
                    if hasattr(e, "response") and e.response:
                        logger.error(f"Detalle: {e.response.text}")
    except Exception as e:
        logger.error(f"❌ Error inesperado enviando Telegram: {e}")
