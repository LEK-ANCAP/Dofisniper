"""API routes para gestión de productos monitorizados."""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload
from typing import List
from app.core.database import get_db
from app.models.models import Product, ProductStatus
from app.schemas.schemas import ProductCreate, ProductUpdate, ProductResponse
from app.scraper.browser import browser_manager
from app.scraper.purchase import add_to_cart_and_checkout
from app.scraper.live_view import live_view_manager
from app.notifications.telegram import send_telegram_notification
import httpx
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/products", tags=["products"])
public_router = APIRouter(prefix="/products", tags=["products_public"])


@router.get("/", response_model=List[ProductResponse])
async def get_products(
    status: ProductStatus | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Lista todos los productos monitorizados."""
    query = select(Product).options(joinedload(Product.category)).order_by(Product.created_at.desc())
    if status:
        query = query.where(Product.status == status)
    result = await db.execute(query)
    return result.scalars().all()


@public_router.get("/image-proxy")
async def proxy_image(url: str):
    """Proxy de imágenes de DofiMall para evadir Mixed Content y errores SSL. Público."""
    async def fetch_and_stream():
        # Dofimall a veces falla con HTTPS o rechaza requests sin User-Agent/Referer
        fetch_url = url.replace("https://", "http://") if "shopin.net" in url else url
        
        try:
            async with httpx.AsyncClient(verify=False) as client:
                async with client.stream(
                    "GET", 
                    fetch_url, 
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Referer": "https://www.dofimall.com/"
                    }
                ) as response:
                    async for chunk in response.aiter_bytes():
                        yield chunk
        except Exception:
            pass

    return StreamingResponse(fetch_and_stream(), media_type="image/jpeg")

@router.post("/", response_model=ProductResponse, status_code=201)
async def add_product(product: ProductCreate, db: AsyncSession = Depends(get_db)):
    """Añade un nuevo producto para monitorizar."""
    # Verificar que no exista ya
    existing = await db.execute(
        select(Product).where(Product.url == product.url)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Este producto ya está siendo monitorizado")

    db_product = Product(
        url=product.url,
        name=product.name or "Sin nombre",
        notes=product.notes,
        category_id=product.category_id,
    )
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)
    return db_product


@router.post("/bulk", response_model=List[ProductResponse], status_code=201)
async def add_products_bulk(
    products: List[ProductCreate], db: AsyncSession = Depends(get_db)
):
    """Añade múltiples productos a la vez."""
    created = []
    for product in products:
        existing = await db.execute(
            select(Product).where(Product.url == product.url)
        )
        if existing.scalar_one_or_none():
            continue

        db_product = Product(
            url=product.url,
            name=product.name or "Sin nombre",
            notes=product.notes,
            category_id=product.category_id,
        )
        db.add(db_product)
        created.append(db_product)

    await db.commit()
    for p in created:
        await db.refresh(p)
    return created


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int, update: ProductUpdate, db: AsyncSession = Depends(get_db)
):
    """Actualiza un producto (nombre, estado, activar/pausar)."""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(404, "Producto no encontrado")

    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(product, field, value)

    await db.commit()
    await db.refresh(product)
    return product


@router.delete("/{product_id}")
async def delete_product(product_id: int, db: AsyncSession = Depends(get_db)):
    """Elimina un producto de la monitorización."""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(404, "Producto no encontrado")

    await db.delete(product)
    await db.commit()
    return {"detail": "Producto eliminado"}


@router.post("/{product_id}/toggle")
async def toggle_product(product_id: int, db: AsyncSession = Depends(get_db)):
    """Activa/desactiva la monitorización de un producto."""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(404, "Producto no encontrado")

    product.is_active = not product.is_active
    if product.is_active:
        product.status = ProductStatus.MONITORING
    else:
        product.status = ProductStatus.PAUSED

    await db.commit()
    await db.refresh(product)
    return {"is_active": product.is_active, "status": product.status}


async def _run_checkout_background(product_id: int, product_url: str):
    """Ejecuta el checkout en segundo plano y actualiza la DB al finalizar."""
    from app.core.database import async_session
    from app.models.models import ActionLog, LogLevel, AppSettings
    from sqlalchemy import select
    
    try:
        # Extraer parámetros dinámicos
        async with async_session() as db:
            result_db = await db.execute(select(Product).where(Product.id == product_id))
            prod = result_db.scalar_one_or_none()
            target_qty = prod.target_quantity if prod else 1
            
            settings_db = await db.execute(select(AppSettings).limit(1))
            sys_settings = settings_db.scalar_one_or_none()
            email = sys_settings.dofimall_email if sys_settings else ""
            password = sys_settings.dofimall_password if sys_settings else ""
            
            actual_target_qty = target_qty
            if actual_target_qty == -1:
                total_stock = (prod.warehouse_stock or 0) + (prod.transit_stock or 0)
                actual_target_qty = total_stock if total_stock > 0 else 1

        page = await browser_manager.get_page()
        checkout_result = await add_to_cart_and_checkout(
            page, product_url, 
            target_quantity=actual_target_qty, 
            email=email, password=password,
            product_id=product_id
        )
        await browser_manager.close_page(page)

        # Si triunfa, abrimos una nueva sesión de DB para guardarlo
        if checkout_result.get("success"):
            async with async_session() as db:
                result_db = await db.execute(select(Product).where(Product.id == product_id))
                prod = result_db.scalar_one_or_none()
                if prod:
                    prod.status = ProductStatus.RESERVED
                    
                    # Log de éxito
                    log = ActionLog(
                        product_id=prod.id, product_name=prod.name,
                        action="manual_checkout", level=LogLevel.SUCCESS, 
                        message=checkout_result.get("message", "Checkout finalizado")
                    )
                    db.add(log)
                    await db.commit()

                    # Notificación de Compra Exitosa (Manual)
                    await send_telegram_notification(
                        subject="COMPRA MANUAL LOGRADA 🎯",
                        product_name=prod.name,
                        product_url=prod.url,
                        checkout_url=checkout_result.get("checkout_url"),
                        is_purchase=True,
                        quantity=actual_target_qty,
                        warehouse=prod.warehouse_breakdown
                    )
            return checkout_result
        else:
            # Log de fallo capturado internamente
            async with async_session() as db:
                result_db = await db.execute(select(Product).where(Product.id == product_id))
                prod = result_db.scalar_one_or_none()
                if prod:
                    log = ActionLog(
                        product_id=prod.id, product_name=prod.name,
                        action="manual_checkout_failed", level=LogLevel.ERROR, 
                        message=checkout_result.get("message", "Error desconocido")
                    )
                    db.add(log)
                    await db.commit()
            return checkout_result
            
    except Exception as e:
        # Failsafe critical
        try:
            async with async_session() as db:
                log = ActionLog(
                    product_id=product_id, product_name="Checkout Tester",
                    action="manual_checkout_crash", level=LogLevel.ERROR, 
                    message=f"Excepción dura: {str(e)}"
                )
                db.add(log)
                await db.commit()
        except:
            pass
        return {"success": False, "message": f"Excepción crítica durante checkout: {str(e)}"}


@router.post("/{product_id}/checkout")
async def manual_checkout(product_id: int, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """Ejecuta el flujo de checkout manualmente en segundo plano para pruebas."""
    if not browser_manager.is_running:
        raise HTTPException(
            status_code=503, 
            detail="Browser manager no está corriendo. Ejecuta el backend correctamente o revisa los logs."
        )

    result_db = await db.execute(select(Product).where(Product.id == product_id))
    product = result_db.scalar_one_or_none()
    
    if not product:
        raise HTTPException(404, "Producto no encontrado")

    # Ejecutar checkout de forma asíncrona pero bloqueando (esperando)
    # para poder devolver la traza directa al frontend y la inserte en el terminal
    final_result = await _run_checkout_background(product.id, product.url)
    return final_result

@router.get("/{product_id}/live-view")
async def get_product_live_view(product_id: int):
    """Retorna el último frame en base64 para visualización en tiempo real."""
    frame = live_view_manager.get_frame(product_id)
    return {"frame": frame}
