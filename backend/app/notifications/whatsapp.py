"""Notificaciones por WhatsApp usando Meta Cloud API."""

import httpx
from loguru import logger
from app.core.config import get_settings

settings = get_settings()

WHATSAPP_API_URL = "https://graph.facebook.com/v21.0"


async def send_whatsapp_notification(
    product_name: str,
    product_url: str,
    checkout_url: str | None = None,
    price: str | None = None,
    stock_change_msg: str | None = None,
):
    """Envía un mensaje de WhatsApp cuando se detecta stock o se reserva."""
    if not settings.whatsapp_token or not settings.whatsapp_phone_id:
        logger.debug("WhatsApp no configurado, saltando notificación")
        return

    try:
        # Construir mensaje
        lines = [
            "🎯 *DofiMall Sniper*",
            "",
            f"📦 *{product_name}*",
        ]
        if stock_change_msg:
            lines.append(stock_change_msg)
        if price:
            lines.append(f"💰 Precio: {price}")

        lines.extend([
            "",
            f"🔗 Producto: {product_url}",
        ])

        if checkout_url:
            lines.extend([
                "",
                f"🛒 *¡RESERVADO!* Completa el pago:",
                checkout_url,
            ])
        else:
            lines.extend([
                "",
                "✅ *¡EN STOCK!* — Revísalo rápido antes de que se agote.",
            ])

        message_body = "\n".join(lines)

        # Enviar via Meta Cloud API
        url = f"{WHATSAPP_API_URL}/{settings.whatsapp_phone_id}/messages"
        headers = {
            "Authorization": f"Bearer {settings.whatsapp_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": settings.whatsapp_to,
            "type": "text",
            "text": {"body": message_body},
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()

        logger.info(f"📱 WhatsApp enviado a {settings.whatsapp_to}")

    except Exception as e:
        logger.error(f"❌ Error enviando WhatsApp: {e}")
