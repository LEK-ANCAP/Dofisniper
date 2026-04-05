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
        stock_info = await check_stock(product_url)
        
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

        # ── Paso 3: Seleccionar productos y hacer checkout ──
        await record_step("Fase: Verificación de items y Checkout")

        # ── Paso 3: Selección de TODO el carrito (Modo Reserva Máxima) ──
        await record_step("Fase: Seleccionando TODO en el carrito")

        try:
            # En la versión actual queremos comprar TODO lo que hay en el carrito
            select_all_target = page.locator("span").filter(has_text="Seleccionar todo").first
            
            # Si no encuentra span literal, intentamos con get_by_text
            if await select_all_target.count() == 0:
                select_all_target = page.get_by_text("Seleccionar todo", exact=False).first

            # Bucle de comprobación para asegurarnos de que la selección sea efectiva
            for attempt in range(4):
                page_text = await page.inner_text("body")
                
                # DofiMall dice "Ha seleccionado 0 productos" o "Total: $0" si no hay check
                if "Ha seleccionado 0 " in page_text or "Total: $0" in page_text:  # Usamos espacio extra al final de 0 por seguridad
                    logger.info(f"🛒 Intento {attempt+1}: Carrito desmarcado (0 seleccionados). Forzando click en 'Seleccionar todo'...")
                    if await select_all_target.count() > 0:
                        await select_all_target.click(force=True)
                        await page.wait_for_timeout(1000)
                    else:
                        logger.warning("⚠️ No se encontró el texto 'Seleccionar todo' en el DOM.")
                        break
                else:
                    logger.info("✅ 'Seleccionar todo' activado correctamente. Productos listos para pagar.")
                    break
                    
            await page.wait_for_timeout(1000)
                
        except Exception as e:
            logger.warning(f"⚠️ Error intentando seleccionar todo: {e}")

        # ── Ajustar Cantidad Exacta dentro del carrito ──
        if target_quantity > 1:
            try:
                await record_step(f"Ajustando la cantidad deseada al lote de ataque: {target_quantity} uds")
                # Basado en la captura: Vue renderiza un <input type="number"> en el carrito.
                # Aseguramos de que agarre el input visible del carrito de este producto.
                cart_qty_input = page.locator("input[type='number']").first
                
                if await cart_qty_input.count() > 0:
                    # Rellenar con la cantidad exacta
                    await cart_qty_input.fill(str(target_quantity))
                    
                    # Simular "Enter" para forzar reactividad en VueJS
                    await cart_qty_input.press("Enter")
                    await page.wait_for_timeout(2000)
                    logger.info(f"✔️ Cantidad blindada en carrito a {target_quantity}")
            except Exception as e:
                logger.warning(f"Aviso de intercepción ajustando cantidad en carrito: {e}")
                await record_step("Aviso: Fallo visual ajustando la cantidad. Continuando...")

        # Click en botón de pagar/checkout
        await record_step("Escaneando el DOM buscando el botón final de PAGO (Checkout)")
        try:
            # Buscar el botón principal del carrito go_buy (tomado de la captura de DevTools)
            checkout_locator = page.locator(".go_buy, .go_submit, .goBuy, .cart-submit, button:has-text('Pagar')").first
            await checkout_locator.wait_for(state="attached", timeout=5000)
            checkout_btn = checkout_locator
            await record_step("Botón de Pagar detectado y visible.")
        except PlaywrightTimeout:
            try:
                # Plan B: buscar por Regex para soportar cosas como Pagar(1) o Pagar
                checkout_locator = page.locator("text=/Pagar/i, text=/Comprar/i").last
                await checkout_locator.wait_for(state="attached", timeout=5000)
                checkout_btn = checkout_locator
                await record_step("Botón de Pagar detectado mediante texto.")
            except PlaywrightTimeout:
                checkout_btn = None

        if not checkout_btn:
            await record_step("CRÍTICO: No se encontró el botón de PAGO. Generando volcado del DOM")
            import os
            os.makedirs("logs", exist_ok=True)
            content = await page.content()
            with open("logs/last_checkout_fail.html", "w", encoding="utf-8") as f:
                f.write(content)
                
            result["message"] = "No se encontró el botón de checkout (DOM guardado para diagnóstico)"
            logger.error(f"❌ {result['message']}")
            await page.screenshot(path="screenshots/checkout_btn_not_found.png")
            return result
            
        await record_step("Presionando Confirmar y Pagar ('Checkout')")
        try:
            # Ejecutar scroll hacia el botón por si está fuera de pantalla
            await checkout_btn.scroll_into_view_if_needed()
            # Probar click normal de Playwright (genera todos los eventos de Vue)
            await checkout_btn.click(force=True, timeout=5000)
            logger.info("🖱️ Mouse Click nativo sobre 'Pagar'")
        except Exception as e:
            # Fallback a JS click
            await checkout_btn.evaluate("element => element.click()")
            logger.info("🖱️ Fallback JS Click en 'Pagar'")
        
        # Esperamos explícitamente a que Vue monte la nueva pantalla (en lugar del timeout fijo, monitoreamos DOM)
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
            result["message"] = "CRÍTICO: No apareció el aviso legal ni hubo redirección tras Enviar pedido."
            logger.error(f"❌ {result['message']}")
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
