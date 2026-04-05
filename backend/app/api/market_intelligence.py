from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, func
from sqlalchemy.orm import joinedload
from app.core.database import get_db
from app.models.models import Product, ProductSnapshot, ProductAnalytics, ProductCategory, ProductStatus
from datetime import datetime, timedelta, timezone
import collections

router = APIRouter(prefix="/market-intelligence", tags=["intelligence"])

async def calculate_product_analytics(product_id: int, db: AsyncSession):
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)

    result_analytics = await db.execute(select(ProductAnalytics).where(ProductAnalytics.product_id == product_id))
    analytics = result_analytics.scalar_one_or_none()
    
    if not analytics:
        analytics = ProductAnalytics(product_id=product_id)
        db.add(analytics)

    query_snapshots = select(ProductSnapshot).where(
        ProductSnapshot.product_id == product_id,
        ProductSnapshot.created_at >= seven_days_ago
    ).order_by(ProductSnapshot.created_at.asc())
    
    result_snaps = await db.execute(query_snapshots)
    snaps = result_snaps.scalars().all()
    
    if len(snaps) < 2:
        return
        
    depletion_events = 0
    total_stock_moved = 0
    total_stock_accumulated = 0
    zero_stock_minutes = 0
    
    for i in range(1, len(snaps)):
        prev = snaps[i-1]
        curr = snaps[i]
        
        prev_total = prev.stock_quantity + prev.transit_quantity
        curr_total = curr.stock_quantity + curr.transit_quantity
        
        if curr_total < prev_total:
            depletion_events += 1
            total_stock_moved += (prev_total - curr_total)
            
        if curr_total > prev_total:
             total_stock_accumulated += (curr_total - prev_total)
             
        if curr_total == 0:
            zero_stock_minutes += 1

    # Heurística Demand Score (Escala 0-100)
    base_score = min((depletion_events / max(len(snaps)/12, 1)) * 100, 100) 
    
    # Trend Analysis
    if len(snaps) >= 12:
        recent = snaps[-6:]
        older = snaps[-12:-6]
        avg_recent = sum(s.stock_quantity + s.transit_quantity for s in recent) / len(recent)
        avg_older = sum(s.stock_quantity + s.transit_quantity for s in older) / len(older)
        
        if avg_recent < avg_older * 0.9:
            analytics.trend = "bearish"
        elif avg_recent > avg_older * 1.1:
            analytics.trend = "bullish"
        else:
            analytics.trend = "neutral"
            
    analytics.demand_score = float(base_score)
    analytics.stock_velocity = float(total_stock_moved)
    
    # Availability Rate (Stock > 0 %)
    if len(snaps) > 0:
         analytics.availability_rate = 100.0 - ((zero_stock_minutes / len(snaps)) * 100.0)
         
    # Simple Extrapolation of next restock (very naive ML approach: average cycle days)
    # Just an estimation metric:
    if total_stock_accumulated > 0:
        cycles = max(total_stock_accumulated / max(curr_total, 1), 1)
        analytics.restock_cycle_days = 7.0 / cycles
        analytics.next_restock_estimate = now + timedelta(days=analytics.restock_cycle_days)
    
    await db.commit()

