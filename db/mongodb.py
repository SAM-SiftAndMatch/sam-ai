import os
import logging
from urllib.parse import quote_plus
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.server_api import ServerApi
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("sam_ai.db")
logging.basicConfig(level=logging.INFO)

# Environment variables
MONGO_URI = os.getenv("MONGO_URI")
MONGO_HOST = os.getenv("MONGO_HOST", "localhost")
MONGO_PORT = os.getenv("MONGO_PORT", "27017")
MONGO_USERNAME = os.getenv("MONGO_USERNAME")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "sam_ai_db")
MONGO_AUTH_SOURCE = os.getenv("MONGO_AUTH_SOURCE", "admin")
MONGO_IS_SRV = os.getenv("MONGO_IS_SRV", "False").lower() in ("true", "1", "yes")


def get_mongo_uri() -> str:
    """Resolve MongoDB connection string from environment."""
    if MONGO_URI:
        return MONGO_URI

    # Construct URI from individual variables
    auth_part = ""
    if MONGO_USERNAME and MONGO_PASSWORD:
        encoded_user = quote_plus(MONGO_USERNAME)
        encoded_pass = quote_plus(MONGO_PASSWORD)
        auth_part = f"{encoded_user}:{encoded_pass}@"

    # Auto-detect SRV (e.g. MongoDB Atlas)
    is_srv = MONGO_IS_SRV or (MONGO_HOST and "mongodb.net" in MONGO_HOST)

    if is_srv:
        return f"mongodb+srv://{auth_part}{MONGO_HOST}/{MONGO_DB_NAME}?retryWrites=true&w=majority"
    else:
        auth_source_param = f"?authSource={MONGO_AUTH_SOURCE}" if auth_part else ""
        return f"mongodb://{auth_part}{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB_NAME}{auth_source_param}"


class MongoDBManager:
    client: AsyncIOMotorClient | None = None
    db: AsyncIOMotorDatabase | None = None


db_manager = MongoDBManager()


async def connect_to_mongo():
    """Initialize connection to MongoDB server."""
    uri = get_mongo_uri()
    # Mask password for secure logging
    masked_uri = uri
    if "@" in uri and "://" in uri:
        protocol, rest = uri.split("://", 1)
        creds, host = rest.split("@", 1)
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
        db_manager.db = db_manager.client[MONGO_DB_NAME]

        # Verify connection by pinging server
        await db_manager.client.admin.command("ping")
        logger.info("Successfully connected to MongoDB server! (Database: '%s')", MONGO_DB_NAME)
    except Exception as e:
        logger.error("Failed to connect to MongoDB: %s", str(e))
        raise e


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
    except Exception:
        return False
