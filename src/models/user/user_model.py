from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from flask_restx import fields, Namespace
from pydantic import BaseModel, Field, field_serializer
from pymongo.errors import DuplicateKeyError

from src.lib.authentication.password import hash_password
from src.lib.configuration import configuration
from src.lib.database.nosql.document.mongodb.base import MongoDBBaseModel
from src.lib.database.nosql.document.mongodb.mongodb_manager import MongoDBManagerInstance
from src.lib.database.nosql.document.mongodb.objectid import PydanticObjectId
from src.lib.log.api_logger import ApiLogger
from src.models import DataBaseModel

account_status = {
    "active": "The user account is active and has full access",
    "inactive": "The account exists but is not currently in use",
    "pending": "The user has registered but not yet verified",
    "suspended": "temporarily disabled by admin or due to policy",
    "banned": "Permanently blocked due to violations",
    "deleted": "Account has been marked for or fully removed",
    "archived": "Old or deactivated account, retained for reference"
}

role = {
    "admin": "Administrator",
    "user": "User",
    "guest": "Limited access user"
}


class UserManager:
    database_name = configuration.get_configuration("mongodb.database")
    collection_name = configuration.get_configuration("mongodb.collection.users")

    @staticmethod
    def init_database():
        users_collection = MongoDBManagerInstance.get_instance().get_collection(
            db_name=UserManager.database_name,
            collection_name=UserManager.collection_name
        )
        users_collection.create_index([("email", 1)], unique=True)


class PasswordHistory(BaseModel):
    password: str
    created_at: datetime


class Account(BaseModel):
    status: str
    role: str

    @staticmethod
    def to_model(name_space: Namespace):
        return name_space.model('AccountModel', {
            'status': fields.String(required=True),
            'role': fields.String(required=True),
        })


class Address(BaseModel):
    street: str
    city: str
    state: str
    zip: str
    country: str

    @staticmethod
    def to_model(name_space: Namespace):
        return name_space.model('AddressModel', {
            'street': fields.String(required=True),
            'city': fields.String(required=True),
            'state': fields.String(required=True),
            'zip': fields.String(required=True),
            'country': fields.String(required=True),
        })


class User(MongoDBBaseModel):
    user_id: Optional[PydanticObjectId] = Field(None, alias="_id")

    firstname: str
    lastname: str
    email: str
    password: str
    account: Account
    address: Optional[Address] = None
    password_history: list[PasswordHistory] = []

    preferences: list[str] = []

    @field_serializer("user_id")
    def serialize_id(self, id_value: PydanticObjectId, _info):
        return str(id_value) if id_value else None


    def save(self):
        api_logger = ApiLogger(f"[MONGODB] [USER] [SAVE] : {self.to_json()}")

        users_collection = MongoDBManagerInstance.get_instance().get_collection(
            db_name=UserManager.database_name,
            collection_name=UserManager.collection_name
        )
        try:
            result = users_collection.insert_one(self.to_bson())
        except DuplicateKeyError:
            api_logger.print_error("User already exists")
            return None
        self.user_id = result.inserted_id
        api_logger.print_log(f"User ID: {self.user_id}")
        return self.user_id

    def update_user(self):
        api_logger = ApiLogger(f"[MONGODB] [USER] [UPDATE] : {self.user_id}")
        users_collection = MongoDBManagerInstance.get_instance().get_collection(
            db_name=UserManager.database_name,
            collection_name=UserManager.collection_name
        )
        result = users_collection.update_one(
            {"_id": ObjectId(self.user_id)},
            {
                "$set": {
                    "firstname": self.firstname,
                    "lastname": self.lastname,
                    "address": self.address,
                    "preferences": self.preferences,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        api_logger.print_log(f"user updated: {result.modified_count > 0}")
        return result.modified_count > 0

    @classmethod
    def update_password(cls, user_id: str, password: str):
        api_logger = ApiLogger(f"[MONGODB] [USER] [UPDATE] [PASSWORD] : {user_id}")
        users_collection = MongoDBManagerInstance.get_instance().get_collection(
            db_name=UserManager.database_name,
            collection_name=UserManager.collection_name
        )
        hashed_password = hash_password(password)

        user = cls.get(user_id=user_id)
        if not user:
            api_logger.print_error("User does not exist")
            return {"error": "User not found"}
        for old_password in user.password_history:
            if old_password.password == hashed_password:
                api_logger.print_error("Password already used")
                return {"error": "You cannot reuse an old password"}

        current_datetime = datetime.now(timezone.utc)

        password_history = PasswordHistory(password=hashed_password, created_at=current_datetime)
        result = users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "password": hashed_password,
                    "updated_at": current_datetime
                },
                "$push": {
                    "password_history": {
                        "$each": [password_history.model_dump(by_alias=True, exclude_none=True)],
                        "$slice": -5  # keep only the last 5
                    }
                }
            }
        )

        api_logger.print_log(f"password updated: {result.modified_count > 0}")
        return result.modified_count > 0

    @classmethod
    def get(cls, user_id: str):
        api_logger = ApiLogger(f"[MONGODB] [USER] [GET] : {user_id}")
        users_collection = MongoDBManagerInstance.get_instance().get_collection(
            db_name=UserManager.database_name,
            collection_name=UserManager.collection_name
        )
        user = users_collection.find_one({"_id": ObjectId(user_id)})
        if user is None:
            api_logger.print_error("User does not exist")
            return None
        api_logger.print_log()
        return cls(**user)

    @classmethod
    def get_by_email(cls, email: str):
        api_logger = ApiLogger(f"[MONGODB] [USER] [GET] [BY EMAIL] : {email}")
        users_collection = MongoDBManagerInstance.get_instance().get_collection(
            db_name=UserManager.database_name,
            collection_name=UserManager.collection_name
        )
        user = users_collection.find_one({"email": email})
        if user is None:
            api_logger.print_error("User does not exist")
            return None
        api_logger.print_log()
        return cls(**user)


class UserMe(DataBaseModel):
    user_id: str
    firstname: str
    lastname: str
    email: str
    account: Account
    address: Optional[Address] = None

    @classmethod
    def from_user(cls, user: User):
        return cls(
            user_id=str(user.user_id),
            firstname=user.firstname,
            lastname=user.lastname,
            email=user.email,
            account=user.account,
            address=user.address
        )

    @staticmethod
    def to_model(name_space: Namespace):
        return name_space.model('UserMeModel', {
            'user_id': fields.String(required=True),
            'firstname': fields.String(required=True),
            'lastname': fields.String(required=True),
            'email': fields.String(required=True),
            'account': fields.Nested(Account.to_model(name_space)),
            'address': fields.Nested(Address.to_model(name_space)),
        })

