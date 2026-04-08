from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.models import AppSettings
from app.schemas.schemas import AppSettingsSchema, AppSettingsUpdate
import os

router = APIRouter(prefix="/settings", tags=["settings"])

@router.get("", response_model=AppSettingsSchema)
async def get_settings(db: AsyncSession = Depends(get_db)):
    """Obtiene la configuración global de la app (credenciales)."""
    result = await db.execute(select(AppSettings).limit(1))
    settings = result.scalar_one_or_none()
    
    if not settings:
        settings = AppSettings(
            dofimall_email=os.getenv("DOFIMALL_EMAIL", "delavegadeus@gmail.com"),
            dofimall_password=os.getenv("DOFIMALL_PASSWORD", "Mvd295186*")
        )
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
        
    return settings

@router.patch("", response_model=AppSettingsSchema)
async def update_settings(settings_update: AppSettingsUpdate, db: AsyncSession = Depends(get_db)):
    """Actualiza las credenciales globales."""
    result = await db.execute(select(AppSettings).limit(1))
    settings = result.scalar_one_or_none()
    
    if not settings:
        settings = AppSettings()
        db.add(settings)
        
    if settings_update.dofimall_email is not None:
        settings.dofimall_email = settings_update.dofimall_email
    if settings_update.dofimall_password is not None:
        settings.dofimall_password = settings_update.dofimall_password
    if settings_update.keep_alive_enabled is not None:
        settings.keep_alive_enabled = settings_update.keep_alive_enabled
    if settings_update.scan_interval_seconds is not None:
        old_interval = settings.scan_interval_seconds
        settings.scan_interval_seconds = settings_update.scan_interval_seconds
        
        # Forzar reprogramación de TODOS los jobs de escaneo al nuevo intervalo
        if old_interval != settings_update.scan_interval_seconds:
            try:
                from app.main import scheduler
                new_interval = settings_update.scan_interval_seconds
                for job in scheduler.get_jobs():
                    if job.id.startswith("scan_product_"):
                        scheduler.reschedule_job(job.id, trigger='interval', seconds=new_interval)
            except Exception:
                pass  # scheduler might not be accessible in some contexts
        
    await db.commit()
    await db.refresh(settings)
    return settings

from app.scraper.browser import browser_manager

@router.post("/logout")
async def force_logout_browser():
    """Destruye la sesión de Playwright liberando las cookies actuales."""
    try:
        await browser_manager.close()
        import shutil
        import os
        # Delete browser context to wipe out cookies and saved states
        if os.path.exists(browser_manager.user_data_dir):
            shutil.rmtree(browser_manager.user_data_dir, ignore_errors=True)
            
        # Reiniciamos el browser limpio
        import asyncio
        asyncio.create_task(browser_manager.start())
        return {"success": True, "message": "Sesión del navegador destruida con éxito. Esperando nuevo login."}
    except Exception as e:
        return {"success": False, "message": f"Error al destruir sesión: {str(e)}"}

@router.get("/session-status")
async def check_session_status():
    """Analiza en tiempo real el DOM para validar si la sesión viva se mantiene."""
    try:
        if getattr(browser_manager, "_context", None) is None:
            return {"active": False, "message": "Navegador físico apagado"}
            
        page = await browser_manager.get_page()
        await page.goto("https://www.dofimall.com/cart", wait_until="domcontentloaded", timeout=15000)
        
        is_anonymous = await page.locator("span:has-text('Iniciar sesión'):visible, .nav-top__login:visible").count() > 0
        if "login" in page.url:
            is_anonymous = True
            
        browser_manager._is_logged_in = not is_anonymous
        await browser_manager.close_page(page)
        return {"active": browser_manager._is_logged_in, "message": "OK"}
    except Exception as e:
        return {"active": False, "message": f"Error: {str(e)}"}

@router.get("/session-status-fast")
async def check_session_status_fast():
    """Retorna la última bandera en caché de Playwright sin penalización de CPU."""
    if getattr(browser_manager, "_context", None) is None:
        return {"active": False, "message": "Navegador físico apagado"}
    return {"active": getattr(browser_manager, "_is_logged_in", False), "message": "Cached"}

@router.post("/force-login")
async def manual_force_login(db: AsyncSession = Depends(get_db)):
    """Inyecta el bot inmediatamente en la ruta de inicio de sesión."""
    result = await db.execute(select(AppSettings).limit(1))
    sys_settings = result.scalar_one_or_none()
    
    if not sys_settings or not sys_settings.dofimall_email:
         return {"success": False, "message": "Faltan credenciales configuradas en el panel."}
         
    try:
        page = await browser_manager.get_page()
        await page.goto("https://www.dofimall.com/cart", wait_until="domcontentloaded", timeout=20000)
        
        from app.scraper.purchase import execute_login_bypass
        res = await execute_login_bypass(page, sys_settings.dofimall_email, sys_settings.dofimall_password)
        
        if res.get("success"):
            browser_manager._is_logged_in = True
            
        await browser_manager.close_page(page)
        return res
    except Exception as e:
        return {"success": False, "message": f"Fallo al forzar inyección: {str(e)}"}
