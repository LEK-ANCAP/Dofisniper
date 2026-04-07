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
from app.scraper.browser import browser_manager
from app.scraper.purchase import add_to_cart_and_checkout
from app.api.auth import router as auth_router, get_current_user, get_password_hash
from app.models.models import Product, ActionLog, ProductStatus, LogLevel, StockHistory, AppSettings, User
from app.schemas.schemas import DashboardStats
from app.api.products import router as products_router
from app.api.logs import router as logs_router
from app.api.settings import router as settings_router
from app.api.analytics import router as analytics_router
from app.api.categories import router as categories_router
from app.scraper.monitor import check_stock
from pydantic import BaseModel
from app.notifications.email_notif import send_email_notification
from app.notifications.whatsapp import send_whatsapp_notification
from app.notifications.telegram import send_telegram_notification
from app.core.persistent_config import get_app_config, save_app_config
from app.api.market_intelligence import calculate_product_analytics
from app.models.models import ProductSnapshot

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

active_checkout_tasks = {}

async def persistent_checkout_loop(product_id: int):
    """
    Mantene un bucle continuo bloqueado al producto hasta que logre la compra o deje de haber stock.
    Esto debe invocarse como un Task asíncrono para que no bloquee nada más.
    """
    logger.info(f"⚡ [HILO CHECKOUT {product_id}] Inicializando ataque continuo...")
    while True:
        try:
            async with async_session() as db:
                product = await db.execute(select(Product).where(Product.id == product_id))
                product = product.scalar_one_or_none()
                if not product or not product.is_active or not product.auto_buy:
                    logger.warning(f"🛑 [HILO CHECKOUT {product_id}] Abortado: Inactivo o AutoBuy deshabilitado.")
                    break
                
                # Check for stock right before attacking
                stock_result = await check_stock(None, product.url)
                if not stock_result.is_available or stock_result.total_available < product.min_stock_to_trigger:
                    logger.warning(f"🚫 [HILO CHECKOUT {product_id}] Stock agotado ({stock_result.total_available}U). Abortando auto-compra y regresando a Monitoreo.")
                    product.status = ProductStatus.IN_STOCK if stock_result.is_available else ProductStatus.MONITORING
                    await db.commit()
                    break

                settings_db = await db.execute(select(AppSettings).limit(1))
                sys_settings = settings_db.scalar_one_or_none()
                email = sys_settings.dofimall_email if sys_settings else ""
                password = sys_settings.dofimall_password if sys_settings else ""

                actual_target_qty = product.target_quantity
                if actual_target_qty == -1:
                    actual_target_qty = stock_result.total_available

                if not browser_manager.is_running:
                    logger.error(f"❌ [HILO CHECKOUT {product_id}] ERROR FATAL: Browser Manager no está corriendo.")
                    await asyncio.sleep(5)
                    continue

                page = await browser_manager.get_page()
                logger.info(f"⚡ [HILO CHECKOUT {product_id}] Disparando Playwright (Pidiendo {actual_target_qty}U)...")

                checkout_result = await add_to_cart_and_checkout(
                    page, product.url,
                    target_quantity=actual_target_qty,
                    email=email, password=password,
                    product_id=product.id
                )
                
                await browser_manager.close_page(page)

                if checkout_result.get("success"):
                    await _log_action(db, product.id, product.name, "auto_purchase", LogLevel.SUCCESS, "Auto-compra confirmada.")
                    await send_telegram_notification(
                        subject="AUTO-COMPRA LOGRADA ⚡", product_name=product.name, product_url=product.url, 
                        checkout_url=checkout_result.get("checkout_url"), is_purchase=True, quantity=actual_target_qty
                    )
                    product.status = ProductStatus.RESERVED
                    product.auto_buy = False # Safety net
                    await db.commit()
                    logger.success(f"🎉 [HILO CHECKOUT {product_id}] Ojetivo Asegurado. Cerrando hilo.")
                    break
                else:
                    await _log_action(db, product.id, product.name, "auto_purchase_failed", LogLevel.ERROR, "Reintentando ataque...")
                    logger.warning(f"⚠️ [HILO CHECKOUT {product_id}] Falló intento. Reanudando loop casi inmediatamente...")
                    await asyncio.sleep(2) # Breve pausa para no spamear totalmente el thread
                    
        except Exception as e:
            logger.error(f"💥 [HILO CHECKOUT {product_id}] Excepción en loop agresivo: {e}")
            await asyncio.sleep(2)
            
    # Cleanup task registry
    if product_id in active_checkout_tasks:
        del active_checkout_tasks[product_id]


