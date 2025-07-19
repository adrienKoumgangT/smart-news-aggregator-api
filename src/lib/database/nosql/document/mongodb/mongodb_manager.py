from typing import Optional

from pymongo import MongoClient

from src.lib.configuration import configuration
from src.lib.configuration.configuration import config
from src.lib.log.api_logger import ApiLogger


class MongoDBManager:

    @staticmethod
    def database_name() -> str:
        return config.mongo.database

    @staticmethod
    def collection_name(name):
        return configuration.get_env_var(f"mongodb.collection.{name}")


mongo_uri = config.mongo.uri if config.mongo.uri else "mongodb://localhost:27017/"
api_logger = ApiLogger(f"[MONGODB] [CONNECTION] : uri={mongo_uri}")
mongodb_client = MongoClient(mongo_uri)
mongodb_client.server_info()
api_logger.print_log()

