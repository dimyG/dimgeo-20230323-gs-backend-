from fastapi import FastAPI
from contextlib import asynccontextmanager
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import json
import asyncio
from logging.config import dictConfig
from config import LogConfig
from dotenv import load_dotenv
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware


# Note: It is recommended to call the dictConfig(...) function before the FastAPI initialization.
dictConfig(LogConfig().dict())
logger = logging.getLogger("gs_backend")

# Load environment variables from .env file
src_path = Path(".")
env_path = src_path / ".env"
load_dotenv(dotenv_path=env_path)

# Read environment variables
mongo_url = os.environ.get("MONGO_URL")
mongo_db_name = os.environ.get("MONGO_DB_NAME")
mongo_collection_name = os.environ.get("MONGO_COLLECTION_NAME")

# Log environment variables
logger.debug(f"mongo_url: {mongo_url}")
logger.debug(f"mongo_db: {mongo_db_name}")
logger.debug(f"mongo_collection_name: {mongo_collection_name}")

# Initialize the global variables to be used in the lifespan function.
# The lifespan function contains the startup and shutdown code. To access a variable both in startup and shutdown,
# it must be declared as a global variable. Another option is to add the variable as a property of the app object,
# but after this discussion on GitHub, it was decided to use global variables instead.
# https://github.com/tiangolo/fastapi/discussions/8239
mongodb = {}
mongodb_client: AsyncIOMotorClient = None


async def count_indexes(collection):
    count = 0
    async for _ in collection.list_indexes():
        count += 1
    return count


async def load_data_from_file(file_path="mongo_initial_data/garments.jl"):
    logger.info(f"Loading data from file {file_path}...")
    garments = []
    with open(file_path, "r") as f:
        for line in f:
            garment = json.loads(line)  # Convert JSON string to Python dict
            garments.append(garment)

    # Bulk insert the garments into the MongoDB collection
    await mongodb[mongo_collection_name].insert_many(garments)


async def initialize_indexes(db, collection_name):
    logger.debug("Initializing indexes...")
    index_count = await count_indexes(db[collection_name])
    logger.debug(f"index_count: {index_count}")

    # if garments collection has only the default index, create one on the product_title and product_description fields
    if index_count == 1:
        logger.info("Creating text index...")
        await db[collection_name].create_index(
            [("product_title", "text"), ("product_description", "text")]
        )


async def load_init_data(db, collection_name):
    # if mongo has no data, load data from the jl file
    if await db[collection_name].count_documents({}) == 0:
        await load_data_from_file()


async def connect_to_mongo():
    logger.debug("connecting to mongodb...")
    global mongodb
    global mongodb_client
    mongodb_client = AsyncIOMotorClient(mongo_url)
    mongodb = mongodb_client[mongo_db_name]


async def startup_db_sequence():
    await connect_to_mongo()
    await load_init_data(mongodb, mongo_collection_name)
    await initialize_indexes(mongodb, mongo_collection_name)


async def shutdown_db_client():
    # Close the MongoDB client
    logger.debug("shutting down db client...")
    mongodb_client.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await startup_db_sequence()
    yield
    await shutdown_db_client()


# Initialize the FastAPI app
app = FastAPI(lifespan=lifespan)

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Endpoint to search for garments
@app.get("/search")
async def search_garments(query: str, skip: int = 0, limit: int = 20):
    garments = []

    projection = {"position": 0, "product_imgs_src": 0, "image_urls": 0}

    try:
        # search based on text index
        cursor = mongodb[mongo_collection_name].find(
            # Search for garments that match the query based on the text index
            {"$text": {"$search": query}},
            # Use projection to fetch only required fields
            projection=projection
        )

        cursor.sort([("score", {"$meta": "textScore"})])  # Sort the results based on the text relevance score
        cursor.skip(skip).limit(limit)  # Skip and limit the results for pagination

        # search based on regex
        # cursor = mongodb[mongo_collection_name].find(
        #     # use a regex to search for garments that match the query
        #     {"$or": [
        #         {"product_title": {"$regex": query, "$options": "i"}},
        #         {"product_description": {"$regex": query, "$options": "i"}}
        #     ]},
        #     projection=projection  # Use projection to fetch only required fields
        # )

        async for garment in cursor:
            # ObjectId is not json serializable, convert it to a string before appending the garment
            garment["_id"] = str(garment["_id"])
            garments.append(garment)
            # logger.debug(f"garment: {garment}")

        logger.debug(f"{len(garments)} garments found.")

    except Exception as e:
        logger.error(f"Error while searching for garments: {e}")
        # if there is an error, just return an empty list
        garments = []

    # sleep for 2 seconds to simulate a slow search
    # await asyncio.sleep(2)

    return garments

