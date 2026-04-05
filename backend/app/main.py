"""
DofiMall Sniper — Main Application

FastAPI server con scheduler integrado para monitorización periódica.
Usa la API REST de DofiMall para comprobar stock (sin Playwright).
"""

import os
import sys
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.config import get_settings
from app.core.database import init_db, get_db, async_session
from app.models.models import Product, ActionLog, ProductStatus, LogLevel, StockHistory, AppSettings
from app.schemas.schemas import DashboardStats
from app.api.products import router as products_router
from app.api.logs import router as logs_router
from app.api.settings import router as settings_router
from app.scraper.monitor import check_stock
from app.scraper.browser import browser_manager
from app.scraper.purchase import add_to_cart_and_checkout
from pydantic import BaseModel
from app.notifications.email_notif import send_email_notification
from app.notifications.whatsapp import send_whatsapp_notification
from app.notifications.telegram import send_telegram_notification
from app.core.persistent_config import get_app_config, save_app_config

settings = get_settings()
scheduler = AsyncIOScheduler()

# Crear directorio para screenshots
os.makedirs("screenshots", exist_ok=True)

# Configurar loguru
logger.add(
    "logs/sniper_{time}.log",
    rotation="1 day",
    retention="7 days",
    level="INFO",
)


# ══════════════════════════════════════════════════════════════
# Scheduled Job
# ══════════════════════════════════════════════════════════════

