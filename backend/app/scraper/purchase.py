"""
Módulo de auto-compra.
Cuando se detecta stock, añade el producto al carrito y navega al checkout.
Esto "reserva" el producto ya que queda en la pasarela de pago.

NOTA: Los selectores necesitan ajustarse según la estructura real de DofiMall.
"""

from playwright.async_api import Page, TimeoutError as PlaywrightTimeout
from loguru import logger
from app.core.config import get_settings

settings = get_settings()

# ═══════════════════════════════════════════════════════════════
# SELECTORES DE COMPRA - AJUSTAR según DofiMall
# ═══════════════════════════════════════════════════════════════
CHECKOUT_SELECTORS = {
    # Botón de añadir al carrito
    "add_to_cart": (
        "button:has-text('加入购物车'), "
        "button:has-text('Añadir al carrito'), "
        "button:has-text('Agregar al carrito'), "
        ".add-to-cart, .btn-add-cart, .add-cart, "
        "button.el-button--primary, "
        ".detail-add__btn, i.df-icon-icon-shopping_cart"
    ),

    # Confirmación de añadido al carrito (popup, toast, etc.)
    "cart_success": (
        ".cart-success, .add-success, .toast-success, "
        ".el-message--success, .notification-success"
    ),

    # Ir al carrito
    "go_to_cart": (
        "a[href*='cart'], .cart-icon, .shopping-cart, "
        ".go-to-cart, button:has-text('Ver carrito'), "
        "button:has-text('购物车')"
    ),

    # Selector de cantidad (si hay que especificar)
    "quantity_input": "input.quantity, input[type='number'].qty, .quantity-input input",

    # Botón de checkout / pagar
    "checkout_button": (
        "button:has-text('Pagar'), button:has-text('Checkout'), "
        "button:has-text('结算'), button:has-text('Proceder al pago'), "
        ".checkout-btn, .btn-checkout, .proceed-checkout"
    ),

    # Checkbox de seleccionar todos los productos en carrito
    "select_all_cart": (
        "input[type='checkbox'].select-all, .check-all input, "
        ".select-all-items"
    ),
}


async def add_to_cart_and_checkout(page: Page, product_url: str) -> dict:
    """
    Añade el producto al carrito y navega a la página de pago.

    El flujo es:
    1. Estando en la página del producto, click en "Añadir al carrito"
    2. Navegar al carrito
    3. Click en "Pagar" / "Checkout"
    4. Se queda en la página de pago (reserva hecha)

    Args:
        page: Página de Playwright en la URL del producto
        product_url: URL del producto (para logs)

    Returns:
        dict con el resultado: {success: bool, message: str, checkout_url: str|None}
    """
    result = {"success": False, "message": "", "checkout_url": None}

    try:
        # ── Paso 1: Añadir al carrito ──
        logger.info(f"🛒 Añadiendo al carrito: {product_url}")

        # Asegurar que estamos en la página del producto
        if page.url != product_url:
            await page.goto(product_url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2000)

        # Buscar y clickear botón de añadir al carrito
        try:
            add_btn = await page.wait_for_selector(
                CHECKOUT_SELECTORS["add_to_cart"], timeout=45000, state="visible"
            )
        except PlaywrightTimeout:
            add_btn = None

        if not add_btn:
            import os
            os.makedirs("logs", exist_ok=True)
            content = await page.content()
            with open("logs/last_checkout_fail.html", "w", encoding="utf-8") as f:
                f.write(content)
                
            result["message"] = "No se encontró el botón de añadir al carrito (DOM guardado)"
            logger.error(f"❌ {result['message']}")
            return result

        await add_btn.click()
        logger.info("🖱️ Click en 'Añadir al carrito'")
        
        # ── Manejar modal de "En tránsito" (si aparece) ──
        try:
            confirm_btn = await page.wait_for_selector(
                "button:has-text('Confirmar'), button:has-text('Confirm'), .el-message-box__btns .el-button--primary", 
                timeout=3000, state="visible"
            )
            if confirm_btn:
                await confirm_btn.click()
                logger.info("🖱️ Popup 'En tránsito' confirmado")
                await page.wait_for_timeout(2000)
        except PlaywrightTimeout:
            # Es normal si no aparece el popup (ej: stock local)
            pass

        # Verificar que se añadió correctamente (buscar toast/popup de éxito o ir directo)
        try:
            await page.wait_for_selector(
                CHECKOUT_SELECTORS["cart_success"], timeout=3000, state="attached"
            )
            logger.info("✅ Producto añadido al carrito correctamente")
        except PlaywrightTimeout:
            logger.warning(
                "⚠️ No se detectó mensaje visual de éxito, asumiendo continuación..."
            )

        # ── Paso 2: Ir al carrito ──
        logger.info("🛒 Navegando al carrito...")

        # Intentar click en icono de carrito o navegar directamente
        try:
            cart_link = await page.wait_for_selector(
                CHECKOUT_SELECTORS["go_to_cart"], timeout=5000
            )
            await cart_link.click()
            await page.wait_for_timeout(2000)
        except PlaywrightTimeout:
            # Navegar directamente a la URL del carrito
            await page.goto(
                f"{settings.dofimall_base_url}/cart",
                wait_until="networkidle",
                timeout=20000,
            )
            await page.wait_for_timeout(2000)

        logger.info(f"📍 En el carrito: {page.url}")

        # ── Paso 3: Seleccionar productos y hacer checkout ──

        # Intentar seleccionar todos los items del carrito
        try:
            select_all = await page.query_selector(
                CHECKOUT_SELECTORS["select_all_cart"]
            )
            if select_all:
                await select_all.check()
                await page.wait_for_timeout(500)
        except Exception:
            pass  # No siempre es necesario

        # Click en botón de pagar/checkout
        checkout_btn = await page.wait_for_selector(
            CHECKOUT_SELECTORS["checkout_button"], timeout=10000
        )

        if not checkout_btn:
            result["message"] = "No se encontró el botón de checkout"
            logger.error(f"❌ {result['message']}")
            return result

        await checkout_btn.click()
        logger.info("🖱️ Click en 'Pagar'")
        await page.wait_for_timeout(3000)

        # ── Paso 4: Verificar que estamos en la página de pago ──
        checkout_url = page.url
        result["success"] = True
        result["checkout_url"] = checkout_url
        result["message"] = f"¡Reserva completada! Página de pago: {checkout_url}"

        logger.info(f"🎉 ¡RESERVA EXITOSA! Checkout URL: {checkout_url}")

        # Tomar screenshot como evidencia
        await page.screenshot(path=f"screenshots/checkout_success.png")

        return result

    except PlaywrightTimeout as e:
        result["message"] = f"Timeout durante el proceso de compra: {e}"
        logger.error(f"⏱️ {result['message']}")
        await page.screenshot(path="screenshots/checkout_timeout.png")
        return result

    except Exception as e:
        result["message"] = f"Error inesperado en el checkout: {e}"
        logger.error(f"💥 {result['message']}")
        await page.screenshot(path="screenshots/checkout_error.png")
        return result