async def process_single_product(product_id: int):
    """Job asignado dinámicamente: Solo comprueba el stock de 1 producto"""
    async with async_session() as db:
        result = await db.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()

        if not product or not product.is_active:
            return

        # Skip scanning if it's already reserved or paused
        if product.status in [ProductStatus.RESERVED, ProductStatus.PAUSED]:
            return

        # If it's purchasing, do not scan it redundantly here, the checkout loop handles it
        if product.status == ProductStatus.PURCHASING:
            return

        try:
            stock_result = await check_stock(None, product.url)
            
            product.last_checked = datetime.now(timezone.utc)
            product.check_count += 1
            
            if stock_result.product_name and product.name == "Sin nombre":
                product.name = stock_result.product_name
            if stock_result.price:
                product.price = stock_result.price
            if stock_result.image_url:
                product.image_url = stock_result.image_url

            # Snapshot for intelligence
            snapshot = ProductSnapshot(
                product_id=product.id,
                stock_quantity=stock_result.warehouse_stock,
                transit_quantity=stock_result.transit_stock
            )
            db.add(snapshot)
            asyncio.create_task(calculate_product_analytics(product.id, db))
            
            # Stock changes
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
            
            product.warehouse_stock = stock_result.warehouse_stock
            product.transit_stock = stock_result.transit_stock
            product.stock_type = stock_result.stock_type
            product.stock_type_label = stock_result.stock_type_label
            if stock_result.warehouses:
                product.warehouse_breakdown = [w.to_dict() for w in stock_result.warehouses]
            
            if stock_result.is_available:
                product.last_in_stock = datetime.now(timezone.utc)
                product.status = ProductStatus.IN_STOCK
                
                if is_stock_changed:
                    icon = "📈" if total_delta > 0 else "📉"
                    word = "Aumentó" if total_delta > 0 else "Disminuyó"
                    parts = []
                    if delta_warehouse != 0: parts.append(f"{'+' if delta_warehouse>0 else ''}{delta_warehouse} almacén")
                    if delta_transit != 0: parts.append(f"{'+' if delta_transit>0 else ''}{delta_transit} tránsito")
                    
                    change_msg = f"{icon} <b>{word} en {abs(total_delta)} unidades</b> ({', '.join(parts)})\n\n<b>Total:</b> {stock_result.total_available}U"
                    log_plain_msg = f"{icon} {word} en {abs(total_delta)} ({', '.join(parts)}). Total: {stock_result.total_available}U"
                    
                    await _log_action(db, product.id, product.name, "stock_changed", LogLevel.SUCCESS if total_delta > 0 else LogLevel.WARNING, log_plain_msg)
                    
                    config = get_app_config()
                    if config.get("notifications_enabled", True):
                        await _notify(
                            subject=f"Cambio de Stock: {product.name}",
                            product_name=product.name, product_url=product.url, price=stock_result.price, stock_change_msg=change_msg
                        )

                # TRIGGER CHECKOUT CONCURRENTLY
                if product.auto_buy and browser_manager.is_running and stock_result.total_available >= product.min_stock_to_trigger:
                    if product.id not in active_checkout_tasks:
                        logger.warning(f"🚀 INICIANDO VUELO TÁCTICO AUTO-COMPRA PARA: {product.name}")
                        product.status = ProductStatus.PURCHASING
                        await db.commit()
                        active_checkout_tasks[product.id] = asyncio.create_task(persistent_checkout_loop(product.id))
            else:
                if stock_result.error:
                    product.status = ProductStatus.ERROR
                    await _log_action(db, product.id, product.name, "check_error", LogLevel.WARNING, stock_result.error)
                else:
                    product.status = ProductStatus.MONITORING

            await db.commit()
            
        except Exception as e:
            logger.error(f"💥 Error procesando Job_{product_id}: {e}")
            product.status = ProductStatus.ERROR
            await db.commit()
            await _log_action(db, product.id, product.name, "error", LogLevel.ERROR, str(e))


