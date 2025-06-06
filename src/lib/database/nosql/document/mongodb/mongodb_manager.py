from typing import Optional

from pymongo import MongoClient

from src.lib.configuration import configuration


class MongoDBManager:

    def __init__(self, mongodb_uri: str = "mongodb://localhost:27017/"):
        self.mongodb_uri = mongodb_uri
        self.client = MongoClient(self.mongodb_uri)

    def get_database(self, db_name: str):
        return self.client[db_name]

    def get_collection(self, db_name: str, collection_name: str):
        return self.client[db_name][collection_name]

    def close_connection(self):
        self.client.close()

    def __del__(self):
        self.close_connection()

    def list_databases(self):
        return self.client.list_database_names()

    def list_collections(self, db_name: str):
        return self.client[db_name].list_collection_names()


class MongoDBManagerInstance:
    instance: Optional[MongoDBManager] = None

    @staticmethod
    def init_database():
        if MongoDBManagerInstance.instance is None:
            MongoDBManagerInstance.instance = MongoDBManager(
                mongodb_uri=configuration.get_configuration("mongodb.uri")
            )

    @staticmethod
    def get_instance() -> MongoDBManager:
        if MongoDBManagerInstance.instance is None:
            MongoDBManagerInstance.init_database()
        return MongoDBManagerInstance.instance


