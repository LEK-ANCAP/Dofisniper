import asyncio
import sys
import json

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from playwright.async_api import async_playwright

async def get_dom():
    try:
        async with async_playwright() as p:
            ctx = await p.chromium.launch_persistent_context(
                user_data_dir=r'C:\\Users\\delav\\Downloads\\dofimall-sniper\\dofimall-sniper\\backend\\browser_data',
                headless=True
            )
            page = await ctx.new_page()
            print('Navegando al producto...')
            await page.goto('https://www.dofimall.com/goods/detail?productId=200003581048')
            await page.wait_for_timeout(5000)
            
            print('Tomando info de los botones...')
            buttons = await page.evaluate('''() => {
                const els = Array.from(document.querySelectorAll('button, .btn, [class*=\'cart\']'));
                return els.map(e => ({
                    tag: e.tagName, 
                    text: e.innerText?.trim().substring(0, 30), 
                    class: e.className
                })).filter(e => e.text && e.text.length > 3);
            }''')
            
            print(json.dumps(buttons, indent=2))
            
            await page.screenshot(path='cart_area.png')
            print('Screenshot guardado.')
            await ctx.close()
    except Exception as e:
        print("Error en get_dom:", e)

asyncio.run(get_dom())