"""
Módulo de auto-compra.
Cuando se detecta stock, añade el producto al carrito y navega al checkout.
Esto "reserva" el producto ya que queda en la pasarela de pago.

NOTA: Los selectores necesitan ajustarse según la estructura real de DofiMall.
"""

from playwright.async_api import Page, TimeoutError as PlaywrightTimeout
from loguru import logger
from app.core.config import get_settings
from app.scraper.live_view import live_view_manager

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
        "div.detail-add__btn, "
        "button.el-button--primary"
    ),

    # Confirmación de añadido al carrito (popup, toast, etc.)
    "cart_success": (
        ".cart-success, .add-success, .toast-success, "
        ".el-message--success, .notification-success"
    ),

    # Ir al carrito (Icono superior derecho)
    "go_to_cart": (
        "div.nav-top__cart, a[href*='cart'], .cart-icon, .shopping-cart, "
        ".go-to-cart, button:has-text('Ver carrito'), "
        "i.df-icon-icon-shopping_cart"
    ),

    # Selector de cantidad (si hay que especificar)
    "quantity_input": "input.quantity, input[type='number'].qty, .quantity-input input, .el-input-number__increase",

    # Botón de checkout / pagar en el carrito
    "checkout_button": (
        "button:has-text('Pagar'), div:has-text('Pagar'), span:has-text('Pagar'), "
        ".el-button:has-text('Pagar'), .el-button--primary:has-text('Pagar'), "
        "button:has-text('Checkout'), a:has-text('Pagar'), a:has-text('Comprar'), "
        ".checkout-btn, .btn-checkout, .proceed-checkout, "
        ".cart-submit, .submit-btn, .cart-pay, .go-checkout"
    ),

    # Checkbox de seleccionar todos los productos en carrito
    "select_all_cart": (
        "input[type='checkbox'].select-all, .check-all input, "
        ".select-all-items, span.el-checkbox__inner"
    ),
}


async def add_to_cart_and_checkout(
    page: Page, 
    product_url: str, 
    target_quantity: int = 1,
    email: str = "",
    password: str = "",
    product_id: int = 0
) -> dict:
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
    steps_trace = []
    current_step = "Inicio"

    async def record_step(msg: str):
        nonlocal current_step
        current_step = msg
        logger.debug(f">> {msg}")
        # Solo guardamos el texto principal sin emojís para limpiar el trace visual
        clean_msg = msg.split(' 👉 ')[-1] if ' 👉 ' in msg else msg
        steps_trace.append(clean_msg)
        try:
            # Actualizar sensor cada vez que avanzamos un paso lógico, ignorando errores si la página navega
            msg_bytes = await page.screenshot(type="jpeg", quality=40)
            live_view_manager.update_frame(product_id, msg_bytes)
        except Exception as e:
            logger.warning(f"Sensor no pudo capturar frame en '{msg}' (posible navegación o cierre de pestaña).")