async def check_all_products():
    """Job principal: recorre todos los productos activos y comprueba stock via API."""
    logger.info("🔄 ═══ Iniciando ciclo de comprobación de stock ═══")

    async with async_session() as db:
        result = await db.execute(
            select(Product)
            .where(Product.is_active == True)
            .where(Product.status.in_([
                ProductStatus.MONITORING,
                ProductStatus.ERROR,
                ProductStatus.IN_STOCK,
            ]))
        )
        products = result.scalars().all()

        if not products:
            logger.info("📭 No hay productos activos para monitorizar")
            return

        logger.info(f"📋 {len(products)} productos a comprobar")

        for product in products:
            try:
                stock_result = await check_stock(None, product.url)

                # Actualizar producto en DB
                product.last_checked = datetime.now(timezone.utc)
                product.check_count += 1

                if stock_result.product_name and product.name == "Sin nombre":
                    product.name = stock_result.product_name
                if stock_result.price:
                    product.price = stock_result.price
                if stock_result.image_url:
                    product.image_url = stock_result.image_url

                # Calcular cambios de stock
                delta_warehouse = stock_result.warehouse_stock - product.warehouse_stock
                delta_transit = stock_result.transit_stock - product.transit_stock
                total_delta = delta_warehouse + delta_transit
                is_stock_changed = total_delta != 0

                if is_stock_changed:
                    history = StockHistory(
                        product_id=product.id,
                        old_warehouse_stock=product.warehouse_stock,
                        new_warehouse_stock=stock_result.warehouse_stock,
                        old_transit_stock=product.transit_stock,
                        new_transit_stock=stock_result.transit_stock
                    )
                    db.add(history)

                # Guardar datos de stock
                product.warehouse_stock = stock_result.warehouse_stock
                product.transit_stock = stock_result.transit_stock
                product.stock_type = stock_result.stock_type
                product.stock_type_label = stock_result.stock_type_label
                product.warehouse_breakdown = [
                    w.to_dict() for w in stock_result.warehouses
                ] if stock_result.warehouses else None

                if stock_result.is_available:
                    es_nuevo_stock = product.status != ProductStatus.IN_STOCK
                    
                    product.last_in_stock = datetime.now(timezone.utc)
                    product.status = ProductStatus.IN_STOCK

                    # Notificar y hacer log solo al detectar CAMBIO DE STOCK
                    if is_stock_changed:
                        change_msg = ""
                        icon = "📈" if total_delta > 0 else "📉"
                        word = "Aumentó" if total_delta > 0 else "Disminuyó"
                        parts = []
                        if delta_warehouse != 0:
                            parts.append(f"{'+' if delta_warehouse>0 else ''}{delta_warehouse} en almacén")
                        if delta_transit != 0:
                            parts.append(f"{'+' if delta_transit>0 else ''}{delta_transit} en tránsito")
                        change_msg = (
                            f"{icon} <b>{word} en {abs(total_delta)} unidades</b> ({', '.join(parts)})\n\n"
                            f"<b>Cantidad total:</b> {stock_result.total_available}\n"
                            f"<b>Cantidad por almacenes:</b>\n{stock_result.warehouse_breakdown}"
                        )
                        
                        log_plain_msg = (
                            f"{icon} {word} en {abs(total_delta)} ("
                            f"{', '.join(parts)}). Total: {stock_result.total_available}U\n"
                            f"{stock_result.warehouse_breakdown}"
                        )
                        
                        # Escribir a la base de datos visual del frontend
                        await _log_action(
                            db, product.id, product.name,
                            "stock_changed", LogLevel.SUCCESS if total_delta > 0 else LogLevel.WARNING, log_plain_msg,
                        )

                        config = get_app_config()
                        if config.get("notifications_enabled", True):
                            await _notify(
                                subject=f"Cambio de Stock: {product.name}",
                                product_name=product.name,
                                product_url=product.url,
                                price=stock_result.price,
                                stock_change_msg=change_msg
                            )
                        else:
                            logger.info(f"🔕 Notificación de stock omitida (desactivado en configuración)")

                    # ── AUTO-RESERVA (Checkout Automático) ──
                    if product.auto_buy and browser_manager.is_running and stock_result.total_available >= product.min_stock_to_trigger:
                        try:
                            settings_db = await db.execute(select(AppSettings).limit(1))
                            sys_settings = settings_db.scalar_one_or_none()
                            email = sys_settings.dofimall_email if sys_settings else ""
                            password = sys_settings.dofimall_password if sys_settings else ""

                            logger.info(f"⚡ Iniciando auto-checkout para {product.name} (Meta: {'MÁX' if product.target_quantity == -1 else product.target_quantity} uds)")
                            
                            # Avisamos al frontend visualmente que estamos atacando
                            product.status = ProductStatus.PURCHASING
                            await db.commit()
                            
                            page = await browser_manager.get_page()
                            
                            actual_target_qty = product.target_quantity
                            if actual_target_qty == -1:
                                actual_target_qty = stock_result.total_available
                                logger.info(f"Opcion MAX seleccionada. Usando iterador de stock: {actual_target_qty}")

                            checkout_result = await add_to_cart_and_checkout(
                                page, product.url,
                                target_quantity=actual_target_qty,
                                email=email, password=password,
                                product_id=product.id
                            )
                            
                            if checkout_result.get("success"):
                                await _log_action(
                                    db, product.id, product.name,
                                    "auto_purchase", LogLevel.SUCCESS,
                                    checkout_result.get("message", "Auto-compra finalizada")
                                )
                                
                                # Notificación de Compra Exitosa
                                await send_telegram_notification(
                                    subject="AUTO-COMPRA LOGRADA ⚡",
                                    product_name=product.name,
                                    product_url=product.url,
                                    checkout_url=checkout_result.get("checkout_url"),
                                    is_purchase=True,
                                    quantity=actual_target_qty,
                                    warehouse=stock_result.warehouse_breakdown
                                )

                                # Cambiar estado a RESERVED para que deje de comprobarse en bucle
                                product.status = ProductStatus.RESERVED
                                logger.warning(f"🔴 Producto {product.id} reservado, deteniendo monitorización...")
                            else:
                                product.status = ProductStatus.IN_STOCK
                                await db.commit()
                                await _log_action(
                                    db, product.id, product.name,
                                    "auto_purchase_failed", LogLevel.ERROR,
                                    checkout_result.get("message", "Error en auto-checkout")
                                )
                            
                            await browser_manager.close_page(page)
                        except Exception as e:
                            logger.error(f"❌ Error en auto-checkout: {e}")
                            product.status = ProductStatus.IN_STOCK
                            await db.commit()
                            await _log_action(
                                db, product.id, product.name,
                                "auto_purchase_error", LogLevel.ERROR,
                                f"Excepción: {str(e)}"
                            )

                else:
                    # No disponible
                    if stock_result.error:
                        product.status = ProductStatus.ERROR
                        await _log_action(
                            db, product.id, product.name,
                            "check_error", LogLevel.WARNING,
                            stock_result.error,
                        )
                    else:
                        product.status = ProductStatus.MONITORING

                await db.commit()

            except Exception as e:
                logger.error(f"💥 Error procesando {product.url}: {e}")
                product.status = ProductStatus.ERROR
                await db.commit()
                await _log_action(
                    db, product.id, product.name,
                    "error", LogLevel.ERROR, str(e),
                )

    logger.info("🔄 ═══ Ciclo de comprobación completado ═══")


