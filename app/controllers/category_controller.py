from datetime import datetime
import re
from typing import Optional, List

from bson import ObjectId
from fastapi import HTTPException, status,UploadFile

from app.config.database import get_database
from app.models.category import CategoryCreate, CategoryUpdate
from app.config.cloudinary import delete_image, extract_public_id
from app.middleware.upload import upload_single_image


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def generate_slug(name: str) -> str:
    """
    Generate a URL-friendly slug from a name.
    """
    # Convert to lowercase
    slug = name.lower()
    
    # Replace spaces with hyphens
    slug = re.sub(r'\s+', '-', slug)
    
    # Remove special characters
    slug = re.sub(r'[^a-z0-9-]', '', slug)
    
    # Remove multiple hyphens
    slug = re.sub(r'-+', '-', slug)
    
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    
    return slug


# ============================================================
# CREATE CATEGORY
# ============================================================

async def create_category(
    category_data: CategoryCreate,
    image_file: UploadFile = None,
) -> dict:
    """
    Create a new category with optional image upload.
    """

    db = get_database()

    # Generate slug
    slug = generate_slug(
        category_data.name
    )

    # Check if category with same name exists
    existing_category = await db.categories.find_one(
        {
            "name": {
                "$regex": f"^{category_data.name}$",
                "$options": "i",
            }
        }
    )

    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this name already exists",
        )

    # Check if category with same slug exists
    existing_slug = await db.categories.find_one(
        {
            "slug": slug
        }
    )

    if existing_slug:
        # Append a number to make it unique
        count = 1
        new_slug = f"{slug}-{count}"
        
        while await db.categories.find_one(
            {"slug": new_slug}
        ):
            count += 1
            new_slug = f"{slug}-{count}"
        
        slug = new_slug

    # Upload image if provided
    image_url = "https://via.placeholder.com/300"
    if image_file:
        image_url = await upload_single_image(
            image_file,
            folder="ai-jewellery-shop/categories",
        )

    # Create category document
    now = datetime.utcnow()

    category_dict = {
        "name": category_data.name.strip(),
        "slug": slug,
        "description": category_data.description,
        "image": image_url,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }

    # Insert into MongoDB
    result = await db.categories.insert_one(
        category_dict
    )

    # Fetch created category
    created_category = await db.categories.find_one(
        {
            "_id": result.inserted_id
        }
    )

    if not created_category:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create category",
        )

    # Convert ObjectId
    created_category["id"] = str(
        created_category["_id"]
    )

    created_category.pop(
        "_id",
        None,
    )

    return {
        "success": True,
        "message": "Category created successfully",
        "category": created_category,
    }


# ============================================================
# GET ALL CATEGORIES
# ============================================================

async def get_categories(
    page: int = 1,
    limit: int = 10,
    search: Optional[str] = None,
    include_inactive: bool = False,
) -> dict:
    """
    Get all categories with pagination and filters.
    """

    db = get_database()

    # Build query
    query = {}

    if not include_inactive:
        query["is_active"] = True

    if search:
        query["name"] = {
            "$regex": search,
            "$options": "i",
        }

    # Pagination
    skip = (page - 1) * limit

    # Get categories
    categories_cursor = db.categories.find(
        query
    ).sort(
        "name",
        1
    ).skip(
        skip
    ).limit(
        limit
    )

    categories = await categories_cursor.to_list(
        length=limit
    )

    # Convert ObjectId to string
    for category in categories:
        category["id"] = str(
            category["_id"]
        )
        category.pop(
            "_id",
            None,
        )

    # Get total count
    total = await db.categories.count_documents(
        query
    )

    return {
        "success": True,
        "categories": categories,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit,
        },
    }


# ============================================================
# GET CATEGORY BY ID
# ============================================================

async def get_category_by_id(
    category_id: str,
) -> dict:
    """
    Get a category by its ID.
    """

    db = get_database()

    if not ObjectId.is_valid(category_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid category ID",
        )

    category = await db.categories.find_one(
        {
            "_id": ObjectId(category_id)
        }
    )

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    # Convert ObjectId
    category["id"] = str(
        category["_id"]
    )

    category.pop(
        "_id",
        None,
    )

    return {
        "success": True,
        "category": category,
    }


# ============================================================
# GET CATEGORY BY SLUG
# ============================================================

async def get_category_by_slug(
    slug: str,
) -> dict:
    """
    Get a category by its slug.
    """

    db = get_database()

    category = await db.categories.find_one(
        {
            "slug": slug,
            "is_active": True,
        }
    )

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    # Convert ObjectId
    category["id"] = str(
        category["_id"]
    )

    category.pop(
        "_id",
        None,
    )

    return {
        "success": True,
        "category": category,
    }


# ============================================================
# UPDATE CATEGORY
# ============================================================

