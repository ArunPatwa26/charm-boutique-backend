from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

load_dotenv()

class Database:
    """Database connection handler"""
    client: AsyncIOMotorClient = None
    db = None

db = Database()

async def connect_to_mongo():
    """Connect to MongoDB"""
    try:
        mongodb_uri = os.getenv("MONGODB_URI", "mongodb+srv://arunpatwa2605:Arun242526@cluster0.yjbna.mongodb.net/")
        db_name = os.getenv("DATABASE_NAME", "ai_jewellery_shop")
        
        # Create MongoDB client
        db.client = AsyncIOMotorClient(mongodb_uri)
        
        # Test connection
        await db.client.admin.command('ping')
        
        # Get database
        db.db = db.client[db_name]
        
        print(f"✅ Connected to MongoDB: {db_name}")
        print(f"📍 Database URL: {mongodb_uri}")
        return db.db
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {str(e)}")
        raise e

async def close_mongo_connection():
    """Close MongoDB connection"""
    if db.client:
        db.client.close()
        print("✅ MongoDB connection closed")

def get_database():
    """Get database instance"""
    return db.db