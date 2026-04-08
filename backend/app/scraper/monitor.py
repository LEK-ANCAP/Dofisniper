"""
Módulo de monitorización de stock.
Usa la API REST de DofiMall para comprobar stock de productos.
"""

import re
import httpx
import asyncio
from urllib.parse import urlparse, parse_qs
from loguru import logger
from datetime import datetime
from app.core.config import get_settings

settings = get_settings()

STOCK_TYPE_LABELS = {
    0: "En almacén",
    1: "En tránsito",
    2: "Esperando producción",
}
VALID_STOCK_TYPES = {0, 1, 2}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "es-ES,es;q=0.9",
}


class WarehouseInfo:
    """Punto de recogida disponible para un producto."""
    def __init__(self, name: str, address_id: int, area: str = "", address: str = ""):
        self.name = name
        self.address_id = address_id
        self.area = area
        self.address = address
        self.warehouse_stock = 0
        self.transit_stock = 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "address_id": self.address_id,
            "area": self.area,
            "address": self.address,
            "warehouse_stock": self.warehouse_stock,
            "transit_stock": self.transit_stock,
        }


class StockCheckResult:
    """Resultado de la comprobación de stock."""

    def __init__(
        self,
        url: str,
        is_available: bool,
        product_name: str | None = None,
        price: str | None = None,
        image_url: str | None = None,
        warehouse_stock: int = 0,
        transit_stock: int = 0,
        stock_type: int | None = None,
        stock_type_label: str | None = None,
        warehouses: list[WarehouseInfo] | None = None,
        warehouse_breakdown: str = "",
        error: str | None = None,
    ):
        self.url = url
        self.is_available = is_available
        self.product_name = product_name
        self.price = price
        self.image_url = image_url
        self.warehouse_stock = warehouse_stock
        self.transit_stock = transit_stock
        self.stock_type = stock_type
        self.stock_type_label = stock_type_label
        self.warehouses = warehouses or []
        self.warehouse_breakdown = warehouse_breakdown
        self.error = error
        self.checked_at = datetime.utcnow()

    @property
    def total_available(self) -> int:
        return self.warehouse_stock + self.transit_stock


def extract_ids_from_url(url: str) -> tuple[str | None, str | None]:
    """Extrae productId y goodsId de una URL de DofiMall."""
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    product_id = params.get("productId", [None])[0]
    goods_id = params.get("goodsId", [None])[0]
    if not product_id:
        match = re.search(r'productId[=:](\d+)', url)
        if match:
            product_id = match.group(1)
    if not goods_id:
        match = re.search(r'goodsId[=:](\d+)', url)
        if match:
            goods_id = match.group(1)
    return product_id, goods_id


