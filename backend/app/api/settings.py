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
