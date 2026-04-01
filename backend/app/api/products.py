"""API routes para gestión de productos monitorizados."""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from app.core.database import get_db
from app.models.models import Product, ProductStatus
from app.schemas.schemas import ProductCreate, ProductUpdate, ProductResponse
from app.scraper.browser import browser_manager
from app.scraper.purchase import add_to_cart_and_checkout

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/", response_model=List[ProductResponse])
async def get_products(
    status: ProductStatus | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Lista todos los productos monitorizados."""
    query = select(Product).order_by(Product.created_at.desc())
    if status:
        query = query.where(Product.status == status)
    result = await db.execute(query)
    return result.scalars().all()


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
    from app.models.models import ActionLog, LogLevel
    
    try:
        page = await browser_manager.get_page()
        checkout_result = await add_to_cart_and_checkout(page, product_url)
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

    # Disparamos tarea en background para no bloquear otras llamadas mientras Playwright espera
    background_tasks.add_task(_run_checkout_background, product.id, product.url)

    return {"success": True, "message": "Checkout iniciado en segundo plano. Comprueba la pestaña 'Actividad'."}
