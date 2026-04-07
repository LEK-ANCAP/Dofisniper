import asyncio
from playwright.async_api import async_playwright

async def main():
    print("🚀 Levantando navegador para escanear el Carrito de DofiMall...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        await page.goto("https://www.dofimall.com/login")
        await page.goto("https://www.dofimall.com/login")
        print("\n⏳ ESPERANDO: Por favor, inicia sesión manualmente en la ventana que se acaba de abrir.")
        print("💡 USA TUS CREDENCIALES (El bot se quedó esperando al captcha de Dofimall).")
        print("⏳ Después de iniciar sesión, navega a tu carrito (Asegúrate de que haya al menos 1 producto).")
        print("⏳ El script detectará cuando estés en el carrito y extraerá la estructura del DOM automáticamente...")
        print("⏳ El script detectará cuando estés en el carrito y extraerá la estructura del DOM automáticamente...")
        
        # Esperar a que el usuario entre al carrito manualmente
        while "cart/index" not in page.url:
            await asyncio.sleep(2)
            
        print("\n✅ ¡Carrito detectado! Esperando 3 segundos a que Vue.js cargue los componentes...")
        await page.wait_for_timeout(3000)
        
        # Guardar DOM
        content = await page.content()
        with open("cart_dom_dump.html", "w", encoding="utf-8") as f:
            f.write(content)
            
        # Extraer checkboxes y botón explícitamente para análisis rápido
        print("\n🔍 Analizando botones y checkboxes visibles:")
        
        # Checkboxes
        check_elements = await page.locator(".el-checkbox, .checkbox, [type='checkbox'], div.active").all()
        for i, el in enumerate(check_elements):
            try:
                html = await el.evaluate("node => node.outerHTML")
                print(f"Checkbox o Elemento Activo {i}: {html[:150]}...")
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
