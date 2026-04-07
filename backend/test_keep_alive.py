import asyncio
from playwright.async_api import async_playwright
import os

async def main():
    user_data_dir = os.path.join(os.getcwd(), "browser_data")
    async with async_playwright() as p:
        b = await p.chromium.launch_persistent_context(user_data_dir, headless=True)
        page = await b.new_page()
        print("Navegando a cart...")
        await page.goto('https://www.dofimall.com/cart', wait_until='domcontentloaded')
        await page.wait_for_timeout(3000)
        
        login_btn = page.locator("span:has-text('Iniciar sesión'):visible, .nav-top__login:visible").first
        if await login_btn.count() > 0:
            print("Clicking login btn...")
            await login_btn.click()
            await page.wait_for_timeout(3000)
        
        url = page.url
        print(f"URL after click: {url}")
        
        pw_box = page.locator("form input[type='password']:visible").first
        print(f"Password box visible after click: {await pw_box.count()}")
        
        await b.close()

asyncio.run(main())
