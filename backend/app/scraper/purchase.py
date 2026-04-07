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
                    await page.wait_for_timeout(2000)
            except Exception as e:
                logger.warning(f"Error al pulsar boton login top: {e}")
        
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
    current_step = "Iniciando"
    steps_trace = []

    async def record_step(msg):
        nonlocal current_step
        current_step = msg
        steps_trace.append(msg)
        logger.info(f"👉 Paso: {msg}")
        try:
            msg_bytes = await page.screenshot(type="jpeg", quality=40)
            live_view_manager.update_frame(product_id, msg_bytes)
        except Exception as e:
            logger.warning(f"Sensor no pudo capturar frame en '{msg}' (posible navegación o cierre de pestaña).")

    try:
        # ── Paso 0: Enrutamiento Óptimo de Almacén ──
        from app.scraper.monitor import check_stock
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
        
        await record_step("Calculando enrutamiento de almacén...")
        stock_info = await check_stock(page, product_url)
        
        best_wh = None
        if stock_info and stock_info.warehouses:
            physicals = [w for w in stock_info.warehouses if w.warehouse_stock > 0]
            transits = [w for w in stock_info.warehouses if w.transit_stock > 0]
            
            if physicals:
                # Priorizar Camagüey, el resto después
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
            logger.info(f"📍 URL de compra enrutada al almacén prioritario: {best_wh.name} ({best_wh.address_id})")

        # ── Paso 1: Añadir al carrito ──
        await record_step("Navegando a la URL del producto")

        # Asegurar que estamos en la página del producto
        if page.url != product_url:
            await page.goto(product_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)
            
        # ── BYPASS DE LOGIN PROACTIVO (Para evitar carritos vacíos) ──
        login_result = await execute_login_bypass(page, email, password, record_step)
        if not login_result.get("success") and "Ya estaba logueado" not in login_result.get("message", ""):
            if login_result.get("message") != "CRÍTICO: Sesión bloqueada y faltan credenciales maestras.":
                logger.error(login_result["message"])
            return login_result
            
        # Si nos mandó al inicio (ej. por re-login), volvemos a la página del producto
        if page.url != product_url:
            await page.goto(product_url, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)

        # (Ajuste de cantidad delegado exitosamente a la fase del Carrito)

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

        await record_step("Insertando al Carrito")
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
        await record_step("Fase: Navegación hacia el Carrito")
        logger.info("🛒 Buscando enlace al carrito...")
        
        # Intentar click en icono de carrito o navegar directamente
        try:
            await record_step("Buscando icono visual del Carrito en el menú superior")
            cart_link = await page.wait_for_selector(
                CHECKOUT_SELECTORS["go_to_cart"], timeout=5000
            )
            await record_step("Clickeando el icono del Carrito")
            await cart_link.click()
            await page.wait_for_timeout(2000)
        except PlaywrightTimeout:
            await record_step("Icono de carrito no detectado. Forzando navegación por URL (/cart)")
            try:
                await page.goto(
                    f"{settings.dofimall_base_url}/cart",
                    wait_until="domcontentloaded",
                    timeout=20000,
                )
            except PlaywrightTimeout:
                await record_step("Advertencia: La red está inestable (Timeout esperado). Forzando continuación.")
                logger.warning("⚠️ Timeout esperando domcontentloaded en el carrito, continuando de todos modos...")
            await page.wait_for_timeout(2000)
            
        await record_step(f"Verificando carga de pasarela (URL actual: {page.url})")
        logger.info(f"📍 En el carrito: {page.url}")

        # ── Paso 3: Verificar Selección Inteligente ──
        await record_step("Fase: Verificación inteligente de items")
        try:
            # Esperamos que la página reflexione selección (texto o clases css).
            # DofiMall usa Vue con la clase 'active' en el botón go_buy cuando está listo para pagar
            ready_indicator = page.locator(".go_buy.active, .go_submit.active").first
            await ready_indicator.wait_for(state="attached", timeout=3000)
            logger.info("✅ Vue.js confirma que los productos están seleccionados (botón activo).")
        except PlaywrightTimeout:
            logger.info("⚠️ El botón Pagar no está activo. Probablemente el carrito esté desmarcado.")
            try:
                # Forzar click de seleccionar todo solo si es estrictamente necesario
                select_all = page.locator("span, div").filter(has_text="Seleccionar todo").last
                await select_all.scroll_into_view_if_needed()
                await select_all.click(force=True)
                await page.wait_for_timeout(1000)
            except: pass

        # ── Ajustar Cantidad Exacta dentro del carrito ──
        if target_quantity > 1:
            try:
                await record_step(f"Ajustando la cantidad deseada al lote de ataque: {target_quantity} uds")
                cart_qty_input = page.locator("input[type='number']").first
                
                if await cart_qty_input.count() > 0:
                    await cart_qty_input.fill(str(target_quantity))
                    await cart_qty_input.press("Enter")
                    # ESPERA INTELIGENTE DE RED: Al presionar Enter, Vue recalcula y lanza un XHR.
                    logger.info("⏳ Esperando estabilización de red por reactividad de Vue...")
                    try:
                        await page.wait_for_load_state("networkidle", timeout=6000)
                    except PlaywrightTimeout:
                        logger.warning("⚠️ Timeout esperando networkidle tras ajustar cantidad. Avanzando de todos modos.")
                    
                    logger.info(f"✔️ Cantidad blindada en carrito a {target_quantity} y UI estabilizada.")
            except Exception as e:
                logger.warning(f"Aviso de intercepción ajustando cantidad en carrito: {e}")
                await record_step("Aviso: Fallo visual ajustando la cantidad. Continuando...")

        # ── Click Inteligente en botón de pagar/checkout ──
        await record_step("Escaneando el DOM buscando el botón final de PAGO (Checkout)")
        try:
            # Según extracción del DOM: <div data-v-15d3b788="" class="go_buy cursor_pointer go_submit">Pagar</div>
            # Cuando está inactivo NO tiene la clase activa. Cuando está listo suele estar activo.
            checkout_locator = page.locator(".go_buy.go_submit, div:has-text('Pagar')").locator("visible=true").first
            await checkout_locator.wait_for(state="attached", timeout=6000)
            checkout_btn = checkout_locator
            await record_step("Botón de Pagar activo, visible y detectado.")
        except PlaywrightTimeout:
            try:
                # Plan B por si 'active' no está presente pero el texto sí
                # Usar xpath o cadena engarzada >> visible=true para compatibilidad robusta
                checkout_locator = page.locator("div.go_buy, div.go_submit").locator("visible=true").last
                await checkout_locator.wait_for(state="attached", timeout=5000)
                checkout_btn = checkout_locator
                await record_step("Botón de Pagar detectado mediante texto fallback.")
            except PlaywrightTimeout:
                checkout_btn = None

        if not checkout_btn:
            await record_step("CRÍTICO: No se encontró el botón de PAGO. Generando volcado del DOM")
            import os
            os.makedirs("logs", exist_ok=True)
            content = await page.content()
            with open("logs/last_checkout_fail.html", "w", encoding="utf-8") as f:
                f.write(content)
                
            result["message"] = "No se encontró el botón de checkout visible y activo (DOM guardado)"
            logger.error(f"❌ {result['message']}")
            await page.screenshot(path="screenshots/checkout_btn_not_found.png")
            return result
            
        await record_step("Inyectando Clic Quirúrgico en Pagar ('Checkout')")
        try:
            # 1. Esperar que desaparezcan capas de carga comunes (bloqueadores visuales)
            loading_mask = page.locator(".el-loading-mask:visible").first
            if await loading_mask.count() > 0:
                logger.info("⏳ Detectada máscara de carga, esperando a que desaparezca...")
                await loading_mask.wait_for(state="hidden", timeout=5000)

            # 2. Scrollear al botón
            await checkout_btn.scroll_into_view_if_needed()
            
            # 3. Clic Quirúrgico Basado en Coordenadas (Bypass de interceptores)
            box = await checkout_btn.bounding_box()
            if box:
                logger.info(f"🎯 Calculadas coordenadas Box(X={box['x']}, Y={box['y']}). Disparando Mouse nativo.")
                await page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            else:
                await checkout_btn.click(force=True, timeout=5000)
                logger.info("🖱️ Fallback a Click force nativo de Playwright")

        except Exception as e:
            await checkout_btn.evaluate("element => element.click()")
            logger.info(f"🖱️ Fallback puro JS Click en 'Pagar'. Error previo: {e}")
        
        # Esperamos explícitamente a que Vue monte la nueva pantalla
        await page.wait_for_timeout(4000)

        # ── Paso 4: Enviar pedido y aceptar condiciones ──
        await record_step("Fase: Confirmación final del pedido")
        # 1. Click en el botón "Enviar pedido"
        try:
            await record_step("Buscando botón 'Enviar pedido'")
            enviar_btn = page.locator("button:has-text('Enviar pedido'), span:has-text('Enviar pedido'), .submit-btn, .goBuy").last
            await enviar_btn.wait_for(state="attached", timeout=10000)
            # DofiMall tiene muchas capas superpuestas en el pre-checkout. Siempre forzamos.
            try:
                await enviar_btn.evaluate("element => element.click()")
                logger.info("🖱️ DOM JS Click ejecutado en 'Enviar pedido'")
            except:
                await enviar_btn.click(force=True)
                logger.info("🖱️ Force Click ejecutado en 'Enviar pedido'")
            # Dar tiempo a que el modal "Aviso" emerja con su animación
            await page.wait_for_timeout(3000)
        except PlaywrightTimeout:
            await record_step("Advertencia: No se detectó 'Enviar pedido'.")

        # 2. Click en el modal de "Aviso" (Estoy de acuerdo)
        try:
            await record_step("Buscando botón 'Estoy de acuerdo' en el aviso legal")
            # Busqueda infalible: Filtrando el typo del desarrollador de Vue ('colse' en vez de 'close'). 
            acuerdo_btn = page.locator("div.agreement-btn:not(.agreement-btn--colse)").last
            await acuerdo_btn.wait_for(state="visible", timeout=10000)
            
            await acuerdo_btn.evaluate("element => element.click()")
            logger.info("🖱️ Click ejecutado en 'Estoy de acuerdo'")
            
            # CRÍTICO: Una vez dado clic, DofiMall envía el POST request de compra.
            await record_step("Transacción enviada. Esperando redirección bancaria a /buy/Pay...")
            
            # Esperar activamente a que la URL cambie (éxito al 100%)
            try:
                async with page.expect_navigation(timeout=15000):
                    pass
            except Exception:
                await page.wait_for_timeout(5000)
            
        except PlaywrightTimeout:
            # Si llegamos aquí y no hay botón de acuerdo ni redirección, el sistema ha fallado en el Pagar
            import os
            os.makedirs("logs", exist_ok=True)
            await page.screenshot(path="logs/checkout_final_fail.png", full_page=True)
            content = await page.content()
            with open("logs/checkout_final_fail.html", "w", encoding="utf-8") as f:
                f.write(content)
                
            result["message"] = "CRÍTICO: No apareció el aviso legal ni hubo redirección tras Enviar pedido."
            logger.error(f"❌ {result['message']} (Screenshot y DOM guardados en logs/)")
            return result

        # ── Paso 5: Completado y reporte ──
        await record_step("Fase: Operación final completada")
        checkout_url = page.url
        result["success"] = True
        result["checkout_url"] = checkout_url
        
        trace_str = "".join([f"✅ {step}\n" for step in steps_trace])
        result["message"] = f"¡Reserva completada! Redirigido a pasarela de pago: {checkout_url}\n\nDetalle de Operaciones:\n{trace_str}"

        logger.info(f"🎉 ¡RESERVA EXITOSA! Checkout URL: {checkout_url}")

        # Tomar screenshot como evidencia suavemente
        try:
            await page.screenshot(path="screenshots/checkout_success.png")
        except:
            pass

        return result

    except PlaywrightTimeout as e:
        trace_str = '\n'.join(steps_trace)
        result["message"] = f"TIMEOUT en paso 👉 '{current_step}'\n\nPasos ejecutados:\n{trace_str}"
        logger.error(f"⏱️ {result['message']}")
        try:
            await page.screenshot(path="screenshots/checkout_timeout.png")
        except:
            pass
        return result

    except Exception as e:
        trace_str = '\n'.join(steps_trace)
        result["message"] = f"CRASH en paso 👉 '{current_step}': {str(e)}\n\nPasos ejecutados:\n{trace_str}"
        logger.error(f"💥 {result['message']}")
        try:
            await page.screenshot(path="screenshots/checkout_error.png")
        except:
            pass
        return result
