import json
from typing import Optional

from bson import ObjectId
from flask import Request
from flask_restx import Namespace, fields
from pydantic import Field, field_serializer

from src.lib.database.nosql.document.mongodb.base import MongoDBBaseModel
from src.lib.database.nosql.document.mongodb.objectid import PydanticObjectId
from src.lib.utility.utils_server import RequestData
from src.models.user.auth_model import UserToken


class ServerErrorLogModel(MongoDBBaseModel):
    server_error_log_id: Optional[PydanticObjectId] = Field(None, alias="_id")

    request_data: Optional[RequestData]

    curl: Optional[str]

    exception_name: Optional[str]
    exception_message: Optional[str]

    @field_serializer("server_error_log_id")
    def serialize_id(self, id_value: PydanticObjectId, _info):
        return str(id_value) if id_value else None

    @classmethod
    def _name(cls) -> str:
        return "server_error_log"

    @classmethod
    def _id_name(cls) -> str:
        return "server_error_log_id"

    def _data_id(self) -> ObjectId:
        return self.server_error_log_id

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


    def save(self, user_token: UserToken):
        self.server_error_log_id = super().save(user_token)
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


