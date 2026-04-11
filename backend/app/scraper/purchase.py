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
    product_id: int = None,
    pre_routed_wh_name: str = None,
    trigger_type: str = None
):
    result = {"success": False, "message": "", "checkout_url": None}
    
    # Start operation tracking
    tracker = live_view_manager.start_operation(product_id) if product_id else None

    async def record_step(msg):
        logger.info(f"👉 Paso: {msg}")
        if tracker:
            tracker.update_detail(msg)
        # ⚡ OPTIMIZACIÓN: Las capturas de pantalla están deshabilitadas para ahorrar ~100ms por paso
        # try:
        #     msg_bytes = await page.screenshot(type="jpeg", quality=40)
        #     live_view_manager.update_frame(product_id, msg_bytes)
        # except Exception:
        #     pass

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
            tracker.advance_to("routing", "Aplicando enrutamiento pre-calculado por Monitoreo...")
        
        # El enrutamiento fue pre-calculado por el proceso de monitoreo o llamada manual
        # para ahorrar ~3-5 segundos críticos de request adicional.
        if pre_routed_wh_name:
            await record_step(f"Ruta instantánea inyectada: {pre_routed_wh_name}")
            logger.info(f"📍 MODO TURBO: Usando URL pre-enrutada a {pre_routed_wh_name}")
        else:
            await record_step("Ruta instantánea inyectada (Manual / Default)")
        
        if tracker:
            tracker.mark_step_done("routing")

        # ══════════════════════════════════════════════════════════
        # PASO 2: NAVEGACIÓN RÁPIDA
        # ══════════════════════════════════════════════════════════
        if page.url != product_url:
            await page.goto(product_url, wait_until="domcontentloaded", timeout=30000)
            # OMITIDO: await page.wait_for_timeout(1000) para ir directo y sin pausas al intento de click
        

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

        # AJUSTE DE CANTIDAD PRE-CARRITO (Optimización)
        effective_qty = max(target_quantity, 1)
        if effective_qty > 1:
            try:
                await record_step(f"Inyectando {effective_qty} uds previas al carrito...")
                # Buscar input de producto (suele ser generic input[type='number'] o .el-input__inner)
                qty_input = page.locator("input.quantity, input[type='number'], .el-input-number__increase, .custom-quantity-input").first
                if await qty_input.count() > 0:
                    await qty_input.fill(str(effective_qty), force=True, timeout=2000)
                    await page.wait_for_timeout(200) # pequeña pausa para que react/vue lo registre
                    await record_step("Cantidad inyectada con éxito ✓")
                else:
                    await record_step("No se encontró input de cantidad pre-carrito, procesando default")
            except Exception as e:
                await record_step(f"Aviso cantidad pre-carrito: {str(e)[:40]}")

        await record_step("Click en 'Añadir al carrito'...")
        await add_btn.click()
        logger.info("🖱️ Click en 'Añadir al carrito'")
        
        # Modal de "En tránsito" (Omitir si es un ataque comprobado como puramente Local)
        if trigger_type != 'local':
            try:
                await record_step("Esperando posible confirmación de tránsito...")
                confirm_btn = await page.wait_for_selector(
                    "button:has-text('Confirmar'), button:has-text('Confirm'), .el-message-box__btns .el-button--primary", 
                    timeout=3000, state="visible"
                )
                if confirm_btn:
                    await confirm_btn.click()
                    await record_step("Popup de tránsito confirmado")
            except PlaywrightTimeout:
                pass
        else:
            await record_step("Ataque puramente local confirmado: ignorando modal de tránsito.")

        # Verificar éxito (OMITIDO POR OPTIMIZACIÓN - Reduce latencia en 3 segundos)
        await record_step("Validación visual de éxito (Toast) omitida por velocidad ✓")
        
        if tracker:
            tracker.mark_step_done("add_cart")

        # ══════════════════════════════════════════════════════════
        # PASO 4: CHECKOUT (Carrito → Pagar)
        # ══════════════════════════════════════════════════════════
        if tracker:
            tracker.advance_to("checkout", "Navegando al carrito...")

        # Ir al carrito directo por URL (Optimización para evitar delays de la UI)
        await record_step("Forzando salto rápido a /cart/index por URL...")
        try:
            await page.goto(f"{settings.dofimall_base_url}/cart/index", wait_until="domcontentloaded", timeout=15000)
        except PlaywrightTimeout:
            await record_step("Timeout en carga del carrito — continuando ciegamente...")
            
        await record_step(f"En carrito: {page.url}")

        # Verificar selección — usar texto del footer como fuente de verdad
        await record_step("Verificando items seleccionados...")
        await page.wait_for_timeout(100)  # Esperar renderizado rapido del carrito
        
        async def ensure_products_selected():
            """Verifica y fuerza la selección de productos en el carrito. Retorna True si hay productos seleccionados."""
            try:
                # Buscar cualquier indicador de conteo en el panel inferior (PC y mobile)
                footer_text = await page.evaluate("""() => {
                    const elCount = document.querySelector('.options_btn_left_check, .cart-footer__text, .cart-footer');
                    if (elCount) return elCount.innerText;
                    
                    const everything = document.body.innerText;
                    const match = everything.match(/Ha seleccionado.*productos?/i);
                    return match ? match[0] : "";
                }""")
                
                import re
                match = re.search(r'(?:seleccionado)\s*(\d+)', footer_text, re.IGNORECASE)
                selected_count = int(match.group(1)) if match else -1
                
                if selected_count == 0:
                    await record_step(f"0 productos seleccionados — forzando selección general ('Seleccionar todo')...")
                    
                    # Hacer click en 'Seleccionar todo'
                    await page.evaluate("""() => {
                        // Buscar explicitamente los contenedores de "Seleccionar todo"
                        const containers = document.querySelectorAll('.options_sel, .cart_title_pre, .cart-footer__all');
                        let clicked = false;
                        
                        for (let el of containers) {
                            if (el.innerText && el.innerText.toUpperCase().includes('SELECCIONAR TODO')) {
                                // Disparar click en el div
                                el.click();
                                // Disparar click en la imagen interna (a veces Vue atilde el evento solo a la imagen)
                                const img = el.querySelector('img');
                                if (img) img.click();
                                clicked = true;
                                break;
                            }
                        }
                        
                        if (!clicked) {
                            // Fallback de emergencia
                            const checkboxes = document.querySelectorAll('.store_sel, .cart-checkbox__icon');
                            if (checkboxes.length > 0) {
                                checkboxes[0].click();
                            }
                        }
                    }""")
                    await page.wait_for_timeout(200)
                    await record_step("Click en 'Seleccionar Todo' ejecutado ✓")
                    return False
                elif selected_count > 0:
                    await record_step(f"{selected_count} producto(s) seleccionado(s) ✓")
                    return True
                else:
                    await record_step("No se detectó un conteo claro de selección — asumiendo OK")
                    return True
            except Exception as e:
                await record_step(f"Aviso selección: {str(e)[:40]}")
                return True
        
        await ensure_products_selected()

        # [REMOVIDO: Ajuste de cantidad en el Carrito para optimizar tiempo. Se hace en el Paso 3 ahora]

        # Click en PAGAR
        await record_step("Disparando comando de PAGAR (Checkout)...")
        pagar_success = False
        
        try:
            # Intentar click estándar directo con Playwright primero (más confiable si los selectores cambiaron internamente)
            try:
                pagar_btn_locator = page.locator(".go_buy, .go_submit, .cart-footer__operate, button:has-text('Pagar')").last
                await pagar_btn_locator.wait_for(state="attached", timeout=2000)
                await pagar_btn_locator.click(force=True)
                clicked = True
            except Exception:
                # Fallback agresivo con JS puro
                clicked = await page.evaluate("""() => {
                    const loadingMask = document.querySelector('.el-loading-mask');
                    if (loadingMask) loadingMask.style.display = 'none';
                    
                    const buttons = document.querySelectorAll('.go_buy, .go_submit, .cart-footer__operate, .pay_btn');
                    for (let btn of buttons) {
                        if (btn.innerText && btn.innerText.toUpperCase().includes('PAGAR')) {
                            btn.click();
                            return true;
                        }
                    }
                    
                    // Fallback a cualquier boton de estas clases
                    if (buttons.length > 0) {
                        buttons[buttons.length - 1].click();
                        return true;
                    }
                    return false;
                }""")
            
            if clicked:
                await record_step("✔ Botón PAGAR ejecutado, esperando redirección...")
                
                # Esperar agresivamente a que la URL cambie, salir en cuanto deje de ser /cart
                for i in range(15):  # Esperar maximo 7.5 segundos
                    await page.wait_for_timeout(500)
                    if "buy/confirm" in page.url or "cart" not in page.url:
                        pagar_success = True
                        await record_step("✔ Tránsito hacia Confirmación validado.")
                        break
            else:
                await record_step("No se pudo disparar botón Pagar en DOM.")
        except Exception as e:
            await record_step(f"Error forzando Pagar: {str(e)[:50]}")
            
        if not pagar_success:
            await record_step("⚠ No se pudo validar la redirección de Pagar automáticamente — forzando continuación")
        
        await page.wait_for_timeout(100)
        if tracker:
            tracker.mark_step_done("checkout")

        # ══════════════════════════════════════════════════════════
        # PASO 5: CONFIRMACIÓN FINAL
        # ══════════════════════════════════════════════════════════
        if tracker:
            tracker.advance_to("confirm", "Buscando 'Enviar pedido'...")

        # 1. Marcar check de acuerdo (Evita el popup)
        try:
            await record_step("Marcando checkbox de Acuerdo de Compra...")
            # Buscando el checkbox específico según el DOM de DofiMall
            check_locator = page.locator("div.order-agreement__checkbox, span.el-checkbox__inner, label.el-checkbox").last
            if await check_locator.count() > 0:
                await check_locator.evaluate("element => { \n                    // Intentar clickar el div o el span interno \n                    const span = element.querySelector('.el-checkbox__inner'); \n                    if (span) { span.click(); } else { element.click(); } \n                }")
                await page.wait_for_timeout(100)
                await record_step("Checkbox validado ✓")
            else:
                await record_step("No se detectó el checkbox previo")
        except Exception as e:
            await record_step(f"Aviso marcando check: {str(e)[:40]}")

        # 2. Click en "Enviar pedido"
        try:
            await record_step("Buscando botón 'Enviar pedido'...")
            # Añadimos .submit_btn o selectores más genéricos por si Dofi cambió la clase
            enviar_btn = page.locator("button:has-text('Enviar pedido'), span:has-text('Enviar pedido'), .submit-btn, .submit_btn, .goBuy, div.submit-btn").last
            await enviar_btn.wait_for(state="attached", timeout=10000)
            
            # Forzar scroll hasta el fondo por si está oculto (Playwright a veces falla si el botón está fuera del viewport y es un div)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            
            try:
                # Playwright click nativo primero (conecta mejor con los listeners de Vue)
                await enviar_btn.click(force=True, timeout=2000)
                await record_step("Click en 'Enviar pedido' ejecutado (Nativo)")
            except Exception:
                # Fallback JS Evaluation
                await enviar_btn.evaluate("element => element.click()")
                await record_step("Click en 'Enviar pedido' ejecutado (JS)")

        except PlaywrightTimeout:
            await record_step("⚠ No se detectó 'Enviar pedido'")

        # 3. Fallback: Click en "Estoy de acuerdo" emergente SI el checkbox falló
        try:
            acuerdo_btn = page.locator("div.agreement-btn:not(.agreement-btn--colse)").last
            # Espera instantánea (100ms max) para no penalizar el tiempo. Si no está en el DOM, ignora.
            await acuerdo_btn.wait_for(state="visible", timeout=100)
            await acuerdo_btn.evaluate("element => element.click()")
            await record_step("Popup Aviso legal forzado aceptado.")
        except PlaywrightTimeout:
            pass # Todo en orden, el popup no apareció
            
        # 4. Esperar transición a la página de pago
        await record_step("Esperando redirección a pasarela de pago (/buy/pay)...")
        try:
            import re
            await page.wait_for_url(re.compile(r".*/buy/pay.*", re.IGNORECASE), timeout=8000)
            
            checkout_url = page.url
            if "buy/pay" not in checkout_url.lower():
                raise Exception("URL incorrecta")
                
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

        except Exception:
            msg = f"⚠ Falló la URL final. Se quedó atascado en: {page.url}"
            await record_step(msg)
            if tracker:
                tracker.mark_step_error(msg)
                tracker.finish(False, msg)
            result["message"] = msg
            result["success"] = False
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

