import asyncio
from playwright.async_api import async_playwright

async def main():
    print("🚀 Levantando navegador para escanear el Carrito de DofiMall...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        await page.goto("https://www.dofimall.com/login")
        print("\n⏳ Haciendo login automático con credenciales maestras...")
        await page.locator("input[placeholder='Correo electrónico']").fill("delavegadeus@gmail.com")
        await page.locator("input[placeholder='contraseña']").fill("Mvd295186*")
        await page.locator("button.login-btn, button:has-text('Iniciar sesión')").click()
        
        print("\n⏳ ESPERANDO: Por favor avanza si cae un captcha, y añade un producto.")
        print("⏳ El script detectará cuando estés en el carrito y extraerá la estructura del DOM automáticamente...")
        
        # Esperar a que el usuario navegue
        print("\n" + "="*60)
        print("💡 INSTRUCCIONES:")
        print("1. Usa la ventana de Chromium abierta.")
        print("2. Inicia sesión SÓLO SI te lo pide.")
        print("3. Busca un producto cualquiera (ej. 'panel solar') y añádelo.")
        print("4. VE AL CARRITO y déjalo exactamente en la pantalla donde falla.")
        print("5. Cuando el carrito esté en pantalla con el producto, vuelve a esta terminal.")
        print("="*60 + "\n")
        
        await asyncio.get_event_loop().run_in_executor(None, input, "👉 PRESIONA ENTER AQUÍ CUANDO EL CARRITO ESTÉ LISTO EN EL NAVEGADOR PARA EXTRAER EL DOM...")
        
        print("\n✅ Extrayendo DOM actual... Espere.")
        await page.wait_for_timeout(1000)
        
        # Guardar DOM
        content = await page.content()
        with open("cart_dom_dump.html", "w", encoding="utf-8") as f:
            f.write(content)
            
        print("\n🔍 Analizando checkboxes visibles en Element UI:")
        
        # Buscar la estructura de el-checkbox
        check_elements = await page.locator("label.el-checkbox, span.el-checkbox__input, .checkbox, [type='checkbox']").all()
        print(f"Se encontraron {len(check_elements)} posibles checkboxes.")
        for i, el in enumerate(check_elements[:5]):  # Mostrar maximo 5
            try:
                html = await el.evaluate("node => node.outerHTML")
                print(f"\n[Checkbox {i}] :\n{html}")
            except: pass
            
        # Pagar
        pagar_btn = page.locator("button:has-text('Pagar'), .go_buy, .go_submit").first
        try:
            pagar_html = await pagar_btn.evaluate("node => node.outerHTML")
            print(f"\n🛒 Botón de Pagar DOM:\n{pagar_html}")
        except Exception as e:
            print(f"\n❌ No encontré el botón de pagar por los selectores habituales: {e}")
            
        print("\n💾 ¡Extracción completa! El DOM completo se guardó en 'cart_dom_dump.html'.")
        print("Puedes cerrar el navegador.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