async def execute_login_bypass(page, email, password, record_step_func=None):
    """
    Rutina que detecta si el usuario fue sacado de su sesión y vuelve a inyectar credenciales + Captcha OCR.
    """
    async def log_step(msg):
        if record_step_func:
            await record_step_func(msg)
        else:
            logger.info(f"Login Bypass: {msg}")

    await log_step("Verificando estado de la sesión (Login Proactivo)")
    
    # Detectar el botón de perfil o si estamos en la URL de login SOLO SI ESTÁN VISIBLES
    is_anonymous = await page.locator("span:has-text('Iniciar sesión'):visible, .nav-top__login:visible, .side-nav__item-user__text:visible").count() > 0
    
    if is_anonymous or "login" in page.url or await page.locator("form input[type='password']:visible").count() > 0:
        await log_step("Sesión de visitante detectada. Desplegando Iniciar Sesión.")
        if not email or not password:
            return {"success": False, "message": "CRÍTICO: Sesión bloqueada y faltan credenciales maestras."}
        
        if await page.locator("form input[type='password']:visible").count() == 0:
            try:
                login_btn_top = page.locator(".nav-top__login:visible, span:has-text('Iniciar sesión'):visible").first
                if await login_btn_top.count() > 0:
                    await login_btn_top.click(timeout=5000)
                    await page.wait_for_load_state("networkidle", timeout=10000)
            except Exception as e:
                logger.warning(f"Error al pulsar boton login top: {e}")
        
        # Espera de protección corta en caso de carga parcial
        try:
            await page.wait_for_selector("form input[type='password']", timeout=5000, state="visible")
        except:
            pass

        if await page.locator("form input[type='password']:visible").count() > 0:
            await log_step("Inyectando credenciales magnas")
            try:
                email_input = page.locator("form input[type='text'], input[autocomplete='email'], input[type='text']").first
                pwd_input = page.locator("form input[type='password']").first
                await email_input.fill(email)
                await pwd_input.fill(password)
            except Exception as e:
                import os
                os.makedirs("logs", exist_ok=True)
                with open("logs/last_checkout_fail.html", "w", encoding="utf-8") as f:
                    f.write(await page.content())
                return {"success": False, "message": f"CRÍTICO: Error en los inputs de Contraseña. {str(e)}"}
        
        # Captcha Bypass
        await log_step("Buscando Captchas en el formulario")
        captcha_img = page.locator("form img, .login-code img, img.captcha").first
        if await captcha_img.count() > 0:
            await log_step("OCR Captcha Bypass iniciado offline")
            import ddddocr
            import tempfile
            
            logger.info("🔍 Capturando captcha...")
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                captcha_path = f.name
            await captcha_img.screenshot(path=captcha_path)
            
            ocr = ddddocr.DdddOcr(show_ad=False)
            with open(captcha_path, 'rb') as f:
                img_bytes = f.read()
            captcha_text = ocr.classification(img_bytes)
            logger.info(f"🤖 IA DdddOcr detectó: {captcha_text}")
            
            captcha_input = page.locator("input[placeholder*='verificación'], input[placeholder*='código'], input[placeholder*='code']").first
            if await captcha_input.count() > 0:
                await captcha_input.fill(captcha_text)
                
        # Click Iniciar Sesión (Simulando Tecla ENTER)
        await log_step("Ejecutando click en Login (Simulación de ENTER)")
        try:
            if await captcha_img.count() > 0:
                await captcha_input.press("Enter")
            else:
                await pwd_input.press("Enter")
            await page.wait_for_timeout(4000)
        except Exception as e:
            return {"success": False, "message": f"CRÍTICO: Error Enter Login {str(e)}"}
        
        if await page.locator("form input[type='password']").count() > 0:
            logger.warning("Fallo en login (posible captcha erróneo o credencial).")
            return {"success": False, "message": "OCR Falló o Login incorrecto."}
        else:
            logger.info("🔓 Login superado con éxito!")
            return {"success": True, "message": "Login exitoso"}
            
    return {"success": True, "message": "Ya estaba logueado"}


