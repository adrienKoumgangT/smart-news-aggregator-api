from typing import Optional

from bson import ObjectId
from flask import Request
from pydantic import Field, field_serializer

from src.lib.database.nosql.document.mongodb.base import MongoDBBaseModel
from src.lib.database.nosql.document.mongodb.mongodb_monitoring_middleware import MONGO_QUERY_TIME
from src.lib.database.nosql.document.mongodb.objectid import PydanticObjectId
from src.lib.log.api_logger import ApiLogger
from src.lib.utility.utils_server import RequestData
from src.models.user.auth_model import UserToken


class AuthEventLogModel(MongoDBBaseModel):
    auth_event_log_id: Optional[PydanticObjectId] = Field(None, alias="_id")

    request_data: Optional[RequestData]

    event: Optional[str]
    is_success: Optional[bool]
    message: Optional[str]

    @field_serializer("auth_event_log_id")
    def serialize_id(self, id_value: PydanticObjectId, _info):
        return str(id_value) if id_value else None

    @classmethod
    def _name(cls) -> str:
        return "auth_event_log"

    @classmethod
    def _id_name(cls) -> str:
        return "auth_event_log_id"

    def _data_id(self) -> ObjectId:
        return self.auth_event_log_id

    def save(self, user_token: UserToken = None):
        api_logger = ApiLogger(f"[MONGODB] [AUTH EVENT LOG] [SAVE]: {self.to_json()}")

        with MONGO_QUERY_TIME.time():
            result = self.collection().insert_one(self.to_bson())

        self.auth_event_log_id = result.inserted_id
        api_logger.print_log(f"Auth Event Log ID: {self.auth_event_log_id}")
        return self.auth_event_log_id


    @classmethod
    def from_request(cls, request: Request, event:str, is_success:bool=True, message:str=''):
        request_data = RequestData.from_request(request=request)

        return cls(
            _id=None,
            request_data=request_data,
            event=event,
            is_success=is_success,
            message=message
        )
