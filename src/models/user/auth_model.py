from typing import Optional

from flask import Request
from flask_restx import Namespace, fields
from pydantic import Field, field_serializer

from src.lib.configuration import configuration
from src.lib.database.nosql.document.mongodb.base import MongoDBBaseModel
from src.lib.database.nosql.document.mongodb.mongodb_manager import mongodb_client
from src.lib.database.nosql.document.mongodb.objectid import PydanticObjectId
from src.lib.log.api_logger import ApiLogger
from src.lib.utility.utils_server import RequestData
from src.models import DataBaseModel
from src.models.user.user_model import User


class RegisterModel(DataBaseModel):
    firstname: str
    lastname: str
    email: str
    # phone: Optional[str] = None
    password: str
    confirm_password: str

    @staticmethod
    def to_model(name_space: Namespace):
        return name_space.model('RegisterModel', {
            'firstname': fields.String(required=True),
            'lastname': fields.String(required=True),
            'email': fields.String(required=True),
            # 'phone': fields.String(required=False),
            'password': fields.String(required=True),
            'confirm_password': fields.String(required=True),
        })


class LoginModel(DataBaseModel):
    email: str
    password: str

    @staticmethod
    def to_model(name_space: Namespace):
        return name_space.model('LoginModel', {
            'email': fields.String(required=True),
            'password': fields.String(required=True),
        })


class ChangePasswordModel(DataBaseModel):
    password: str
    old_password: str

    @staticmethod
    def to_model(name_space: Namespace):
        return name_space.model('ChangePasswordModel', {
            'password': fields.String(required=True),
            'old_password': fields.String(required=True),
        })



class UserToken(DataBaseModel):
    user_id: str
    firstname: str
    lastname: str
    email: str
    status: str
    role: str

    @classmethod
    def from_user(cls, user: User):
        return cls(
            user_id=str(user.user_id),
            firstname=user.firstname,
            lastname=user.lastname,
            email=user.email,
            status=user.account.status,
            role=user.account.role
        )

    @staticmethod
    def to_model(name_space: Namespace):
        return name_space.model('UserTokenModel', {
            'user_id': fields.String(required=True),
            'firstname': fields.String(required=True),
            'lastname': fields.String(required=True),
            'email': fields.String(required=True),
            'status': fields.String(required=True),
            'role': fields.String(required=True),
        })

class AuthEventLogManager:
    database_name = configuration.get_configuration("mongodb.database")
    collection_name = configuration.get_configuration("mongodb.collection.auth_event_log")

    @staticmethod
    def collection():
        """
        return MongoDBManagerInstance.get_instance().get_collection(
            db_name=AuthEventLogManager.database_name,
            collection_name=AuthEventLogManager.collection_name
        )
        """
        return mongodb_client[AuthEventLogManager.database_name][AuthEventLogManager.collection_name]


class AuthEventLogModel(MongoDBBaseModel):
    auth_event_log_id: Optional[PydanticObjectId] = Field(None, alias="_id")

    request_data: Optional[RequestData]

    event: Optional[str]
    is_success: Optional[bool]
    message: Optional[str]

    @field_serializer("auth_event_log_id")
    def serialize_id(self, id_value: PydanticObjectId, _info):
        return str(id_value) if id_value else None

    def save(self):
        api_logger = ApiLogger(f"[MONGODB] [AUTH EVENT LOG] [SAVE]: {self.to_json()}")

        server_error_log_collection = AuthEventLogManager.collection()

        result = server_error_log_collection.insert_one(self.to_bson())

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



