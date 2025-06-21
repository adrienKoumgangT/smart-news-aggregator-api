import json
from typing import Optional

from bson import ObjectId
from flask import Request
from flask_restx import Namespace, fields
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

    @staticmethod
    def to_model(name_space: Namespace):
        return name_space.model('ServerErrorLogModel', {
            'server_error_log_id': fields.String(required=False),
            'request_data': fields.Nested(RequestData.to_model(name_space)),
            'curl': fields.String(required=False),
            'exception_name': fields.String(required=False),
            'exception_message': fields.String(required=False),
        })

    @staticmethod
    def to_model_list(name_space: Namespace):
        return name_space.model('ServerErrorLogModelList', {
            'errors': fields.List(fields.Nested(ServerErrorLogModel.to_model(name_space)), ),
            'total': fields.Integer,
            'page': fields.Integer,
            'limit': fields.Integer,
            'pageCount': fields.Integer,
        })


    def save(self):
        api_logger = ApiLogger(f"[MONGODB] [SERVER ERROR LOG] [SAVE] : {self.to_json()}")

        server_error_log_collection = ServerErrorLogManager.collection()

        result = server_error_log_collection.insert_one(self.to_bson())

        self.server_error_log_id = result.inserted_id
        api_logger.print_log(f"Server Error Log ID: {self.server_error_log_id}")
        return self.server_error_log_id

    def delete(self):
        api_logger = ApiLogger(f"[MONGODB] [SERVER ERROR LOG] [DELETE] : {self.user_id}")
        result = ServerErrorLogManager.collection().delete_one(
            {"_id": ObjectId(self.server_error_log_id)}
        )
        api_logger.print_log(f"user deleted: {result.deleted_count > 0}")
        return result.deleted_count > 0

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

    @classmethod
    def get(cls, server_error_log_id):
        api_logger = ApiLogger(f"[MONGODB] [SERVER ERROR LOG] [GET] : {server_error_log_id}")

        result = ServerErrorLogManager.collection().find_one({'_id': ObjectId(server_error_log_id)})
        if result is None:
            api_logger.print_error("Errors does not exist")
            return None
        api_logger.print_log()

        return cls(**result)

    @staticmethod
    def get_list_count():
        api_logger = ApiLogger(f"[MONGODB] [SERVER ERROR LOG COUNT] [ALL] ")
        total = ServerErrorLogManager.collection().count_documents({})
        api_logger.print_log()
        return total if (total and total > 0) else 0

    @classmethod
    def get_list(cls, page: int = 1, limit: int = 10):
        api_logger = ApiLogger(f"[MONGODB] [SERVER ERROR LOG] [LIST] : page={page} and limit={limit}")
        sort = list({'created_at': -1}.items())
        results = ServerErrorLogManager.collection().find(
            filter={},
            sort=sort,
            skip=limit * (page - 1),
            limit=limit
        )

        api_logger.print_log()

        if results:
            return [cls(**result) for result in results]
        return []