async def _log_action(db, product_id, product_name, action, level, message):
    """Registra una acción en los logs."""
    log = ActionLog(
        product_id=product_id,
        product_name=product_name,
        action=action,
        level=level,
        message=message,
    )
    db.add(log)
    await db.commit()


async def _notify(subject, product_name, product_url, checkout_url=None, price=None, stock_change_msg=None):
    """Envía notificaciones por todos los canales configurados."""
    try:
        await send_email_notification(
            subject=subject, product_name=product_name,
            product_url=product_url, checkout_url=checkout_url, price=price,
            stock_change_msg=stock_change_msg
        )
    except Exception as e:
        logger.error(f"Error enviando email: {e}")

    try:
        await send_telegram_notification(
            subject=subject, product_name=product_name,
            product_url=product_url, checkout_url=checkout_url, price=price,
            stock_change_msg=stock_change_msg
        )
    except Exception as e:
        logger.error(f"Error enviando Telegram: {e}")

    try:
        await send_whatsapp_notification(
            product_name=product_name, product_url=product_url,
            checkout_url=checkout_url, price=price,
            stock_change_msg=stock_change_msg
        )
    except Exception as e:
        logger.error(f"Error enviando WhatsApp: {e}")


# ══════════════════════════════════════════════════════════════
# App Lifecycle
# ══════════════════════════════════════════════════════════════

async def init_browser_background():
    """Inicializa el browser de Playwright en segundo plano para evitar bloqueos del loop"""
    logger.info("🌍 Iniciando gestor de navegador de sesión en segundo plano...")
    try:
        await browser_manager.start()
    except Exception as e:
        logger.error(f"❌ No se pudo iniciar el navegador de Playwright: {e}")
        logger.warning("El auto-checkout no funcionará, compruébalo ejecutando login_manager.py primero")


