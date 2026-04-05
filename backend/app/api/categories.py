from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, exc
from typing import List
from app.core.database import get_db
from app.models.models import ProductCategory
from app.schemas.schemas import ProductCategoryCreate, ProductCategoryUpdate, ProductCategoryResponse

router = APIRouter(prefix="/categories", tags=["Categories"])

@router.get("", response_model=List[ProductCategoryResponse])
async def get_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ProductCategory))
    return result.scalars().all()

@router.post("", response_model=ProductCategoryResponse)
async def create_category(category: ProductCategoryCreate, db: AsyncSession = Depends(get_db)):
    db_category = ProductCategory(
        name=category.name,
        color=category.color
    )
    db.add(db_category)
    try:
        await db.commit()
        await db.refresh(db_category)
    except exc.IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Category name already exists")
    return db_category

@router.patch("/{category_id}", response_model=ProductCategoryResponse)
async def update_category(category_id: int, category_update: ProductCategoryUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ProductCategory).where(ProductCategory.id == category_id))
    db_category = result.scalar_one_or_none()
    
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
        
    if category_update.name is not None:
        db_category.name = category_update.name
    if category_update.color is not None:
        db_category.color = category_update.color
        
    try:
        await db.commit()
        await db.refresh(db_category)
    except exc.IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Category name already exists")
    
    return db_category

@router.delete("/{category_id}")
async def delete_category(category_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ProductCategory).where(ProductCategory.id == category_id))
    db_category = result.scalar_one_or_none()
    
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
        
    await db.delete(db_category)
    await db.commit()
    return {"success": True, "message": "Category deleted"}
