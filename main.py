from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import json
from logging.config import dictConfig
from config import LogConfig
from dotenv import load_dotenv
from pathlib import Path


# Note: It is recommended to call the dictConfig(...) function before the FastAPI initialization.
dictConfig(LogConfig().dict())
logger = logging.getLogger("gs_backend")

# Load environment variables from .env file
src_path = Path(".")
env_path = src_path / ".env"
load_dotenv(dotenv_path=env_path)

# Read environment variables
mongo_url = os.environ.get("MONGO_URL")
mongo_db = os.environ.get("MONGO_DB")
mongo_collection_name = os.environ.get("MONGO_COLLECTION_NAME")

logger.debug(f"mongo_url: {mongo_url}")
logger.debug(f"mongo_db: {mongo_db}")
logger.debug(f"mongo_collection_name: {mongo_collection_name}")

# Initialize the FastAPI app
app = FastAPI()


# Register a startup event handler function
@app.on_event("startup")
async def startup_db_client():
    # Initialize the MongoDB client
    app.mongodb_client = AsyncIOMotorClient(mongo_url)
    app.mongodb = app.mongodb_client[mongo_db]

    # if mongo has no data, load data from a jl file
    if await app.mongodb[mongo_collection_name].count_documents({}) == 0:
        logger.info("Loading data from file...")
        garments = []
        with open("mongo_initial_data/garments.jl", "r") as f:
            for line in f:
                garment = json.loads(line)  # Convert JSON string to Python dict
                garments.append(garment)

        # Bulk insert the garments into the MongoDB collection
        await app.mongodb[mongo_collection_name].insert_many(garments)


# Register a shutdown event handler function
@app.on_event("shutdown")
async def shutdown_db_client():
    # Close the MongoDB client
    await app.mongodb_client.close()


# Endpoint to search for garments
@app.get("/search/{query}")
async def search_garments(query: str):
    garments = []

    cursor = app.mongodb[mongo_collection_name].find(
        {"product_title": {"$regex": f".*{query}.*", "$options": "i"}}
    )

    async for garment in cursor:
        # Convert the ObjectId to a string before appending the garment
        garment["_id"] = str(garment["_id"])
        garments.append(garment)
        logger.debug(f"garment: {garment['product_title']}")

    logger.debug(f"returning {len(garments)} garments...")

    return garments[:10]

