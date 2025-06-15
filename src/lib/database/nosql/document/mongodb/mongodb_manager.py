from typing import Optional

from pymongo import MongoClient

from src.lib.configuration import configuration

mongodb_uri = configuration.get_configuration("mongodb.uri")
mongodb_client = MongoClient(
    mongodb_uri if mongodb_uri else "mongodb://localhost:27017/"
)
