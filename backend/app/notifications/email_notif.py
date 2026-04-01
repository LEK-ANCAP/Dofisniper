"""Notificaciones por email usando SMTP."""

import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from loguru import logger
from app.core.config import get_settings

settings = get_settings()


async def send_email_notification(
    subject: str,
    product_name: str,
    product_url: str,
    checkout_url: str | None = None,
    price: str | None = None,
    stock_change_msg: str | None = None,
):
    """Envía un email de notificación cuando se detecta stock o se reserva."""
    if not settings.smtp_user or not settings.notification_email:
        logger.warning("⚠️ Email no configurado, saltando notificación")
        return

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🎯 DofiMall Sniper: {subject}"
        msg["From"] = settings.smtp_user
        msg["To"] = settings.notification_email

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #1a1a2e; color: white; padding: 20px; border-radius: 10px 10px 0 0;">
                <h1 style="margin: 0;">🎯 DofiMall Sniper</h1>
                <p style="margin: 5px 0 0; opacity: 0.8;">{subject}</p>
            </div>
            <div style="padding: 20px; background: #f5f5f5; border-radius: 0 0 10px 10px;">
                <h2 style="color: #333;">{product_name}</h2>
                {f'<p style="font-size: 16px; color: #444; background: #e2e8f0; padding: 10px; border-radius: 5px;">{stock_change_msg}</p>' if stock_change_msg else ''}
                {f'<p style="font-size: 24px; color: #e63946; font-weight: bold;">{price}</p>' if price else ''}
                <p>
                    <a href="{product_url}"
                       style="background: #457b9d; color: white; padding: 10px 20px;
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        Ver Producto
                    </a>
                </p>
                {f'''
                <p style="margin-top: 15px;">
                    <a href="{checkout_url}"
                       style="background: #e63946; color: white; padding: 12px 24px;
                              text-decoration: none; border-radius: 5px; display: inline-block;
                              font-weight: bold;">
                        🛒 Completar Pago
                    </a>
                </p>
                ''' if checkout_url else ''}
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="color: #888; font-size: 12px;">
                    Enviado automáticamente por DofiMall Sniper
                </p>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(html, "html"))

        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            use_tls=False,
            start_tls=True,
        )

        logger.info(f"📧 Email enviado a {settings.notification_email}")

    except Exception as e:
        logger.error(f"❌ Error enviando email: {e}")
