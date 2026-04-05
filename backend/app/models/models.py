from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum as SAEnum, JSON
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class ProductStatus(str, enum.Enum):
    MONITORING = "monitoring"       # Activamente monitorizando
    IN_STOCK = "in_stock"           # Detectado en stock
    PURCHASING = "purchasing"       # Compra automática en proceso
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

    # Snipe Config
    target_quantity = Column(Integer, default=1)      # Cantidad que intentar comprar
    min_stock_to_trigger = Column(Integer, default=1) # Stock mínimo para disparar el snipe
    auto_buy = Column(Boolean, default=False)          # Compra automática independiente de monitorización

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


class AppSettings(Base):
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dofimall_email = Column(String(255), nullable=True)
    dofimall_password = Column(String(255), nullable=True)
    keep_alive_enabled = Column(Boolean, default=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