async def add_to_cart_and_checkout(
    page: Page,
    product_url: str,
    target_quantity: int,
    email: str = None,
    password: str = None,
    product_id: int = None
):
    result = {"success": False, "message": "", "checkout_url": None}
    
    # Start operation tracking
    tracker = live_view_manager.start_operation(product_id) if product_id else None

    async def record_step(msg):
        logger.info(f"👉 Paso: {msg}")
        if tracker:
            tracker.update_detail(msg)
        try:
            msg_bytes = await page.screenshot(type="jpeg", quality=40)
            live_view_manager.update_frame(product_id, msg_bytes)
        except Exception:
            pass

    async def retry_selector(selector, timeout_initial=15000, min_timeout=3000, max_retries=3, state="visible"):
        """Intenta encontrar un selector reduciéndole el timeout en cada reintento."""
        timeout = timeout_initial
        for attempt in range(max_retries + 1):
            try:
                el = await page.wait_for_selector(selector, timeout=timeout, state=state)
                return el
            except PlaywrightTimeout:
                if attempt < max_retries:
                    timeout = max(min_timeout, timeout // 2)
                    if tracker:
                        tracker.mark_retry(f"Selector no encontrado, reintentando con timeout={timeout}ms")
                    await record_step(f"Reintento {attempt+1}/{max_retries} (timeout: {timeout}ms)")
                else:
                    return None

    try:
        # ══════════════════════════════════════════════════════════
        # PASO 1: ENRUTAMIENTO DE ALMACÉN
        # ══════════════════════════════════════════════════════════
        if tracker:
            tracker.advance_to("routing", "Calculando almacén prioritario...")
        
        from app.scraper.monitor import check_stock
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
        
        await record_step("Consultando stock y almacenes disponibles...")
        stock_info = await check_stock(page, product_url)
        
        best_wh = None
        if stock_info and stock_info.warehouses:
            physicals = [w for w in stock_info.warehouses if w.warehouse_stock > 0]
            transits = [w for w in stock_info.warehouses if w.transit_stock > 0]
            
            if physicals:
                physicals.sort(key=lambda w: 0 if "camag" in w.name.lower() else 1)
                best_wh = physicals[0]
            elif transits:
                transits.sort(key=lambda w: 0 if "camag" in w.name.lower() else 1)
                best_wh = transits[0]
                
        if best_wh:
            parsed = urlparse(product_url)
            qs = parse_qs(parsed.query)
            qs["warehouseId"] = [str(best_wh.address_id)]
            new_query = urlencode(qs, doseq=True)
            product_url = urlunparse(parsed._replace(query=new_query))
            await record_step(f"Enrutado a: {best_wh.name} (ID: {best_wh.address_id})")
            logger.info(f"📍 URL de compra enrutada al almacén prioritario: {best_wh.name} ({best_wh.address_id})")
        else:
            await record_step("Sin almacén preferente — usando ruta por defecto")
        
        if tracker:
            tracker.mark_step_done("routing")

        # ══════════════════════════════════════════════════════════
        # PASO 2: NAVEGACIÓN + LOGIN BYPASS
        # ══════════════════════════════════════════════════════════
        if tracker:
            tracker.advance_to("navigate", "Navegando a la URL del producto...")
        
        await record_step("Cargando página del producto...")
        if page.url != product_url:
            await page.goto(product_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)
            
        # Login bypass
        await record_step("Verificando sesión activa...")
        login_result = await execute_login_bypass(page, email, password, record_step)
        if not login_result.get("success") and "Ya estaba logueado" not in login_result.get("message", ""):
            if tracker:
                tracker.mark_step_error(f"Login falló: {login_result.get('message', '')}")
                tracker.finish(False, login_result.get("message", "Login falló"))
            return login_result
            
        if page.url != product_url:
            await record_step("Renavegando al producto tras login...")
            await page.goto(product_url, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
        
        await record_step("Página del producto cargada correctamente")
        if tracker:
            tracker.mark_step_done("navigate")

        # ══════════════════════════════════════════════════════════
        # PASO 3: AÑADIR AL CARRITO
        # ══════════════════════════════════════════════════════════
        if tracker:
            tracker.advance_to("add_cart", "Buscando botón 'Añadir al carrito'...")

        add_btn = await retry_selector(CHECKOUT_SELECTORS["add_to_cart"], timeout_initial=45000, min_timeout=5000, max_retries=3)

        if not add_btn:
            import os
            os.makedirs("logs", exist_ok=True)
            content = await page.content()
            with open("logs/last_checkout_fail.html", "w", encoding="utf-8") as f:
                f.write(content)
            msg = "No se encontró el botón de añadir al carrito (DOM guardado)"
            if tracker:
                tracker.mark_step_error(msg)
                tracker.finish(False, msg)
            result["message"] = msg
            return result

        await record_step("Click en 'Añadir al carrito'...")
        await add_btn.click()
        logger.info("🖱️ Click en 'Añadir al carrito'")
        
        # Modal de "En tránsito"
        try:
            await record_step("Esperando posible confirmación de tránsito...")
            confirm_btn = await page.wait_for_selector(
                "button:has-text('Confirmar'), button:has-text('Confirm'), .el-message-box__btns .el-button--primary", 
                timeout=3000, state="visible"
            )
            if confirm_btn:
                await confirm_btn.click()
                await record_step("Popup de tránsito confirmado")
                await page.wait_for_timeout(2000)
        except PlaywrightTimeout:
            pass

        # Verificar éxito
        try:
            await page.wait_for_selector(CHECKOUT_SELECTORS["cart_success"], timeout=3000, state="attached")
            await record_step("Producto añadido al carrito ✓")
        except PlaywrightTimeout:
            await record_step("Sin mensaje de éxito visual — continuando")
        
        if tracker:
            tracker.mark_step_done("add_cart")

        # ══════════════════════════════════════════════════════════
        # PASO 4: CHECKOUT (Carrito → Pagar)
        # ══════════════════════════════════════════════════════════
        if tracker:
            tracker.advance_to("checkout", "Navegando al carrito...")

        # Ir al carrito
        try:
            await record_step("Buscando icono del carrito...")
            cart_link = await page.wait_for_selector(CHECKOUT_SELECTORS["go_to_cart"], timeout=5000)
            await cart_link.click()
            await page.wait_for_timeout(2000)
        except PlaywrightTimeout:
            await record_step("Forzando navegación directa a /cart")
            try:
                await page.goto(f"{settings.dofimall_base_url}/cart", wait_until="domcontentloaded", timeout=20000)
            except PlaywrightTimeout:
                await record_step("Timeout en carga del carrito — forzando continuación")
            await page.wait_for_timeout(2000)
            
        await record_step(f"En carrito: {page.url}")

        # Verificar selección — usar texto del footer como fuente de verdad
        await record_step("Verificando items seleccionados...")
        await page.wait_for_timeout(1500)  # Esperar renderizado del carrito
        
        async def ensure_products_selected():
            """Verifica y fuerza la selección de productos en el carrito. Retorna True si hay productos seleccionados."""
            try:
                # Leer el texto del footer del carrito para saber cuantos están seleccionados
                footer_text = await page.evaluate("""() => {
                    const el = document.querySelector('.cart-footer, .cart-bottom, .fixed-bottom, .cart-total');
                    return el ? el.innerText : document.body.innerText.substring(document.body.innerText.indexOf('seleccionado') - 30, document.body.innerText.indexOf('seleccionado') + 50);
                }""")
                
                # Detectar "Ha seleccionado 0 productos" o similar
                import re
                match = re.search(r'seleccionado\s+(\d+)\s+producto', footer_text, re.IGNORECASE)
                selected_count = int(match.group(1)) if match else -1
                
                if selected_count == 0:
                    await record_step(f"0 productos seleccionados — clickeando 'Seleccionar todo'...")
                    # Click en el primer checkbox visible (suele ser "Seleccionar todo")
                    select_all = page.locator(".cart-checkbox, .el-checkbox").first
                    try:
                        await select_all.click(force=True, timeout=2000)
                        await page.wait_for_timeout(800)
                        await record_step("Click en 'Seleccionar todo' ejecutado ✓")
                    except Exception:
                        # Fallback: click en todos los checkboxes individuales
                        cbs = await page.locator(".cart-checkbox, .el-checkbox").all()
                        for cb in cbs:
                            try:
                                await cb.click(force=True, timeout=500)
                                await page.wait_for_timeout(300)
                            except Exception:
                                pass
                        await record_step(f"Forzados {len(cbs)} checkboxes individuales")
                    return False  # Estaban en 0, tuvimos que forzar
                elif selected_count > 0:
                    await record_step(f"{selected_count} producto(s) seleccionado(s) ✓")
                    return True
                else:
                    # No pudimos leer el count, asumimos OK pero avisamos
                    await record_step("No se pudo leer conteo de selección — continuando")
                    return True
            except Exception as e:
                await record_step(f"Error verificando selección: {str(e)[:60]}")
                return True  # Continuar de todas formas
        
        await ensure_products_selected()

        # Ajustar cantidad (forzar mínimo 1)
        effective_qty = max(target_quantity, 1)
        if effective_qty > 1:
            try:
                await record_step(f"Ajustando cantidad a {effective_qty} uds...")
                cart_qty_input = page.locator("input[type='number']").first
                if await cart_qty_input.count() > 0:
                    await cart_qty_input.fill(str(effective_qty))
                    await cart_qty_input.press("Enter")
                    try:
                        await page.wait_for_load_state("networkidle", timeout=6000)
                    except PlaywrightTimeout:
                        pass
                    await record_step(f"Cantidad ajustada a {effective_qty} ✓")
            except Exception as e:
                await record_step(f"Aviso ajustando cantidad: {str(e)[:50]}")

        # Click en PAGAR
        await record_step("Buscando botón de PAGAR...")
        pagar_success = False
        import time
        for intento in range(1, 5):
            # PRE-CHECK: Si ya salimos del carrito, no reintentar
            if "cart" not in page.url:
                await record_step("Navegación fuera del carrito detectada antes del click ✓")
                pagar_success = True
                break
            
            # RE-SELECCIÓN: Tras primer fallo, volver a verificar checkboxes
            if intento > 1:
                await record_step("🔄 Re-verificando selección de productos antes de reintentar...")
                await ensure_products_selected()
                await page.wait_for_timeout(500)
                
            if tracker and intento > 1:
                tracker.mark_retry(f"Intento {intento} de click en Pagar")
            await record_step(f"Intento {intento}/4 de click en Pagar...")
            try:
                # Esperar a que loading masks desaparezcan
                loading_mask = page.locator(".el-loading-mask:visible").first
                if await loading_mask.count() > 0:
                    await loading_mask.wait_for(state="hidden", timeout=2000)

                # Buscar botones de checkout
                checkout_elements = await page.locator(".cart-footer__operate, .go_buy, .go_submit").locator("visible=true").all()
                
                for idx, btn in enumerate(checkout_elements):
                    if "cart" not in page.url:
                        break  # Ya navegó, salir del loop de botones
                    try:
                        # Estrategia 1: JS click (más rápido)
                        await btn.evaluate("el => el.click()")
                        await page.wait_for_timeout(500)
                        
                        # Check inmediato tras JS click
                        if "cart" not in page.url:
                            await record_step("Navegación detectada tras JS click ✓")
                            break
                        
                        # Estrategia 2: Mouse click en coordenadas
                        box = await btn.bounding_box()
                        if box and box["width"] < 400 and box["height"] < 200:
                            await page.mouse.click(box["x"] + box["width"]/2, box["y"] + box["height"]/2)
                            await page.wait_for_timeout(500)
                            
                            if "cart" not in page.url:
                                await record_step("Navegación detectada tras mouse click ✓")
                                break
                    except Exception:
                        pass
                
                # Verificación final de URL
                if "cart" not in page.url:
                    pagar_success = True
                    await record_step("Fuera del carrito ✓")
                    break
                else:
                    # Esperar un poco más por si la navegación es lenta
                    await page.wait_for_timeout(1500)
                    if "cart" not in page.url:
                        pagar_success = True
                        await record_step("Navegación tardía detectada ✓")
                        break
                    
            except Exception as e:
                await record_step(f"Error intento {intento}: {str(e)[:50]}")
                
        if not pagar_success:
            await record_step("⚠ Todos los intentos de Pagar fallaron — forzando continuación")
        
        await page.wait_for_timeout(1000)
        if tracker:
            tracker.mark_step_done("checkout")

        # ══════════════════════════════════════════════════════════
        # PASO 5: CONFIRMACIÓN FINAL
        # ══════════════════════════════════════════════════════════
        if tracker:
            tracker.advance_to("confirm", "Buscando 'Enviar pedido'...")

        # Click en "Enviar pedido"
        try:
            await record_step("Buscando botón 'Enviar pedido'...")
            enviar_btn = page.locator("button:has-text('Enviar pedido'), span:has-text('Enviar pedido'), .submit-btn, .goBuy").last
            await enviar_btn.wait_for(state="attached", timeout=10000)
            try:
                await enviar_btn.evaluate("element => element.click()")
                await record_step("Click en 'Enviar pedido' ejecutado")
            except Exception:
                await enviar_btn.click(force=True)
                await record_step("Force-click en 'Enviar pedido' ejecutado")
            await page.wait_for_timeout(3000)
        except PlaywrightTimeout:
            await record_step("⚠ No se detectó 'Enviar pedido'")

        # Click en "Estoy de acuerdo"
        try:
            await record_step("Buscando aviso legal 'Estoy de acuerdo'...")
            acuerdo_btn = page.locator("div.agreement-btn:not(.agreement-btn--colse)").last
            await acuerdo_btn.wait_for(state="visible", timeout=10000)
            
            await acuerdo_btn.evaluate("element => element.click()")
            await record_step("Aviso legal aceptado — esperando redirección bancaria...")
            
            try:
                async with page.expect_navigation(timeout=15000):
                    pass
            except Exception:
                await page.wait_for_timeout(5000)
                
        except PlaywrightTimeout:
            import os
            os.makedirs("logs", exist_ok=True)
            await page.screenshot(path="logs/checkout_final_fail.png", full_page=True)
            content = await page.content()
            with open("logs/checkout_final_fail.html", "w", encoding="utf-8") as f:
                f.write(content)
                
            msg = "CRÍTICO: No apareció el aviso legal ni hubo redirección tras Enviar pedido."
            if tracker:
                tracker.mark_step_error(msg)
                tracker.finish(False, msg)
            result["message"] = msg
            return result
        
        if tracker:
            tracker.mark_step_done("confirm")

        # ══════════════════════════════════════════════════════════
        # PASO 6: RESULTADO FINAL
        # ══════════════════════════════════════════════════════════
        checkout_url = page.url
        result["success"] = True
        result["checkout_url"] = checkout_url
        result["message"] = f"¡Reserva completada! Redirigido a pasarela de pago: {checkout_url}"

        logger.info(f"🎉 ¡RESERVA EXITOSA! Checkout URL: {checkout_url}")
        
        if tracker:
            tracker.finish(True, f"Reserva completada → {checkout_url}")

        try:
            await page.screenshot(path="screenshots/checkout_success.png")
        except Exception:
            pass

        return result

    except PlaywrightTimeout as e:
        msg = f"TIMEOUT en paso actual: {str(e)[:100]}"
        if tracker:
            tracker.mark_step_error(msg)
            tracker.finish(False, msg)
        result["message"] = msg
        try:
            await page.screenshot(path="screenshots/checkout_timeout.png")
        except Exception:
            pass
        return result

    except Exception as e:
        msg = f"CRASH: {str(e)[:150]}"
        if tracker:
            tracker.mark_step_error(msg)
            tracker.finish(False, msg)
        result["message"] = msg
        try:
            await page.screenshot(path="screenshots/checkout_error.png")
        except Exception:
            pass
        return result

