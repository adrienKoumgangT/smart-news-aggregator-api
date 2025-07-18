from datetime import datetime, timezone
from threading import Thread
from typing import Optional

from bson import ObjectId
from flask_restx import fields, Namespace
from pydantic import Field, field_serializer

from src.lib.authentication.password import hash_password
from src.lib.database.nosql.document.mongodb.base import MongoDBBaseModel
from src.lib.database.nosql.document.mongodb.mongodb_monitoring_middleware import MONGO_QUERY_TIME
from src.lib.database.nosql.document.mongodb.objectid import PydanticObjectId
from src.lib.database.nosql.keyvalue.redis.redis_manager import RedisManagerInstance
from src.lib.log.api_logger import ApiLogger
from src.models import DataBaseModel
from src.models.user.auth_model import UserToken

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


class PasswordHistory(DataBaseModel):
    password: str
    created_at: datetime


class Account(DataBaseModel):
    status: str
    role: str

    @staticmethod
    def to_model(name_space: Namespace):
        return name_space.model('AccountModel', {
            'status': fields.String(required=True),
            'role': fields.String(required=True),
        })


class Address(DataBaseModel):
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


class UserAuthor(MongoDBBaseModel):
    user_id: Optional[PydanticObjectId] = Field(None, alias="_id")

    firstname: str
    lastname: str

    @field_serializer("user_id")
    def serialize_id(self, id_value: PydanticObjectId, _info):
        return str(id_value) if id_value else None

    @classmethod
    def _name(cls) -> str:
        return "user"

    @classmethod
    def _id_name(cls) -> str:
        return "user_id"

    def _data_id(self) -> ObjectId:
        return self.user_id

    @classmethod
    def init(cls):
        cls.collection().create_index([("email", 1)], unique=True)

    @staticmethod
    def to_model(name_space: Namespace):
        return name_space.model('UserAuthorModel', {
            'user_id': fields.String(required=True),
            'firstname': fields.String(required=True),
            'lastname': fields.String(required=True),
        })


class UserMe(UserAuthor):
    email: str
    phone: Optional[str] = None
    cell: Optional[str] = None
    account: Account
    address: Optional[Address] = None

    @staticmethod
    def to_model(name_space: Namespace):
        return name_space.model('UserMeModel', {
            'user_id': fields.String(required=True),
            'firstname': fields.String(required=True),
            'lastname': fields.String(required=True),
            'email': fields.String(required=True),
            'phone': fields.String(required=False),
            'cell': fields.String(required=False),
            'account': fields.Nested(Account.to_model(name_space)),
            'address': fields.Nested(Address.to_model(name_space)),
        })

    @staticmethod
    def to_model_list(name_space: Namespace):
        return name_space.model('UserMeModelList', {
            'users': fields.List(fields.Nested(UserMe.to_model(name_space)), ),
            'total': fields.Integer,
            'page': fields.Integer,
            'limit': fields.Integer,
            'pageCount': fields.Integer,
        })


