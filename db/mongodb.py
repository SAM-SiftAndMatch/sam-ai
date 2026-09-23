import logging

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.server_api import ServerApi

from core.config import settings

logger = logging.getLogger("sam_ai.db")
logging.basicConfig(level=logging.INFO)


class MongoDBManager:
    client: AsyncIOMotorClient | None = None
    db: AsyncIOMotorDatabase | None = None


db_manager = MongoDBManager()


async def connect_to_mongo():
    """Initialize connection to MongoDB server."""
    uri = settings.get_mongo_uri()

    # Mask password for secure logging
    masked_uri = uri
    if "@" in uri and "://" in uri:
        protocol, rest = uri.split("://", 1)
        _, host = rest.split("@", 1)
        masked_uri = f"{protocol}://***:***@{host}"

    logger.info("Connecting to MongoDB at: %s ...", masked_uri)

    try:
        # Use ServerApi version 1 for MongoDB Atlas compatibility
        server_api = ServerApi("1")
        db_manager.client = AsyncIOMotorClient(
            uri,
            server_api=server_api,
            serverSelectionTimeoutMS=5000,
        )
        db_manager.db = db_manager.client[settings.MONGO_DB_NAME]

        # Verify connection by pinging server
        await db_manager.client.admin.command("ping")
        logger.info(
            "Successfully connected to MongoDB server! (Database: '%s')",
            settings.MONGO_DB_NAME,
        )
    except Exception as e:
        logger.error("Failed to connect to MongoDB: %s", str(e))
        raise


async def close_mongo_connection():
    """Close MongoDB connection pool."""
    if db_manager.client:
        logger.info("Closing MongoDB connection...")
        db_manager.client.close()
        db_manager.client = None
        db_manager.db = None
        logger.info("MongoDB connection closed.")


def get_database() -> AsyncIOMotorDatabase:
    """FastAPI Dependency to retrieve active database instance."""
    if db_manager.db is None:
        raise RuntimeError("Database connection has not been initialized.")
    return db_manager.db


def get_mongo_client() -> AsyncIOMotorClient:
    """Retrieve active Mongo client."""
    if db_manager.client is None:
        raise RuntimeError("MongoDB client is not connected.")
    return db_manager.client


async def ping_mongo() -> bool:
    """Check whether MongoDB server is reachable."""
    if db_manager.client is None:
        return False
    try:
        await db_manager.client.admin.command("ping")
        return True
    except Exception:  # noqa: BLE001
        return False
