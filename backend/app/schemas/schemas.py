from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Optional, Any
from app.models.models import ProductStatus, LogLevel


# --- Categories ---

class ProductCategoryCreate(BaseModel):
    name: str
    color: Optional[str] = "#38BDF8"

class ProductCategoryUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None

class ProductCategoryResponse(BaseModel):
    id: int
    name: str
    color: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# --- Products ---

class ProductCreate(BaseModel):
    url: str
    name: Optional[str] = "Sin nombre"
    notes: Optional[str] = None
    category_id: Optional[int] = None


class ProductUpdate(BaseModel):
    url: Optional[str] = None
    name: Optional[str] = None
    is_active: Optional[bool] = None
    status: Optional[ProductStatus] = None
    notes: Optional[str] = None
    min_local_to_trigger: Optional[int] = None
    target_qty_local: Optional[int] = None
    min_transit_to_trigger: Optional[int] = None
    target_qty_transit: Optional[int] = None
    auto_buy: Optional[bool] = None
    category_id: Optional[int] = None


class ProductResponse(BaseModel):
    id: int
    url: str
    name: str
    image_url: Optional[str] = None
    price: Optional[str] = None
    status: ProductStatus
    is_active: bool
    last_checked: Optional[datetime] = None
    last_in_stock: Optional[datetime] = None
    check_count: int
    notes: Optional[str] = None
    category_id: Optional[int] = None
    category: Optional[ProductCategoryResponse] = None
    warehouse_stock: int = 0
    transit_stock: int = 0
    stock_type: Optional[int] = None
    stock_type_label: Optional[str] = None
    warehouse_breakdown: Optional[list[dict[str, Any]]] = None
    
    min_local_to_trigger: int = 1
    target_qty_local: int = 1
    min_transit_to_trigger: int = 0
    target_qty_transit: int = 0
    
    auto_buy: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# --- Logs ---

class LogResponse(BaseModel):
    id: int
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    action: str
    level: LogLevel
    message: str
    screenshot_path: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# --- Dashboard ---

class DashboardStats(BaseModel):
    total_products: int
    monitoring: int
    total_checks: int
    scheduler_running: bool


# --- Config ---

class AppConfigUpdate(BaseModel):
    check_interval_minutes: Optional[int] = None
    headless: Optional[bool] = None
    notifications_enabled: Optional[bool] = None

# --- Global Settings ---

class AppSettingsSchema(BaseModel):
    dofimall_email: Optional[str] = None
    dofimall_password: Optional[str] = None
    keep_alive_enabled: Optional[bool] = False
    scan_interval_seconds: int = 3
    purchase_interval_seconds: int = 1
    
    class Config:
        from_attributes = True

class AppSettingsUpdate(BaseModel):
    dofimall_email: Optional[str] = None
    dofimall_password: Optional[str] = None
    keep_alive_enabled: Optional[bool] = None
    scan_interval_seconds: Optional[int] = None
    purchase_interval_seconds: Optional[int] = None


# --- Authentication ---

class UserLogin(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class UserResponse(BaseModel):
    id: int
    email: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