class User(UserMe):
    password: str
    password_history: list[PasswordHistory] = []

    preferences: list[str] = []
    preferences_enable: bool = False


    def to_author(self):
        available_fields = {k for k in UserAuthor.model_fields.keys() if hasattr(self, k)}

        author_data = self.model_dump(include=available_fields)
        author_data['_id'] = self.user_id
        return UserAuthor(**author_data)

    def to_me(self):
        available_fields = {k for k in UserMe.model_fields.keys() if hasattr(self, k)}
        # print(available_fields)
        me_data = self.model_dump(include=available_fields)
        # print(me_data)
        me_data['_id'] = self.user_id
        me_data['user_id'] = self.user_id
        # print(me_data)
        return UserMe(**me_data)


    def to_author_json(self):
        return self.model_dump(
            by_alias=False,
            exclude_none=True,
            include=UserAuthor.model_fields.keys(),
            exclude={"created_at", "updated_at"},
        )

    def to_me_json(self):
        return self.model_dump(
            by_alias=False,
            exclude_none=False,
            include=UserMe.model_fields.keys(),
            exclude={"created_at", "updated_at"},
        )

    def to_preferences_json(self):
        return {
            "preferences": self.preferences,
            "preferences_enable": self.preferences_enable,
        }

    @classmethod
    def get_directly(cls, user_id: str):

        api_logger = ApiLogger(f"[MONGODB] [USER] [GET] : {user_id}")
        with MONGO_QUERY_TIME.time():
            result = cls.collection().find_one({"_id": ObjectId(user_id)})
        if result is None:
            api_logger.print_error("User does not exist")
            return None
        api_logger.print_log()

        return cls(**result)

    def save(self, user_token: UserToken):
        self.user_id = super().save(user_token)

    @staticmethod
    def scache_all_user():
        api_logger = ApiLogger(f"[REDIS] [USER] [SCACHE ALL]")

        delete_count = RedisManagerInstance.get_instance().delete_pattern(pattern=f"user:*")

        api_logger.print_log(extend_message=f"delete count: {delete_count}")

    def update_user(self, user_token: UserToken):
        api_logger = ApiLogger(f"[MONGODB] [USER] [UPDATE] : {self.to_json()}")
        with MONGO_QUERY_TIME.time():
            result = self.collection().update_one(
                filter={"_id": ObjectId(self.user_id)},
                update={
                    "$set": {
                        "firstname": self.firstname,
                        "lastname": self.lastname,
                        "phone": self.phone if self.phone else "",
                        "cell": self.cell if self.cell else "",
                        "address": self.address.to_json() if self.address else None,
                        "preferences": self.preferences,
                        "preferences_enable": self.preferences_enable,
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
        # print(result)
        self._scache(user_token, str(self.user_id))
        api_logger.print_log(f"user updated: {result.modified_count > 0}")
        return result.modified_count > 0

    @classmethod
    def update_account(cls, user_token: UserToken, user_id: str, account: Account):
        api_logger = ApiLogger(f"[MONGODB] [USER] [UPDATE] [ACCOUNT] : {account.model_dump()}")

        if not account.status:
            account.status = "active"
        if not account.role:
            account.role = "user"

        with MONGO_QUERY_TIME.time():
            result = cls.collection().update_one(
                filter={"_id": ObjectId(user_id)},
                update={
                    "$set": {
                        "account": account,
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
        cls._scache(user_token, user_id)
        api_logger.print_log(f"user updated: {result.modified_count > 0}")
        return result.modified_count > 0

    @classmethod
    def update_password(cls, user_token: UserToken, user_id: str, password: str):
        api_logger = ApiLogger(f"[MONGODB] [USER] [UPDATE] [PASSWORD] : {user_id}")
        hashed_password = hash_password(password)

        user = cls.get(user_token, user_id)
        if not user:
            api_logger.print_error("User does not exist")
            return {"error": "User not found"}
        for old_password in user.password_history:
            if old_password.password == hashed_password:
                api_logger.print_error("Password already used")
                return {"error": "You cannot reuse an old password"}

        current_datetime = datetime.now(timezone.utc)

        password_history = PasswordHistory(password=hashed_password, created_at=current_datetime)
        with MONGO_QUERY_TIME.time():
            result = cls.collection().update_one(
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

    @classmethod
    def get_by_email(cls, email: str):
        api_logger = ApiLogger(f"[MONGODB] [USER] [GET] [BY EMAIL] : {email}")
        with MONGO_QUERY_TIME.time():
            user = cls.collection().find_one({"email": email})
        if user is None:
            api_logger.print_error("User does not exist")
            return None
        api_logger.print_log()
        return cls(**user)



class UserMePreferences(DataBaseModel):
    preferences: list[str] = []
    preferences_enable: bool = True

    @classmethod
    def from_user(cls, user: User):
        return cls(preferences=user.preferences)

    @classmethod
    def get_preferences(cls, user_token: UserToken, user_id: str):
        user = User.get(user_token, user_id)
        if user is None:
            return None

        return cls(preferences=user.preferences, preferences_enable=user.preferences_enable)

    @staticmethod
    def to_model(name_space: Namespace):
        return name_space.model('UserMePreferencesModel', {
            'preferences': fields.List(fields.String, description="List of preferences (tags, categories, ...)"),
            'preferences_enable': fields.Boolean(default=True, required=False),
        })


class UserPreferencesDashboard(DataBaseModel):
    tag: str
    count: int

    @staticmethod
    def to_model(name_space: Namespace):
        return name_space.model('UserPreferencesDashboardModel', {
            'tag': fields.String(required=False),
            'count': fields.Integer(required=False),
        })

    @classmethod
    def get_most_tags(cls, limit: int = 5):
        api_logger = ApiLogger(f"[MONGODB] [USER TAGS] [DASHBOARD] [MOST TAGS IN PREFERENCES] : limit={limit}")

        pipeline = [
            {
                '$match': {
                    'preferences': {'$exists': True, '$ne': []}
                }
            }, {
                '$unwind': '$preferences'
            }, {
                '$group': {
                    '_id': '$preferences',
                    'count': {'$sum': 1}
                }
            }, {
                '$sort': {
                    'count': -1
                }
            }, {
                '$limit': limit
            }, {
                '$project': {
                    'tag': '$_id',
                    'count': 1,
                    '_id': 0
                }
            }
        ]

        with MONGO_QUERY_TIME.time():
            stats = cls.collection().aggregate(pipeline)
        if stats is None:
            api_logger.print_error("Error during retrieving statistics")

        stat_list = list(stats)
        api_logger.print_log()

        return [cls(**data) for data in stat_list]


class UserUtility:

    @classmethod
    def _cache_users(cls, user_token: UserToken, users: list[User]):
        for user in users:
            _ = User.get(user_token, str(user.user_id))

    @classmethod
    def cache_users(cls, user_token: UserToken, users: list[User]):
        thread = Thread(target=UserUtility._cache_users, args=(user_token, users,))
        thread.daemon = True
        thread.start()