@router.post("/recalculate/{product_id}")
async def force_recalculation(product_id: int, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    background_tasks.add_task(calculate_product_analytics, product_id, db)
    return {"message": "Recalculation queued"}

@router.get("/dashboard")
async def get_intelligence_dashboard_kpis(db: AsyncSession = Depends(get_db)):
    """ Retorna los 8 KPIs agregados super-rápidos para el Header """
    result = await db.execute(select(ProductAnalytics))
    analytics = result.scalars().all()
    
    all_products_res = await db.execute(select(Product))
    products = all_products_res.scalars().all()

    if not analytics or not products:
        return {
            "global_demand_score": 0,
            "bearish_products": 0,
            "availability_rate": 0,
            "total_velocity": 0,
            "fastest_depletion": "-",
            "total_transit": 0,
            "total_warehouse": 0,
            "zero_cycle_count": 0
        }

    global_demand = sum(a.demand_score for a in analytics) / len(analytics) if len(analytics) > 0 else 0
    bearish = sum(1 for a in analytics if a.trend == 'bearish')
    avg_avail = sum(a.availability_rate for a in analytics) / len(analytics) if len(analytics) > 0 else 0
    velocity = sum(a.stock_velocity for a in analytics)
    
    total_warehouse = sum(p.warehouse_stock for p in products)
    total_transit = sum(p.transit_stock for p in products)
    zero_cycle = sum(1 for a in analytics if a.availability_rate > 95.0)

    fastest = max(analytics, key=lambda x: x.demand_score, default=None)
    top_prod = "-"
    if fastest:
        top_prod = next((p.name for p in products if p.id == fastest.product_id), "-")

    return {
        "global_demand_score": round(global_demand, 1),
        "bearish_products": bearish,
        "availability_rate": round(avg_avail, 1),
        "total_velocity": velocity,
        "fastest_depletion": top_prod,
        "total_transit": total_transit,
        "total_warehouse": total_warehouse,
        "zero_cycle_count": zero_cycle
    }

@router.get("/history/{product_id}")
async def get_product_history(product_id: int, db: AsyncSession = Depends(get_db)):
    """ Series Temporales para ChartJs """
    now = datetime.now(timezone.utc)
    twelve_hours_ago = now - timedelta(hours=12) # Graficamos las últimas 12 horas por min
    
    result = await db.execute(select(ProductSnapshot).where(
        ProductSnapshot.product_id == product_id,
        ProductSnapshot.created_at >= twelve_hours_ago
    ).order_by(ProductSnapshot.created_at.asc()))
    
    snaps = result.scalars().all()
    
    timestamps = [s.created_at.strftime('%H:%M') for s in snaps]
    warehouse = [s.stock_quantity for s in snaps]
    transit = [s.transit_quantity for s in snaps]
    
    return {
        "labels": timestamps,
        "datasets": {
            "warehouse": warehouse,
            "transit": transit
        }
    }

@router.get("/demand-ranking")
async def get_demand_ranking(db: AsyncSession = Depends(get_db)):
    """ Devuelve el array ordenado descendentemente por Demand Score """
    result = await db.execute(
        select(Product.id, Product.name, ProductAnalytics.demand_score, ProductAnalytics.trend)
        .join(ProductAnalytics, Product.id == ProductAnalytics.product_id)
        .order_by(ProductAnalytics.demand_score.desc())
        .limit(15)
    )
    ranking = []
    for row in result:
        ranking.append({
            "id": row.id,
            "name": row.name,
            "score": round(row.demand_score, 1),
            "trend": row.trend
        })
    return ranking

@router.get("/distribution")
async def get_distribution(db: AsyncSession = Depends(get_db)):
    """ Agrupación por Categoría para Doughnut & Stacked Bar """
    result = await db.execute(select(Product).options(joinedload(Product.category)))
    products = result.scalars().all()
    
    category_grouped = collections.defaultdict(lambda: {"warehouse": 0, "transit": 0, "color": "#cbd5e1"})
    
    for p in products:
        cat_name = p.category.name if p.category else "Sin Categoria"
        color = p.category.color if p.category else "#64748b"
        
        category_grouped[cat_name]["warehouse"] += p.warehouse_stock
        category_grouped[cat_name]["transit"] += p.transit_stock
        category_grouped[cat_name]["color"] = color
        
    labels = list(category_grouped.keys())
    warehouse_data = [category_grouped[k]["warehouse"] for k in labels]
    transit_data = [category_grouped[k]["transit"] for k in labels]
    colors = [category_grouped[k]["color"] for k in labels]
    
    return {
        "labels": labels,
        "datasets": {
            "warehouse": warehouse_data,
            "transit": transit_data
        },
        "colors": colors
    }
