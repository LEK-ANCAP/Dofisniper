import asyncio
from playwright.async_api import async_playwright
import time
import json

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Intercept network requests
        async def handle_response(response):
            if response.request.resource_type in ['xhr', 'fetch'] and response.request.method != "OPTIONS":
                print(f"[XHR] {response.url}")
                try:
                    data = await response.json()
                    default_prod = data.get("data", {}).get("defaultProduct", {})
                    if default_prod:
                        print(f"  productStock: {default_prod.get('productStock')}")
                        print(f"  transitStock: {default_prod.get('transitStock')}")
                except:
                    pass

        page.on("response", handle_response)
        
        print("Navigating...")
        await page.goto("https://www.dofimall.com/goods/detail?productId=200003581048&warehouseId&st=-1", wait_until="networkidle")
        await asyncio.sleep(3)
        
        print("\nSwitching warehouse...")
        await page.locator('.ant-select-selector').click()
        await asyncio.sleep(1)
        # Buscar el nombre CAMAGÜEY
        await page.locator('text=CA1 SUMAI CAMAGÜEY').click()
        await asyncio.sleep(5)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