async def update_category(
    category_id: str,
    update_data: CategoryUpdate,
    image_file: UploadFile = None,
) -> dict:
    """
    Update a category with optional image upload.
    """

    db = get_database()

    if not ObjectId.is_valid(category_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid category ID",
        )

    # Check if category exists
    existing_category = await db.categories.find_one(
        {
            "_id": ObjectId(category_id)
        }
    )

    if not existing_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    # Prepare update data
    update_dict = {}
    now = datetime.utcnow()

    if update_data.name is not None:
        # Check if name already exists (excluding current category)
        duplicate = await db.categories.find_one(
            {
                "name": {
                    "$regex": f"^{update_data.name}$",
                    "$options": "i",
                },
                "_id": {
                    "$ne": ObjectId(category_id)
                },
            }
        )

        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category with this name already exists",
            )

        update_dict["name"] = update_data.name.strip()
        
        # Update slug if name changed
        new_slug = generate_slug(update_data.name)
        
        # Check if slug already exists (excluding current category)
        slug_duplicate = await db.categories.find_one(
            {
                "slug": new_slug,
                "_id": {
                    "$ne": ObjectId(category_id)
                },
            }
        )

        if slug_duplicate:
            # Append a number to make it unique
            count = 1
            final_slug = f"{new_slug}-{count}"
            
            while await db.categories.find_one(
                {
                    "slug": final_slug,
                    "_id": {
                        "$ne": ObjectId(category_id)
                    },
                }
            ):
                count += 1
                final_slug = f"{new_slug}-{count}"
            
            new_slug = final_slug

        update_dict["slug"] = new_slug

    if update_data.description is not None:
        update_dict["description"] = update_data.description

    if update_data.is_active is not None:
        update_dict["is_active"] = update_data.is_active

    # Handle image upload
    if image_file:
        # Delete old image if it's not the default
        old_image = existing_category.get("image")
        if old_image and "via.placeholder.com" not in old_image:
            public_id = extract_public_id(old_image)
            if public_id:
                await delete_image(public_id)

        # Upload new image
        image_url = await upload_single_image(
            image_file,
            folder="ai-jewellery-shop/categories",
        )
        update_dict["image"] = image_url

    update_dict["updated_at"] = now

    # Update category
    await db.categories.update_one(
        {
            "_id": ObjectId(category_id)
        },
        {
            "$set": update_dict
        }
    )

    # Fetch updated category
    updated_category = await db.categories.find_one(
        {
            "_id": ObjectId(category_id)
        }
    )

    # Convert ObjectId
    updated_category["id"] = str(
        updated_category["_id"]
    )

    updated_category.pop(
        "_id",
        None,
    )

    return {
        "success": True,
        "message": "Category updated successfully",
        "category": updated_category,
    }



# ============================================================
# DELETE CATEGORY
# ============================================================

async def delete_category(
    category_id: str,
) -> dict:
    """
    Delete a category (soft delete by setting is_active=False).
    """

    db = get_database()

    if not ObjectId.is_valid(category_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid category ID",
        )

    # Check if category exists
    existing_category = await db.categories.find_one(
        {
            "_id": ObjectId(category_id)
        }
    )

    if not existing_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    # Check if category has products
    products_count = await db.products.count_documents(
        {
            "category": ObjectId(category_id),
            "is_active": True,
        }
    )

    if products_count > 0:
        # Soft delete (deactivate)
        await db.categories.update_one(
            {
                "_id": ObjectId(category_id)
            },
            {
                "$set": {
                    "is_active": False,
                    "updated_at": datetime.utcnow(),
                }
            }
        )

        return {
            "success": True,
            "message": f"Category deactivated as it has {products_count} associated products",
            "products_count": products_count,
        }

    # Delete image from Cloudinary if it's not the default
    old_image = existing_category.get("image")
    if old_image and "via.placeholder.com" not in old_image:
        public_id = extract_public_id(old_image)
        if public_id:
            await delete_image(public_id)

    # Hard delete (permanent)
    await db.categories.delete_one(
        {
            "_id": ObjectId(category_id)
        }
    )

    return {
        "success": True,
        "message": "Category deleted successfully",
    }


# ============================================================
# GET CATEGORY PRODUCTS
# ============================================================

async def get_category_products(
    category_id: str,
    page: int = 1,
    limit: int = 10,
) -> dict:
    """
    Get all products in a category.
    """

    db = get_database()

    if not ObjectId.is_valid(category_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid category ID",
        )

    # Check if category exists
    category = await db.categories.find_one(
        {
            "_id": ObjectId(category_id)
        }
    )

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    # Build query
    query = {
        "category": ObjectId(category_id),
        "is_active": True,
    }

    # Pagination
    skip = (page - 1) * limit

    # Get products
    products_cursor = db.products.find(
        query
    ).sort(
        "created_at",
        -1
    ).skip(
        skip
    ).limit(
        limit
    )

    products = await products_cursor.to_list(
        length=limit
    )

    # Convert ObjectId to string
    for product in products:
        product["id"] = str(
            product["_id"]
        )
        product.pop(
            "_id",
            None,
        )
        product["category"] = str(
            product["category"]
        )

    # Get total count
    total = await db.products.count_documents(
        query
    )

    return {
        "success": True,
        "category": {
            "id": str(category["_id"]),
            "name": category["name"],
            "slug": category["slug"],
        },
        "products": products,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit,
        },
    }