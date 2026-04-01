"""
Módulo de autenticación en DofiMall.
Maneja el login y la verificación de sesión.

NOTA: Los selectores CSS/XPath necesitan ajustarse según el HTML real de DofiMall.
      Ejecuta el scraper en modo headless=false para inspeccionar la página
      y actualizar los selectores en las constantes de abajo.
"""

from playwright.async_api import Page, TimeoutError as PlaywrightTimeout
from loguru import logger
from app.core.config import get_settings
from app.scraper.browser import browser_manager

settings = get_settings()

# ═══════════════════════════════════════════════════════════════
# SELECTORES - AJUSTAR según la estructura real de DofiMall
# Ejecuta con HEADLESS=false para inspeccionar y actualizar
# ═══════════════════════════════════════════════════════════════
SELECTORS = {
    # Página de login
    "login_url": f"{settings.dofimall_base_url}/login",
    "email_input": 'input[type="text"], input[type="email"], input[name="email"]',
    "password_input": 'input[type="password"]',
    "login_button": 'button[type="submit"], .login-btn, .btn-login',

    # Indicadores de sesión activa
    "logged_in_indicator": '.user-info, .user-name, .avatar, .account-menu',
    "logout_button": '.logout, .sign-out, [href*="logout"]',
}


async def login(page: Page) -> bool:
    """
    Realiza login en DofiMall.

    Returns:
        True si el login fue exitoso, False en caso contrario.
    """
    if browser_manager.is_logged_in:
        # Verificar si la sesión sigue activa
        if await is_session_active(page):
            logger.debug("✅ Sesión activa, no es necesario hacer login")
            return True
        logger.info("⚠️ Sesión expirada, re-autenticando...")

    try:
        logger.info(f"🔐 Navegando a login: {SELECTORS['login_url']}")
        await page.goto(SELECTORS["login_url"], wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)  # Esperar a que la SPA cargue

        # Rellenar email
        email_input = await page.wait_for_selector(
            SELECTORS["email_input"], timeout=10000
        )
        await email_input.fill(settings.dofimall_email)
        logger.debug("📧 Email introducido")

        # Rellenar password
        password_input = await page.wait_for_selector(
            SELECTORS["password_input"], timeout=5000
        )
        await password_input.fill(settings.dofimall_password)
        logger.debug("🔑 Password introducido")

        # Click en login
        login_btn = await page.wait_for_selector(
            SELECTORS["login_button"], timeout=5000
        )
        await login_btn.click()
        logger.info("🖱️ Click en botón de login")

        # Esperar a que cargue el dashboard o indicador de login
        await page.wait_for_timeout(3000)

        # Verificar login exitoso
        try:
            await page.wait_for_selector(
                SELECTORS["logged_in_indicator"], timeout=10000
            )
            browser_manager.is_logged_in = True
            logger.info("✅ Login exitoso en DofiMall")
            return True
        except PlaywrightTimeout:
            # Puede que el indicador no aparezca pero el login sea exitoso
            # Verificar por URL o por ausencia de formulario de login
            current_url = page.url
            if "login" not in current_url.lower():
                browser_manager.is_logged_in = True
                logger.info("✅ Login exitoso (verificado por URL)")
                return True

            logger.error("❌ Login fallido - no se detectó sesión activa")
            await browser_manager.take_screenshot(
                page, "screenshots/login_failed.png"
            )
            return False

    except PlaywrightTimeout as e:
        logger.error(f"❌ Timeout durante login: {e}")
        await browser_manager.take_screenshot(page, "screenshots/login_timeout.png")
        return False
    except Exception as e:
        logger.error(f"❌ Error inesperado durante login: {e}")
        await browser_manager.take_screenshot(page, "screenshots/login_error.png")
        return False


async def is_session_active(page: Page) -> bool:
    """Verifica si la sesión actual sigue activa."""
    try:
        await page.goto(settings.dofimall_base_url, wait_until="networkidle", timeout=20000)
        await page.wait_for_timeout(2000)

        indicator = await page.query_selector(SELECTORS["logged_in_indicator"])
        return indicator is not None
    except Exception:
        return False