async def job_synchronizer():
    """
    Se ejecuta globalmente cada pocos segundos para levantar o destruir procesos por cada producto.
    """
    async with async_session() as db:
        settings_db = await db.execute(select(AppSettings).limit(1))
        sys_settings = settings_db.scalar_one_or_none()
        interval_secs = sys_settings.scan_interval_seconds if sys_settings and sys_settings.scan_interval_seconds else 10

        # Obtener todos los productos
        result = await db.execute(select(Product))
        products = result.scalars().all()

        current_jobs_ids = [job.id for job in scheduler.get_jobs()]
        active_db_ids = set()

        for p in products:
            job_id = f"scan_product_{p.id}"
            
            # Si el producto está activo, intentamos asegurarnos de que el job exista con el intervalo correcto
            if p.is_active and p.status not in [ProductStatus.PAUSED]:
                active_db_ids.add(job_id)
                job = scheduler.get_job(job_id)
                # Solo updatear o añadir si no existe
                if not job:
                    scheduler.add_job(
                        process_single_product,
                        "interval",
                        seconds=interval_secs,
                        args=[p.id],
                        id=job_id,
                        replace_existing=True
                    )
                else:
                    # En apscheduler podemos reprogramar si el intervalo cambió
                    if hasattr(job.trigger, 'interval') and job.trigger.interval.total_seconds() != interval_secs:
                        scheduler.reschedule_job(job_id, trigger='interval', seconds=interval_secs)
            else:
                # Si no está activo en DB pero existe el job, se borra
                if job_id in current_jobs_ids:
                    scheduler.remove_job(job_id)
                    
        # Borrar jobs residuales que ya ni existan en BD
        for job_id in current_jobs_ids:
            if job_id.startswith("scan_product_") and job_id not in active_db_ids:
                scheduler.remove_job(job_id)


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


async def seed_admin_user():
    """Crea el usuario administrador por defecto si no existe."""
    async with async_session() as db:
        email = "admin@odubasolar.com"
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        
        new_password = "OdubaSolar@97"
        
        if not user:
            logger.info(f"👤 Creando usuario administrador por defecto: {email}")
            admin_user = User(
                email=email,
                hashed_password=get_password_hash(new_password)
            )
            db.add(admin_user)
            await db.commit()
            logger.info("✅ Usuario administrador creado con éxito")
        else:
            logger.info(f"👤 Actualizando credenciales del administrador: {email}")
            user.hashed_password = get_password_hash(new_password)
            await db.commit()
            logger.info("✅ Contraseña de administrador sincronizada")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Iniciando DofiMall Sniper...")
    await init_db()
    await seed_admin_user()
    os.makedirs("logs", exist_ok=True)
    
    # Iniciar Browser Manager Persistente en una tarea de fondo
    asyncio.create_task(init_browser_background())

    logger.info(f"⏰ Scheduler iniciado — Orchestrator de Hilos corriendo cada 5s")
    
    scheduler.add_job(
        job_synchronizer,
        "interval",
        seconds=5,
        id="job_synchronizer",
        name="Job Synchronizer",
        replace_existing=True,
        max_instances=1,
    )
    
    scheduler.add_job(
        run_keep_alive,
        "interval",
        minutes=3,
        id="keep_alive_session",
        name="Keep Alive Session",
        replace_existing=True,
        max_instances=1,
    )
    
    scheduler.start()
    logger.info(
        f"⏰ Scheduler activado (Keep-alive programado cada 3 min)"
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

# Public Routes
app.include_router(auth_router, prefix="/api")

# Protected Routes
from app.api.products import public_router as public_products_router
app.include_router(public_products_router, prefix="/api") # Image proxy is here, no auth required

app.include_router(products_router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(logs_router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(settings_router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(analytics_router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(categories_router, prefix="/api", dependencies=[Depends(get_current_user)])

from app.api.market_intelligence import router as market_intelligence_router
app.include_router(market_intelligence_router, prefix="/api", dependencies=[Depends(get_current_user)])


@app.get("/api/dashboard", response_model=DashboardStats, dependencies=[Depends(get_current_user)])
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    """Estadísticas del dashboard."""
    products = await db.execute(select(Product))
    all_products = products.scalars().all()

    total_checks = sum(p.check_count for p in all_products)
    last_check = max(
        (p.last_checked for p in all_products if p.last_checked), default=None
    )

    return DashboardStats(
        total_products=len(all_products),
        monitoring=sum(1 for p in all_products if p.is_active and p.status in [
            ProductStatus.MONITORING, ProductStatus.IN_STOCK, ProductStatus.PURCHASING, ProductStatus.ERROR
        ]),
        reserved=sum(1 for p in all_products if p.status == ProductStatus.RESERVED),
        in_stock=sum(1 for p in all_products if p.status == ProductStatus.IN_STOCK),
        errors=sum(1 for p in all_products if p.is_active and p.status == ProductStatus.ERROR),
        total_checks=total_checks,
        scheduler_running=scheduler.running,
    )


# Endpoint /api/check-now eliminado (Ahora el sincronizador es continuo a 5s)


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
