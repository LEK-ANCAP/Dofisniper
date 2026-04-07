from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('https://www.dofimall.com/goods/detail?productId=200003000207&warehouseId&st=-1', wait_until='networkidle')
    page.wait_for_timeout(3000)
    
    btns = page.locator(".buy_btn, .add_cart, .cart-submit, .btn_wrap div, .btn_wrap button, .goods-buy-btn, [class*='buy']").all()
    for b in btns:
        try:
            print(f"[{b.inner_text()}] Classes: {b.get_attribute('class')}")
        except:
            pass
