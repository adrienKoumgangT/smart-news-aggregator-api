from typing import Optional

from pymongo import MongoClient

from src.lib.configuration import configuration
from src.lib.configuration.configuration import config


class MongoDBManager:

    @staticmethod
    def database_name() -> str:
        return config.mongo.database

    @staticmethod
    def collection_name(name):
        return configuration.get_env_var(f"mongodb.collection.{name}")


mongodb_client = MongoClient(
    config.mongo.uri if config.mongo.uri else "mongodb://localhost:27017/"
)