async def check_stock(page, product_url: str) -> StockCheckResult:
    """Comprueba el stock verificando almacenes sin multiplicar stock global."""
    try:
        logger.info(f"🔍 Comprobando stock: {product_url}")

        product_id, goods_id = extract_ids_from_url(product_url)
        if not product_id:
            return StockCheckResult(
                url=product_url, is_available=False,
                error="No se pudo extraer productId de la URL",
            )

        api_url = f"{settings.dofimall_base_url}/v3/goods/front/goods/details"
        params = {"productId": product_id}
        if goods_id:
            params["goodsId"] = goods_id

        async with httpx.AsyncClient(
            timeout=30.0,
            headers={**HEADERS, "Referer": product_url},
        ) as client:
            response = await client.get(api_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return await _parse_api_response_all_warehouses(client, product_url, data, product_id, goods_id)

    except httpx.HTTPStatusError as e:
        logger.error(f"❌ HTTP error {e.response.status_code} para: {product_url}")
        return StockCheckResult(
            url=product_url, is_available=False,
            error=f"HTTP {e.response.status_code}",
        )
    except httpx.RequestError as e:
        logger.error(f"❌ Request error para {product_url}: {e}")
        return StockCheckResult(url=product_url, is_available=False, error=str(e))
    except Exception as e:
        logger.error(f"💥 Error comprobando stock de {product_url}: {e}")
        return StockCheckResult(url=product_url, is_available=False, error=str(e))


async def fetch_warehouse_stock(client: httpx.AsyncClient, p2_params: dict, wh: WarehouseInfo):
    """Obtiene el stock específico de un almacén."""
    api_url2 = f"{settings.dofimall_base_url}/v3/goods/front/goods/details2"
    try:
        r2 = await client.get(api_url2, params=p2_params)
        r2.raise_for_status()
        d2 = r2.json()
        real_stock_data = d2.get("data") or d2
        stock_default_product = real_stock_data.get("defaultProduct") or {}
        wh.warehouse_stock = int(stock_default_product.get("productStock") or 0)
        wh.transit_stock = int(stock_default_product.get("transitStock") or 0)
    except Exception as e:
        logger.warning(f"⚠️ Error obteniendo details2 para almacén {wh.name}: {e}")


async def _parse_api_response_all_warehouses(
    client: httpx.AsyncClient, 
    product_url: str, 
    data: dict, 
    product_id: str, 
    goods_id: str | None
) -> StockCheckResult:
    """Parsea DofiMall. El tránsito SIEMPRE es global. El stock físico sí se suma por almacén."""

    detail = data.get("data") or data

    product_name = detail.get("goodsName")
    
    image_url = None
    default_product = detail.get("defaultProduct") or {}
    goods_pics = default_product.get("goodsPics") or []
    if goods_pics and isinstance(goods_pics[0], str):
        image_url = goods_pics[0]
    if not image_url:
        image_url = detail.get("shareImage")
        
    if image_url:
        if image_url.startswith("//"):
            image_url = "https:" + image_url
        elif image_url.startswith("http://"):
            image_url = image_url.replace("http://", "https://")
        elif not image_url.startswith("http"):
            # Si es relativa sin // ni http, asumimos el host de DofiMall
            image_url = f"https://www.dofimall.com{image_url if image_url.startswith('/') else '/' + image_url}"

    price = None
    product_price = default_product.get("productPrice")
    if product_price is not None:
        price = f"${product_price}" if not str(product_price).startswith("$") else str(product_price)

    warehouses_list = detail.get("warehouseVOS") or []
    warehouses = []
    
    tasks = []
    for wh_data in warehouses_list:
        wh = WarehouseInfo(
            name=wh_data.get("name", "Desconocido"),
            address_id=wh_data.get("addressId", 0),
            area=wh_data.get("areaInfo", ""),
            address=wh_data.get("address", ""),
        )
        warehouses.append(wh)
        
        if wh.address_id:
            p2 = {"productId": product_id, "warehouseId": wh.address_id}
            if goods_id:
                p2["goodsId"] = goods_id
            tasks.append(fetch_warehouse_stock(client, p2, wh))
            
    if tasks:
        await asyncio.gather(*tasks)

    # ── Corrección del Cálculo: Stock Físico y Tránsito sí pertenecen a almacenes específicos ──
    total_warehouse_stock = 0
    total_transit_stock = 0
    breakdown_lines = []

    # Al corregir el parÃ¡metro de peticiÃ³n a "warehouseId" en details2,
    # ahora DofiMall SÃ devuelve el desglose de trÃ¡nsito real por sucursal.
    for wh in warehouses:
        total_warehouse_stock += wh.warehouse_stock
        total_transit_stock += wh.transit_stock
        
        has_local = wh.warehouse_stock > 0
        has_transit = wh.transit_stock > 0

        if has_local or has_transit:
            types = []
            if has_local: types.append(f"{wh.warehouse_stock}U (Físico)")
            if has_transit: types.append(f"{wh.transit_stock}U (Tránsito)")
            joined_types = " y ".join(types)
            breakdown_lines.append(f"• {wh.name}: {joined_types}")

    if not tasks:
        stock_default_product = detail.get("defaultProduct") or {}
        total_warehouse_stock = int(stock_default_product.get("productStock") or 0)
        total_transit_stock = int(stock_default_product.get("transitStock") or 0)
        if total_transit_stock > 0:
            breakdown_lines.append(f"• Tránsito: {total_transit_stock} piezas")

    if not breakdown_lines and (total_warehouse_stock == 0 and total_transit_stock == 0):
        breakdown_lines.append("• Sin stock en ningún almacén")

    warehouse_breakdown = "\n".join(breakdown_lines)

    stock_type = detail.get("stockType")
    if stock_type is not None:
        stock_type = int(stock_type)
    stock_type_label = STOCK_TYPE_LABELS.get(stock_type, f"Desconocido ({stock_type})")

    is_valid_type = stock_type in VALID_STOCK_TYPES or stock_type is None
    has_stock = total_warehouse_stock > 0 or total_transit_stock > 0
    
    # If the API says it has stock mathematically, we consider it available
    # regardless of the strict stockType field which may sometimes be omitted.
    is_available = has_stock

    status_msg = (
        f"Tipo: {stock_type_label}, "
        f"Almacén Global: {total_warehouse_stock}U, Tránsito Global: {total_transit_stock}U, "
        f"Puntos de recogida: {len(warehouses)}"
    )
    if is_available:
        logger.info(f"✅ ¡DISPONIBLE!: {product_name or product_url} — {status_msg}")
    else:
        logger.info(f"❌ No disponible: {product_name or product_url} — {status_msg}")

    return StockCheckResult(
        url=product_url,
        is_available=is_available,
        product_name=product_name,
        price=price,
        image_url=image_url,
        warehouse_stock=total_warehouse_stock,
        transit_stock=total_transit_stock,
        stock_type=stock_type,
        stock_type_label=stock_type_label,
        warehouses=warehouses,
        warehouse_breakdown=warehouse_breakdown
    )

def get_best_warehouse(stock_info: StockCheckResult) -> WarehouseInfo | None:
    """Calcula el almacén prioritario según stock disponible y prioridad de sucursales."""
    if not stock_info or not stock_info.warehouses:
        return None
        
    physicals = [w for w in stock_info.warehouses if w.warehouse_stock > 0]
    transits = [w for w in stock_info.warehouses if w.transit_stock > 0]
    
    if physicals:
        physicals.sort(key=lambda w: 0 if "camag" in w.name.lower() else 1)
        return physicals[0]
    elif transits:
        transits.sort(key=lambda w: 0 if "camag" in w.name.lower() else 1)
        return transits[0]
        
    return None


def find_triggering_warehouse(
    stock_result: StockCheckResult,
    min_local: int,
    min_transit: int
) -> tuple[WarehouseInfo, str, int] | None:
    """
    Busca un almacén INDIVIDUAL que cumpla los mínimos configurados.
    
    Args:
        stock_result: Resultado del check de stock con desglose por almacén.
        min_local: Mínimo de stock LOCAL por almacén para disparar. 0 = ignorar local.
        min_transit: Mínimo de stock en TRÁNSITO por almacén para disparar. 0 = ignorar tránsito.
    
    Returns:
        Tupla (warehouse, 'local'|'transit', stock_disponible) del almacén que disparó,
        o None si ninguno cumple los mínimos.
    
    Prioridad: local > tránsito. Dentro de cada tipo, Camagüey primero.
    """
    if not stock_result:
        return None
        
    candidates = []
    
    # Si tenemos desglose por almacén, verificamos individualmente
    if stock_result.warehouses:
        for wh in stock_result.warehouses:
            if min_local > 0 and wh.warehouse_stock >= min_local:
                candidates.append((wh, 'local', wh.warehouse_stock))
            if min_transit > 0 and wh.transit_stock >= min_transit:
                candidates.append((wh, 'transit', wh.transit_stock))
    else:
        # Fallback: Cuando DofiMall solo devuelve stock total (sin desglose)
        if min_local > 0 and stock_result.warehouse_stock >= min_local:
            wh_mock = WarehouseInfo(name="Global/Desconocido", warehouse_stock=stock_result.warehouse_stock, transit_stock=stock_result.transit_stock)
            candidates.append((wh_mock, 'local', stock_result.warehouse_stock))
        elif min_transit > 0 and stock_result.transit_stock >= min_transit:
            wh_mock = WarehouseInfo(name="Global/Desconocido", warehouse_stock=stock_result.warehouse_stock, transit_stock=stock_result.transit_stock)
            candidates.append((wh_mock, 'transit', stock_result.transit_stock))
    
    if not candidates:
        return None
    
    # Priorizar: local > tránsito, luego Camagüey primero
    candidates.sort(key=lambda c: (
        0 if c[1] == 'local' else 1,
        0 if 'camag' in c[0].name.lower() else 1
    ))
    return candidates[0]

