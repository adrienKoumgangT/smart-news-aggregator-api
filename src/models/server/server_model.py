import json
from typing import Optional

from flask import Request
from pydantic import Field, field_serializer

from src.lib.configuration import configuration
from src.lib.database.nosql.document.mongodb.base import MongoDBBaseModel
from src.lib.database.nosql.document.mongodb.mongodb_manager import mongodb_client
from src.lib.database.nosql.document.mongodb.objectid import PydanticObjectId
from src.lib.log.api_logger import ApiLogger
from src.lib.utility.utils_server import RequestData


class ServerErrorLogManager:
    database_name = configuration.get_configuration("mongodb.database")
    collection_name = configuration.get_configuration("mongodb.collection.server_error_log")

    @staticmethod
    def collection():
        """
        return MongoDBManagerInstance.get_instance().get_collection(
            db_name=ServerErrorLogManager.database_name,
            collection_name=ServerErrorLogManager.collection_name
        )
        """
        return mongodb_client[ServerErrorLogManager.database_name][ServerErrorLogManager.collection_name]


class ServerErrorLogModel(MongoDBBaseModel):
    server_error_log_id: Optional[PydanticObjectId] = Field(None, alias="_id")

    request_data: Optional[RequestData]

    curl: Optional[str]

    exception_name: Optional[str]
    exception_message: Optional[str]

    @field_serializer("server_error_log_id")
    def serialize_id(self, id_value: PydanticObjectId, _info):
        return str(id_value) if id_value else None


    def save(self):
        api_logger = ApiLogger(f"[MONGODB] [SERVER ERROR LOG] [SAVE] : {self.to_json()}")

        server_error_log_collection = ServerErrorLogManager.collection()

        result = server_error_log_collection.insert_one(self.to_bson())

        self.server_error_log_id = result.inserted_id
        api_logger.print_log(f"Server Error Log ID: {self.server_error_log_id}")
        return self.server_error_log_id


    @classmethod
    def from_request(cls, request: Request, exception_name:str, exception_message:str):
        request_data = RequestData.from_request(request=request)

        headers = [f"-H '{key}: {value}'" for key, value in request.headers if key.lower() != "content-length"]

        if request.is_json:
            data = request.get_json()
            body = f"-H 'Content-Type: application/json' -d '{json.dumps(data)}'"
        elif request.form:
            form_data = "&".join([f"{k}={v}" for k, v in request.form.items()])
            body = f"-d '{form_data}'"
        else:
            body = ""

        curl = f"curl -X {request_data.method} {' '.join(headers)} {body} '{request_data.url}'"

        return cls(
            _id=None,
            request_data=request_data,
            curl=curl,
            exception_name=exception_name,
            exception_message=exception_message
        )



