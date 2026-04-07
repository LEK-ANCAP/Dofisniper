from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, asc
from app.core.database import get_db
from app.models.models import StockHistory, ActionLog, Product
from typing import List, Dict, Any

router = APIRouter(tags=["Analytics"])

from datetime import datetime, timedelta, timezone
from typing import Optional

@router.get("/analytics/product/{product_id}")
async def get_product_analytics(
    product_id: int, 
    period: str = "24h",
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene el historial combinado de stock y eventos para un producto.
    Calcula volúmenes de cambio y diferencia compras del mercado vs compras propias.
    Soporta filtrado por periodos de tiempo.
    """
    
    # Verificar existencia
    prod_query = await db.execute(select(Product).where(Product.id == product_id))
    prod = prod_query.scalar_one_or_none()
    if not prod:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
        
    # Calcular fecha de inicio según periodo
    time_threshold = None
    now = datetime.now(timezone.utc)
    if period == "1h":
        time_threshold = now - timedelta(hours=1)
    elif period == "24h":
        time_threshold = now - timedelta(hours=24)
    elif period == "7d":
        time_threshold = now - timedelta(days=7)
    elif period == "30d":
        time_threshold = now - timedelta(days=30)
        
    # Obtener historial de stock
    stock_stmt = select(StockHistory).where(StockHistory.product_id == product_id).order_by(asc(StockHistory.created_at))
    if time_threshold:
        stock_stmt = stock_stmt.where(StockHistory.created_at >= time_threshold)
    stock_query = await db.execute(stock_stmt)
    stock_records = stock_query.scalars().all()
    
    # Obtener logs críticos (compras)
    logs_stmt = select(ActionLog).where(
        ActionLog.product_id == product_id,
        ActionLog.action.in_(["auto_purchase", "manual_checkout", "auto_purchase_failed", "manual_checkout_failed", "manual_checkout_crash"])
    ).order_by(asc(ActionLog.created_at))
    if time_threshold:
        logs_stmt = logs_stmt.where(ActionLog.created_at >= time_threshold)
    logs_query = await db.execute(logs_stmt)
    log_records = logs_query.scalars().all()
    
    # Unificar la línea de tiempo
    timeline: List[Dict[str, Any]] = []
    
    # ── FASE 1: Procesar Cambios de Stock y calcular Volumen ──
    for s in stock_records:
        old_total = (s.old_warehouse_stock or 0) + (s.old_transit_stock or 0)
        new_total = (s.new_warehouse_stock or 0) + (s.new_transit_stock or 0)
        diff = new_total - old_total
        
        timeline.append({
            "type": "stock",
            "timestamp": s.created_at.replace(tzinfo=timezone.utc).isoformat() if s.created_at.tzinfo is None else s.created_at.isoformat(),
            "raw_timestamp": s.created_at,
            "warehouse_stock": s.new_warehouse_stock,
            "transit_stock": s.new_transit_stock,
            "total_stock": new_total,
            "volume_change": diff,
            "event_category": None # Se llenará en la FASE 2
        })
        
    # ── FASE 2: Clasificar "Mi Compra" vs "Compra del Mercado" ──
    for t in timeline:
        if t["volume_change"] < 0:
            # Hubo una bajada de stock. ¿Fuimos nosotros?
            # Buscamos un ActionLog exitoso en un margen de +/- 60 segundos
            t_time = t["raw_timestamp"].replace(tzinfo=timezone.utc) if t["raw_timestamp"].tzinfo is None else t["raw_timestamp"]
            
            is_my_purchase = False
            for l in log_records:
                l_time = l.created_at.replace(tzinfo=timezone.utc) if l.created_at.tzinfo is None else l.created_at
                time_diff = abs((t_time - l_time).total_seconds())
                
                # Si tenemos un log de compra muy cerca temporalmente del cambio de stock
                if time_diff <= 90 and l.level == "success":
                    is_my_purchase = True
                    break
            
            t["event_category"] = "my_purchase" if is_my_purchase else "market_purchase"
        elif t["volume_change"] > 0:
            t["event_category"] = "restock"
            
    # Limpiar datos crudos para JSON
    for t in timeline:
        del t["raw_timestamp"]
        
    # Añadir logs huérfanos que no provocaron cambio de stock real (ej. Fallos)
    for l in log_records:
        if l.level != "success":
            timeline.append({
                "type": "event",
                "timestamp": l.created_at.replace(tzinfo=timezone.utc).isoformat() if l.created_at.tzinfo is None else l.created_at.isoformat(),
                "event_category": "failed_purchase",
                "message": l.message
            })

    # Ordenar cronológicamente
    timeline.sort(key=lambda x: x["timestamp"])
    
    # ── FASE 3: Downsampling para periodos excesivamente largos (7d o 30d) ──
    # Para mantener el frontend rápido, agrupamos datos
    if period in ["7d", "30d"] and len(timeline) > 100:
        downsampled = []
        # Agrupar por hora (yyyy-mm-dd hh)
        grouped = {}
        for item in timeline:
            if item["type"] == "stock":
                hora = item["timestamp"][:13] # Corta hasta la hora: "2023-10-27T14"
                if hora not in grouped:
                    grouped[hora] = item
                else:
                    # Sobrescribir con el dato más reciente de esa hora
                    grouped[hora]["warehouse_stock"] = item["warehouse_stock"]
                    grouped[hora]["transit_stock"] = item["transit_stock"]
                    grouped[hora]["total_stock"] = item["total_stock"]
                    # Sumar volatilidades (volúmenes)
                    grouped[hora]["volume_change"] += item["volume_change"]
                    
                    # Conservar el evento de mayor prioridad en esa hora
                    if item["event_category"] == "my_purchase":
                        grouped[hora]["event_category"] = "my_purchase"
                    elif item["event_category"] == "market_purchase" and grouped[hora]["event_category"] != "my_purchase":
                        grouped[hora]["event_category"] = "market_purchase"
            else:
                downsampled.append(item) # Conservar todos los fallos
                
        # Re-convertir a lista y ordenar
        stocks_only = list(grouped.values())
        timeline = sorted(stocks_only + downsampled, key=lambda x: x["timestamp"])
    
    return {
        "product_name": prod.name,
        "timeline": timeline,
        "period": period,
        "data_points": len(timeline)
    }
