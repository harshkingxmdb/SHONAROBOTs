from motor.motor_asyncio import AsyncIOMotorClient
from config import DB_URL

MONGO_URL = DB_URL

client = AsyncIOMotorClient(MONGO_URL)
db = client["AloneX"]

antiedit_db = db["antiedit"]
