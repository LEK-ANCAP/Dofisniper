from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, asc
from app.core.database import get_db
from app.models.models import StockHistory, ActionLog, Product
from typing import List, Dict, Any

router = APIRouter(tags=["Analytics"])

@router.get("/analytics/product/{product_id}")
async def get_product_analytics(product_id: int, db: AsyncSession = Depends(get_db)):
    """
    Obtiene el historial combinado de stock y eventos (ActionLogs) para un producto.
    Esto permite dibujar una gráfica interactiva de oferta y demanda.
    """
    
    # Verificar existencia
    prod_query = await db.execute(select(Product).where(Product.id == product_id))
    prod = prod_query.scalar_one_or_none()
    if not prod:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
        
    # Obtener historial de stock
    stock_query = await db.execute(
        select(StockHistory)
        .where(StockHistory.product_id == product_id)
        .order_by(asc(StockHistory.created_at))
    )
    stock_records = stock_query.scalars().all()
    
    # Obtener logs críticos (compras automáticas, o cambios manuales relevantes)
    # Filtro solo acciones específicas para no saturar gráficas
    logs_query = await db.execute(
        select(ActionLog)
        .where(ActionLog.product_id == product_id)
        .where(ActionLog.action.in_(["auto_purchase", "auto_purchase_failed"]))
        .order_by(asc(ActionLog.created_at))
    )
    log_records = logs_query.scalars().all()
    
    # Unificar la línea de tiempo
    timeline: List[Dict[str, Any]] = []
    
    for s in stock_records:
        timeline.append({
            "type": "stock",
            "timestamp": s.created_at.isoformat(),
            "warehouse_stock": s.new_warehouse_stock,
            "transit_stock": s.new_transit_stock,
            "total_stock": (s.new_warehouse_stock or 0) + (s.new_transit_stock or 0)
        })
        
    for l in log_records:
        timeline.append({
            "type": "event",
            "timestamp": l.created_at.isoformat(),
            "event_name": "Compra" if l.action == "auto_purchase" else "Trámite Fallido",
            "message": l.message
        })
        
    # Ordenar ambas colecciones unificadas por tiempo cronológico (antiguo a nuevo)
    timeline.sort(key=lambda x: x["timestamp"])
    
    return {
        "product_name": prod.name,
        "timeline": timeline
    }
