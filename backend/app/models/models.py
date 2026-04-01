from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum as SAEnum, JSON
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class ProductStatus(str, enum.Enum):
    MONITORING = "monitoring"       # Activamente monitorizando
    IN_STOCK = "in_stock"           # Detectado en stock
    RESERVED = "reserved"           # Añadido al carrito / reservado
    PAUSED = "paused"               # Pausado por el usuario
    ERROR = "error"                 # Error en el scraping


class LogLevel(str, enum.Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(500), nullable=False)
    name = Column(String(300), default="Sin nombre")
    image_url = Column(String(500), nullable=True)
    price = Column(String(50), nullable=True)
    status = Column(SAEnum(ProductStatus), default=ProductStatus.MONITORING)
    is_active = Column(Boolean, default=True)
    last_checked = Column(DateTime, nullable=True)
    last_in_stock = Column(DateTime, nullable=True)
    check_count = Column(Integer, default=0)
    notes = Column(Text, nullable=True)

    # Stock data
    warehouse_stock = Column(Integer, default=0)    # Stock global en almacén
    transit_stock = Column(Integer, default=0)       # Stock global en tránsito
    stock_type = Column(Integer, nullable=True)      # 0=almacén, 1=tránsito, 2=producción
    stock_type_label = Column(String(100), nullable=True)
    warehouse_breakdown = Column(JSON, nullable=True)  # [{name, warehouse_stock, transit_stock, area}, ...]

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ActionLog(Base):
    __tablename__ = "action_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, nullable=True)
    product_name = Column(String(300), nullable=True)
    action = Column(String(100), nullable=False)
    level = Column(SAEnum(LogLevel), default=LogLevel.INFO)
    message = Column(Text, nullable=False)
    screenshot_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class StockHistory(Base):
    __tablename__ = "stock_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, nullable=False)
    old_warehouse_stock = Column(Integer, default=0)
    new_warehouse_stock = Column(Integer, default=0)
    old_transit_stock = Column(Integer, default=0)
    new_transit_stock = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
