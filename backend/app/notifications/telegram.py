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
    is_purchase: bool = False,
    quantity: int | None = None,
    warehouse: str | list | None = None,
    order_id: str | None = None,
):
    """Envía un mensaje de Telegram (Notificación de Stock o Compra Exitosa)."""
    token = settings.telegram_bot_token
    chat_id = settings.telegram_chat_id

    if not token or not chat_id:
        return

    chat_ids = [c.strip() for c in chat_id.split(",") if c.strip()]
    if not chat_ids:
        return

    if is_purchase:
        message = f"✅ <b>¡RESERVA COMPLETADA!</b>\n"
        message += f"🎯 {subject}\n\n"
        message += f"📦 <b>{product_name}</b>\n"
        if quantity:
            message += f"🔢 <b>Cantidad:</b> {quantity} uds\n"
        
        if warehouse:
            if isinstance(warehouse, list):
                # Formatear lista de almacenes JSON
                lines = []
                for wh in warehouse:
                    # wh es dict: {name, warehouse_stock, transit_stock, area}
                    stock_f = wh.get('warehouse_stock', 0)
                    stock_t = wh.get('transit_stock', 0)
                    if stock_f > 0 or stock_t > 0:
                        detail = []
                        if stock_f > 0: detail.append(f"{stock_f}U Físico")
                        if stock_t > 0: detail.append(f"{stock_t}U Tránsito")
                        lines.append(f"• {wh.get('name')}: {' y '.join(detail)}")
                
                warehouse_str = "\n".join(lines) if lines else "Sin stock desglosado"
            else:
                warehouse_str = str(warehouse)
                
            message += f"📍 <b>Almacén:</b>\n{warehouse_str}\n"

        if order_id:
            message += f"🆔 <b>Ref/Orden:</b> <code>{order_id}</code>\n"
    else:
        message = f"🎯 <b>DofiMall Sniper: {subject}</b>\n\n"
        message += f"📦 {product_name}\n"
        if stock_change_msg:
            message += f"{stock_change_msg}\n"
        if price:
            message += f"💵 {price}\n"
    
    url_to_use = checkout_url if checkout_url else product_url
    message += f"\n👉 <a href='{url_to_use}'>{'🛒 PAGAR AHORA' if checkout_url else 'Ver Producto'}</a>"

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
