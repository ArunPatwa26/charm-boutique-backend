from datetime import datetime
from typing import Optional, List

from bson import ObjectId
from fastapi import HTTPException, status, UploadFile

from app.config.database import get_database
from app.config.cloudinary import delete_image, extract_public_id
from app.middleware.upload import upload_multiple_images_middleware, upload_single_image
from app.models.product import ProductCreate, ProductUpdate


# ============================================================
# CREATE PRODUCT
# ============================================================

async def create_product(
    product_data: ProductCreate,
    images: List[UploadFile],
) -> dict:
    """
    Create a new product with multiple images.
    """
    db = get_database()

    # Validate category
    category = await db.categories.find_one(
        {
            "_id": ObjectId(product_data.category),
            "is_active": True,
        }
    )

    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category not found or inactive",
        )

    # Upload images to Cloudinary
    uploaded_images = await upload_multiple_images_middleware(
        images,
        folder="ai-jewellery-shop/products",
    )

    if not uploaded_images:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one image is required",
        )

    # Create product document
    now = datetime.utcnow()

    product_dict = product_data.model_dump()

    product_dict["category"] = ObjectId(
        product_data.category
    )
    product_dict["images"] = uploaded_images
    product_dict["main_image"] = uploaded_images[0]
    product_dict["average_rating"] = 0
    product_dict["num_reviews"] = 0
    product_dict["reviews"] = []
    product_dict["is_active"] = True
    product_dict["created_at"] = now
    product_dict["updated_at"] = now

    # Insert into MongoDB
    result = await db.products.insert_one(
        product_dict
    )

    # Fetch created product
    created_product = await db.products.find_one(
        {
            "_id": result.inserted_id
        }
    )

    if not created_product:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create product",
        )

    # Convert ObjectId
    created_product["id"] = str(
        created_product["_id"]
    )

    created_product.pop(
        "_id",
        None,
    )

    created_product["category"] = str(
        created_product["category"]
    )

    return {
        "success": True,
        "message": "Product created successfully",
        "product": created_product,
    }


# ============================================================
# GET ALL PRODUCTS
# ============================================================

async def get_products(
    page: int = 1,
    limit: int = 10,
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    material: Optional[str] = None,
    gemstone: Optional[str] = None,
    sort_by: Optional[str] = None,
    is_featured: Optional[bool] = None,
    is_ai_recommended: Optional[bool] = None,
    search: Optional[str] = None,
) -> dict:
    """
    Get all products with pagination and filters.
    """
    db = get_database()

    # Build query
    query = {"is_active": True}

    if category:
        query["category"] = ObjectId(category)

    if material:
        query["material"] = material

    if gemstone:
        query["gemstone"] = gemstone

    if is_featured is not None:
        query["is_featured"] = is_featured

    if is_ai_recommended is not None:
        query["is_ai_recommended"] = is_ai_recommended

    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
            {"tags": {"$regex": search, "$options": "i"}},
        ]

    # Price range filter
    price_query = {}
    if min_price is not None:
        price_query["$gte"] = min_price
    if max_price is not None:
        price_query["$lte"] = max_price
    if price_query:
        query["price"] = price_query

    # Sorting
    sort_options = {
        "price_asc": ("price", 1),
        "price_desc": ("price", -1),
        "rating": ("average_rating", -1),
        "newest": ("created_at", -1),
        "oldest": ("created_at", 1),
        "name_asc": ("name", 1),
        "name_desc": ("name", -1),
    }

    sort_key = sort_by if sort_by in sort_options else "newest"
    sort_field, sort_order = sort_options[sort_key]

    # Pagination
    skip = (page - 1) * limit

    # Get products
    products_cursor = db.products.find(
        query
    ).sort(
        sort_field,
        sort_order
    ).skip(
        skip
    ).limit(
        limit
    )

    products = await products_cursor.to_list(
        length=limit
    )

    # Convert ObjectId to string and get category names
    for product in products:
        product["id"] = str(
            product["_id"]
        )
        product.pop(
            "_id",
            None,
        )
        
        # Get category name
        if product.get("category"):
            category_obj = await db.categories.find_one(
                {"_id": product["category"]}
            )
            product["category_name"] = category_obj.get("name", "Uncategorized") if category_obj else "Uncategorized"
            product["category"] = str(
                product["category"]
            )

    # Get total count
    total = await db.products.count_documents(
        query
    )

    return {
        "success": True,
        "products": products,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit,
        },
    }


# ============================================================
# ADMIN: GET ALL PRODUCTS (INCLUDING INACTIVE)
# ============================================================

async def admin_get_all_products(
    page: int = 1,
    limit: int = 10,
    search: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
) -> dict:
    """
    Get all products for admin (includes inactive products).
    """
    db = get_database()

    # Build query
    query = {}

    if category:
        query["category"] = ObjectId(category)

    if status == "active":
        query["is_active"] = True
    elif status == "inactive":
        query["is_active"] = False

    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
            {"tags": {"$regex": search, "$options": "i"}},
        ]

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

    products = await products_cursor.to_list(length=limit)

    # Convert ObjectId to string and get category names
    for product in products:
        product["id"] = str(product["_id"])
        product.pop("_id", None)
        
        # Get category name
        if product.get("category"):
            category_obj = await db.categories.find_one(
                {"_id": product["category"]}
            )
            product["category_name"] = category_obj.get("name", "Uncategorized") if category_obj else "Uncategorized"
            product["category"] = str(product["category"])

    # Get total count
    total = await db.products.count_documents(query)

    return {
        "success": True,
        "products": products,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit,
        },
    }


