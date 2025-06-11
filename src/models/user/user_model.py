from __future__ import annotations
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
from src.lib.database.nosql.keyvalue.redis.redis_manager import RedisManagerInstance
from src.lib.log.api_logger import ApiLogger
from src.models import DataBaseModel, DataManagerBase

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


class UserManager(DataManagerBase):
    database_name = configuration.get_configuration("mongodb.database")
    collection_name = configuration.get_configuration("mongodb.collection.users")

    @staticmethod
    def collection():
        return MongoDBManagerInstance.get_instance().get_collection(
            db_name=UserManager.database_name,
            collection_name=UserManager.collection_name
        )

    @staticmethod
    def init_database():
        UserManager.collection().create_index([("email", 1)], unique=True)

    @staticmethod
    def generate_user_me_key(user_id: str):
        return f"user:{user_id}:me"

    @staticmethod
    def generate_user_account_key(user_id: str):
        return f"user:{user_id}:account"

    @staticmethod
    def generate_user_preferences_key(user_id: str):
        return f"user:{user_id}:preferences"


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

    def update(self, user_me: UserMe):
        self.firstname = user_me.firstname
        self.lastname = user_me.lastname
        self.address = user_me.address

    def save(self):
        api_logger = ApiLogger(f"[MONGODB] [USER] [SAVE] : {self.to_json()}")

        try:
            result = UserManager.collection().insert_one(self.to_bson())
        except DuplicateKeyError:
            api_logger.print_error("User already exists")
            return None
        self.user_id = result.inserted_id
        api_logger.print_log(f"User ID: {self.user_id}")
        return self.user_id

    @staticmethod
    def scache_all_user():
        api_logger = ApiLogger(f"[REDIS] [USER] [SCACHE ALL]")

        delete_count = RedisManagerInstance.get_instance().delete_pattern(pattern=f"user:*")

        api_logger.print_log(extend_message=f"delete count: {delete_count}")

    @staticmethod
    def _scache_user(user_id: str):
        api_logger = ApiLogger(f"[REDIS] [USER] [SCACHE] : {user_id}")

        delete_count = RedisManagerInstance.get_instance().delete_pattern(pattern=f"user:{user_id}:*")

        api_logger.print_log(extend_message=f"delete count: {delete_count}")

    def update_user(self):
        api_logger = ApiLogger(f"[MONGODB] [USER] [UPDATE] : {self.user_id}")
        result = UserManager.collection().update_one(
            filter={"_id": ObjectId(self.user_id)},
            update={
                "$set": {
                    "firstname": self.firstname,
                    "lastname": self.lastname,
                    "address": self.address,
                    "preferences": self.preferences,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        self._scache_user(user_id=str(self.user_id))
        api_logger.print_log(f"user updated: {result.modified_count > 0}")
        return result.modified_count > 0

    @staticmethod
    def _scache_account(user_id: str):
        RedisManagerInstance.get_instance().delete(key=UserManager.generate_user_account_key(user_id=user_id))

    @classmethod
    def update_account(cls, user_id: str, account: Account):
        api_logger = ApiLogger(f"[MONGODB] [USER] [UPDATE] [ACCOUNT] : {account.model_dump()}")

        if not account.status:
            account.status = "active"
        if not account.role:
            account.role = "user"

        result = UserManager.collection().update_one(
            filter={"_id": ObjectId(user_id)},
            update={
                "$set": {
                    "account": account,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        cls._scache_account(user_id=user_id)
        api_logger.print_log(f"user updated: {result.modified_count > 0}")
        return result.modified_count > 0

    @classmethod
    def update_password(cls, user_id: str, password: str):
        api_logger = ApiLogger(f"[MONGODB] [USER] [UPDATE] [PASSWORD] : {user_id}")
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
        result = UserManager.collection().update_one(
            filter={"_id": ObjectId(user_id)},
            update={
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

    def delete(self):
        api_logger = ApiLogger(f"[MONGODB] [USER] [DELETE] : {self.user_id}")
        result = UserManager.collection().delete_one(
            {"_id": ObjectId(self.user_id)}
        )
        api_logger.print_log(f"user deleted: {result.deleted_count > 0}")
        return result.deleted_count > 0

    @classmethod
    def get(cls, user_id: str):
        api_logger = ApiLogger(f"[MONGODB] [USER] [GET] : {user_id}")
        user = UserManager.collection().find_one({"_id": ObjectId(user_id)})
        if user is None:
            api_logger.print_error("User does not exist")
            return None
        api_logger.print_log()
        return cls(**user)

    @classmethod
    def get_by_email(cls, email: str):
        api_logger = ApiLogger(f"[MONGODB] [USER] [GET] [BY EMAIL] : {email}")
        user = UserManager.collection().find_one({"email": email})
        if user is None:
            api_logger.print_error("User does not exist")
            return None
        api_logger.print_log()
        return cls(**user)

    @staticmethod
    def get_account(user_id: str):
        user_account_key = UserManager.generate_user_account_key(user_id=user_id)

        api_logger = ApiLogger(f"[REGIS] [USER] [GET ACCOUNT] : {user_id}")
        account_caching = RedisManagerInstance.get_instance().get_dict(key=user_account_key)
        if account_caching:
            api_logger.print_log()
            return Account(**account_caching)
        api_logger.print_error(message_error="Cache missing")

        user = User.get(user_id=user_id)
        RedisManagerInstance.get_instance().set_dict(key=user_account_key, value=user.account.model_dump())
        return user.account


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

    @classmethod
    def get(cls, user_id: str):
        user_me_key = UserManager.generate_user_me_key(user_id=user_id)

        api_logger = ApiLogger(f"[REDIS] [USER] [GET ME] : {user_id}")
        user_me_caching = RedisManagerInstance.get_instance().get_dict(key=user_me_key)
        if user_me_caching:
            api_logger.print_log()
            return cls(**user_me_caching)
        api_logger.print_error(message_error="Cache missing")

        user = User.get(user_id=user_id)
        user_me = cls.from_user(user)
        RedisManagerInstance.get_instance().set_dict(key=user_me_key, value=user_me.to_json())
        return user_me

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


class UserMePreferences(DataBaseModel):
    preferences: list[str] = []

    @classmethod
    def from_user(cls, user: User):
        return cls(preferences=user.preferences)

    @classmethod
    def get_preferences(cls, user_id: str):
        user_preferences_key = UserManager.generate_user_me_key(user_id=user_id)

        api_logger = ApiLogger(f"[REGIS] [USER] [GET PREFERENCES] : {user_id}")
        preferences_caching = RedisManagerInstance.get_instance().get_list(key=user_preferences_key)
        if preferences_caching:
            api_logger.print_log()
            return cls(preferences=preferences_caching)
        api_logger.print_error(message_error="Cache missing")

        user = User.get(user_id=user_id)
        if user is None:
            return cls(preferences=[])
        RedisManagerInstance.get_instance().set_list(key=user_preferences_key, value=user.preferences, ex=60*60)
        return cls(preferences=user.preferences)

    @staticmethod
    def to_model(name_space: Namespace):
        return name_space.model('UserMePreferencesModel', {
            'preferences': fields.List(fields.String, description="List of preferences (tags, categories, ...)"),
        })

