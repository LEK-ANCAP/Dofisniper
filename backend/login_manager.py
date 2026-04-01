"""
Gestor de Login en DofiMall.
Ejecuta este script manualmente una vez para iniciar sesión en DofiMall y guardar
las cookies/tokens en el sistema local, superando así los Captchas.
"""

import asyncio
import os
from playwright.async_api import async_playwright

USER_DATA_DIR = os.path.join(os.path.dirname(__file__), "browser_data")
DOFIMALL_URL = "https://www.dofimall.com/login"

async def main():
    print(f"\n🚀 Iniciando gestor de sesión de DofiMall...")
    print(f"📁 Directorio de datos: {USER_DATA_DIR}")
    
    os.makedirs(USER_DATA_DIR, exist_ok=True)
    
    async with async_playwright() as p:
        print("\n🌐 Abriendo navegador (no lo cierres manualmente aún)...")
        # Abrimos en modo no headless para poder ver el captcha
        context = await p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,
            viewport={"width": 1366, "height": 768},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="es-ES",
            args=[
                "--disable-blink-features=AutomationControlled"
            ]
        )
        
        page = await context.new_page()
        await page.goto(DOFIMALL_URL)
        
        print("\n" + "="*60)
        print("🛑 ACCIÓN REQUERIDA 🛑")
        print("1. Inicia sesión en DofiMall en la ventana emergente.")
        print("2. Resuelve cualquier CAPTCHA que aparezca.")
        print("3. Cuando veas que ya estás dentro de tu cuenta, PRESIONA ENTER aquí en la consola.")
        print("="*60 + "\n")
        
        # Esperamos a que el usuario termine manualmente en su SO
        # Note: input() is synchronous, so we run it in an executor
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, input, "Presiona ENTER aquí cuando hayas terminado... ")
        
        print("\n💾 Guardando estado de la sesión...")
        await context.close()
        print("✅ Session guardada exitosamente. Ya puedes cerrar esta consola o volver a levantar el backend.")

if __name__ == "__main__":
    asyncio.run(main())