async def run_keep_alive():
    """ Tarea en segundo plano para mantener la sesión viva navegando al carrito cada 5 min """
    try:
        async for db in get_db():
            settings_db = await db.execute(select(AppSettings).limit(1))
            sys_settings = settings_db.scalar_one_or_none()
            if sys_settings and sys_settings.keep_alive_enabled:
                if browser_manager.is_running:
                    logger.info("🛡️ Keep-Alive: Recargando sesión silenciosamente (visitando /cart)")
                    try:
                        page = await browser_manager.get_page()
                        await page.goto("https://www.dofimall.com/cart", wait_until="domcontentloaded", timeout=20000)
                        await page.wait_for_timeout(2000)
                        
                        from app.scraper.purchase import execute_login_bypass
                        logger.info("🛡️ Verificando integridad de sesión en el carrito...")
                        login_result = await execute_login_bypass(page, sys_settings.dofimall_email, sys_settings.dofimall_password)
                        
                        if login_result.get("success") and "Ya estaba logueado" not in login_result.get("message", ""):
                            logger.info("🛡️ Detectó sesión cerrada, pero el bypass logró auto-loguearse de forma exitosa.")
                        elif not login_result.get("success"):
                            logger.error(f"🛡️ Detectó sesión cerrada y el Bypass falló: {login_result.get('message')}")
                            
                        await browser_manager.close_page(page)
                        logger.info("🛡️ Keep-Alive completado existosamente.")
                    except Exception as e:
                        logger.warning(f"🛡️ Error en Keep-Alive: {e}")
            break # solo iterar una vez el generador
    except Exception as e:
        logger.error(f"Error gestionando db en Keep-Alive: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Iniciando DofiMall Sniper...")
    await init_db()
    os.makedirs("logs", exist_ok=True)
    
    # Iniciar Browser Manager Persistente en una tarea de fondo
    asyncio.create_task(init_browser_background())

    logger.info(f"⏰ Scheduler iniciado — comprobando cada {settings.check_interval_seconds} seg")
    
    scheduler.add_job(
        check_all_products,
        "interval",
        seconds=settings.check_interval_seconds,
        id="stock_checker",
        name="Stock Checker",
        replace_existing=True,
        max_instances=1,
    )
    
    scheduler.add_job(
        run_keep_alive,
        "interval",
        minutes=5,
        id="keep_alive_session",
        name="Keep Alive Session",
        replace_existing=True,
        max_instances=1,
    )
    
    scheduler.start()
    logger.info(
        f"⏰ Scheduler activado (Keep-alive programado cada 5 min)"
    )

    yield

    logger.info("🛑 Apagando DofiMall Sniper...")
    scheduler.shutdown(wait=False)
    await browser_manager.stop()


# ══════════════════════════════════════════════════════════════
# FastAPI App
# ══════════════════════════════════════════════════════════════

app = FastAPI(
    title="DofiMall Sniper",
    description="Sistema de monitorización y auto-reserva de productos en DofiMall",
    version="1.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products_router, prefix="/api")
app.include_router(logs_router, prefix="/api")
app.include_router(settings_router, prefix="/api")


@app.get("/api/dashboard", response_model=DashboardStats)
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    """Estadísticas del dashboard."""
    products = await db.execute(select(Product))
    all_products = products.scalars().all()

    total_checks = sum(p.check_count for p in all_products)
    last_check = max(
        (p.last_checked for p in all_products if p.last_checked), default=None
    )

    # Calcular próximo check del scheduler
    next_check = None
    job = scheduler.get_job("stock_checker")
    if job and job.next_run_time:
        next_check = job.next_run_time.isoformat()

    return DashboardStats(
        total_products=len(all_products),
        monitoring=sum(1 for p in all_products if p.status == ProductStatus.MONITORING),
        reserved=sum(1 for p in all_products if p.status == ProductStatus.RESERVED),
        in_stock=sum(1 for p in all_products if p.status == ProductStatus.IN_STOCK),
        errors=sum(1 for p in all_products if p.status == ProductStatus.ERROR),
        total_checks=total_checks,
        last_check=last_check,
        next_check=next_check,
        scheduler_running=scheduler.running,
        check_interval=settings.check_interval_minutes,
    )


@app.post("/api/check-now")
async def trigger_check_now():
    """Fuerza una comprobación inmediata."""
    scheduler.add_job(
        check_all_products,
        id="manual_check",
        name="Manual Check",
        replace_existing=True,
        max_instances=1,
    )
    return {"detail": "Comprobación manual iniciada"}


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "scheduler_running": scheduler.running,
    }


class ConfigModel(BaseModel):
    notifications_enabled: bool


@app.get("/api/config")
async def get_config():
    return get_app_config()


@app.post("/api/config")
async def update_config(config: ConfigModel):
    new_config = {"notifications_enabled": config.notifications_enabled}
    save_app_config(new_config)
    return new_config


@app.post("/api/notifications/test")
async def test_notification():
    await _notify(
        subject="Notificación de Prueba 🤖",
        product_name="Producto de Prueba (Ignorar)",
        product_url="https://www.dofimall.com",
        price="$0.00"
    )
    return {"detail": "Notificación de prueba enviada"}