# ============================================================
# GET PRODUCT BY ID
# ============================================================

async def get_product_by_id(
    product_id: str,
) -> dict:
    """
    Get a product by its ID.
    """
    db = get_database()

    if not ObjectId.is_valid(product_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID",
        )

    product = await db.products.find_one(
        {
            "_id": ObjectId(product_id),
            "is_active": True,
        }
    )

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    # Convert ObjectId
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

    return {
        "success": True,
        "product": product,
    }


# ============================================================
# UPDATE PRODUCT - FIXED VERSION
# ============================================================

async def update_product(
    product_id: str,
    update_data: ProductUpdate,
    new_images: List[UploadFile] = None,
    remove_images: List[str] = None,
) -> dict:
    """
    Update a product with optional image management.
    """
    db = get_database()

    if not ObjectId.is_valid(product_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID",
        )

    # Check if product exists
    existing_product = await db.products.find_one(
        {
            "_id": ObjectId(product_id)
        }
    )

    if not existing_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    # Prepare update data
    update_dict = {}
    now = datetime.utcnow()

    # Update basic fields
    fields_to_update = [
        "name", "description", "price", "discount_price",
        "material", "gemstone", "weight", "dimensions",
        "stock", "is_featured", "is_ai_recommended",
        "tags", "is_active",
    ]

    for field in fields_to_update:
        value = getattr(update_data, field)
        if value is not None:
            update_dict[field] = value

    # Update category if provided
    if update_data.category is not None:
        try:
            category = await db.categories.find_one(
                {
                    "_id": ObjectId(update_data.category),
                    "is_active": True,
                }
            )

            if not category:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Category not found or inactive",
                )

            update_dict["category"] = ObjectId(update_data.category)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid category ID format: {str(e)}",
            )

    # ============================================================
    # IMAGE MANAGEMENT
    # ============================================================
    
    current_images = existing_product.get("images", [])
    current_main_image = existing_product.get("main_image")

    print(f"📸 Current images count: {len(current_images)}")
    print(f"🗑️ Images to remove: {remove_images}")
    print(f"📤 New images count: {len(new_images) if new_images else 0}")

    # STEP 1: Remove specified images
    if remove_images:
        # Ensure remove_images is a list
        if isinstance(remove_images, str):
            remove_images = [remove_images]
        
        for image_url in remove_images:
            if image_url in current_images:
                # Delete from Cloudinary
                public_id = extract_public_id(image_url)
                if public_id:
                    try:
                        await delete_image(public_id)
                        print(f"✅ Deleted image from Cloudinary: {public_id}")
                    except Exception as e:
                        print(f"⚠️ Failed to delete image: {str(e)}")
                # Remove from the list
                current_images.remove(image_url)
                print(f"🗑️ Removed image from product")

    # STEP 2: Upload and add new images
    if new_images:
        # Ensure new_images is a list
        if not isinstance(new_images, list):
            new_images = [new_images]
        
        # Filter out None values
        valid_new_images = [img for img in new_images if img is not None]
        
        if valid_new_images:
            try:
                uploaded_images = await upload_multiple_images_middleware(
                    valid_new_images,
                    folder="ai-jewellery-shop/products",
                )
                if uploaded_images:
                    current_images.extend(uploaded_images)
                    print(f"✅ Added {len(uploaded_images)} new images")
            except Exception as e:
                print(f"❌ Failed to upload images: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to upload images: {str(e)}",
                )

    # STEP 3: Update the images list
    if current_images:
        update_dict["images"] = current_images
        
        # Check if the current main image was removed
        if current_main_image and current_main_image not in current_images:
            update_dict["main_image"] = current_images[0]
            print(f"🖼️ Updated main image to first image")
        elif not current_main_image and current_images:
            update_dict["main_image"] = current_images[0]
            print(f"🖼️ Set main image to first image")
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product must have at least one image",
        )

    update_dict["updated_at"] = now

    # Update product
    result = await db.products.update_one(
        {
            "_id": ObjectId(product_id)
        },
        {
            "$set": update_dict
        }
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found during update",
        )

    # Fetch updated product
    updated_product = await db.products.find_one(
        {
            "_id": ObjectId(product_id)
        }
    )

    # Convert ObjectId to string
    updated_product["id"] = str(updated_product["_id"])
    updated_product.pop("_id", None)
    updated_product["category"] = str(updated_product["category"])

    print(f"✅ Product updated. Total images: {len(updated_product.get('images', []))}")

    return {
        "success": True,
        "message": "Product updated successfully",
        "product": updated_product,
    }


# ============================================================
# DELETE PRODUCT
# ============================================================

async def delete_product(
    product_id: str,
) -> dict:
    """
    Delete a product and its images from Cloudinary.
    """
    db = get_database()

    if not ObjectId.is_valid(product_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID",
        )

    # Check if product exists
    existing_product = await db.products.find_one(
        {
            "_id": ObjectId(product_id)
        }
    )

    if not existing_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    # Delete all images from Cloudinary
    for image_url in existing_product.get("images", []):
        public_id = extract_public_id(image_url)
        if public_id:
            try:
                await delete_image(public_id)
                print(f"✅ Deleted image: {public_id}")
            except Exception as e:
                print(f"⚠️ Failed to delete image: {str(e)}")

    # Delete product
    await db.products.delete_one(
        {
            "_id": ObjectId(product_id)
        }
    )

    return {
        "success": True,
        "message": "Product deleted successfully",
    }