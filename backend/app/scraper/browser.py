"""
Playwright browser manager.
Mantiene una instancia persistente del browser para reutilizar la sesión.
"""

from playwright.async_api import async_playwright, BrowserContext, Page
import os
from loguru import logger
from app.core.config import get_settings

settings = get_settings()


class BrowserManager:
    """Gestiona una instancia de Playwright browser con sesión persistente."""

    def __init__(self):
        self._playwright = None
        self._context: BrowserContext | None = None
        self._is_logged_in = False
        self.user_data_dir = os.path.join(os.getcwd(), "browser_data")

    async def start(self):
        """Inicia el browser si no está corriendo."""
        if self._context:
            return

        logger.info(f"🌐 Iniciando Playwright browser en modo persistente... Directorio: {self.user_data_dir}")
        self._playwright = await async_playwright().start()
        
        # Crear directorio si no existe
        os.makedirs(self.user_data_dir, exist_ok=True)

        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=False,
            viewport={"width": 1366, "height": 768},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="es-ES",
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-blink-features=AutomationControlled"
            ]
        )
        self._is_logged_in = False
        logger.info("✅ Browser persistente iniciado correctamente")

    async def get_page(self) -> Page:
        """Retorna una nueva página en el contexto actual."""
        if not self._context:
            await self.start()
        return await self._context.new_page()

    async def close_page(self, page: Page):
        """Cierra una página específica."""
        try:
            if page and not page.is_closed():
                await page.close()
        except Exception as e:
            logger.warning(f"Error cerrando página: {e}")

    async def stop(self):
        """Cierra el browser completamente."""
        logger.info("🛑 Cerrando browser...")
        try:
            if self._context:
                await self._context.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception as e:
            logger.error(f"Error cerrando browser: {e}")
        finally:
            self._context = None
            self._playwright = None
            self._is_logged_in = False

    async def take_screenshot(self, page: Page, path: str):
        """Toma un screenshot para debug."""
        try:
            await page.screenshot(path=path, full_page=False)
            logger.debug(f"📸 Screenshot guardado: {path}")
        except Exception as e:
            logger.warning(f"No se pudo tomar screenshot: {e}")

    @property
    def is_logged_in(self) -> bool:
        return self._is_logged_in

    @is_logged_in.setter
    def is_logged_in(self, value: bool):
        self._is_logged_in = value

    @property
    def is_running(self) -> bool:
        return self._context is not None


# Singleton global
browser_manager = BrowserManager()
