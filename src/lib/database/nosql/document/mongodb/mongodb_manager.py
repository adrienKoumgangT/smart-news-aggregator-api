from typing import Optional

from pymongo import MongoClient

from src.lib.configuration import configuration


class MongoDBManager:

    @staticmethod
    def database_name() -> str:
        return configuration.get_configuration("mongodb.database")

    @staticmethod
    def collection_name(name):
        return configuration.get_configuration(f"mongodb.collection.{name}")



mongodb_uri = configuration.get_configuration("mongodb.uri")
mongodb_client = MongoClient(
    mongodb_uri if mongodb_uri else "mongodb://localhost:27017/"
)
