from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional, Literal

from bson import ObjectId
from flask_restx import Namespace, fields
from pydantic import Field, field_serializer, BaseModel
from pymongo.errors import DuplicateKeyError

from src.lib.configuration import configuration
from src.lib.database.nosql.document.mongodb.base import MongoDBBaseModel
from src.lib.database.nosql.document.mongodb.mongodb_manager import MongoDBManagerInstance
from src.lib.database.nosql.document.mongodb.objectid import PydanticObjectId
from src.lib.database.nosql.keyvalue.redis.redis_manager import RedisManagerInstance
from src.lib.log.api_logger import ApiLogger


class UserArticleInteractionManager:
    database_name = configuration.get_configuration("mongodb.database")
    collection_name = configuration.get_configuration("mongodb.collection.articles")

    @staticmethod
    def collection():
        return MongoDBManagerInstance.get_instance().get_collection(
            db_name=UserArticleInteractionManager.database_name,
            collection_name=UserArticleInteractionManager.collection_name
        )

    @staticmethod
    def generate_user_article_interaction_key(user_id: str, article_id: str, comment_id: str = None):
        if comment_id:
            return f"user:{user_id}:article:{article_id}:comment:{comment_id}"
        return f"user:{user_id}:article:{article_id}"

LEVEL_INTERACTION = Literal["article", "comment"]

class UserArticleInteractionModel(MongoDBBaseModel):
    interaction_id: Optional[PydanticObjectId] = Field(None, alias="_id")

    level_interaction: str

    user_id: str
    article_id: str
    comment_id: Optional[str] = None

    read_at: datetime = datetime.now()
    time_spent: Optional[int] = Field(default=None, ge=0)
    liked: Optional[bool] = False
    shared: Optional[bool] = False
    saved: Optional[bool] = False
    report: Optional[str] = None

    @field_serializer("interaction_id")
    def serialize_id(self, id_value: PydanticObjectId, _info):
        return str(id_value) if id_value else None

    @staticmethod
    def to_model(name_space: Namespace):
        return name_space.model('UserArticleInteractionModel', {
            'interaction_id': fields.String(required=True),
            'level_interaction': fields.String(required=True),
            'user_id': fields.String(required=True),
            'article_id': fields.String(required=True),
            'comment_id': fields.String(required=False),
            'read_at': fields.DateTime(required=False),
            'time_spent': fields.Integer(required=False),
            'liked': fields.Boolean(required=False),
            'shared': fields.Boolean(required=False),
            'saved': fields.Boolean(required=False),
            'report': fields.String(required=False),
        })

    def update(self, interaction: UserArticleInteraction):
        if not interaction.liked is None:
            self.liked = interaction.liked
        if not interaction.shared is None:
            self.shared = interaction.shared
        if not interaction.saved is None:
            self.saved = interaction.saved
        if not interaction.report is None:
            self.report = interaction.report

    def save(self):
        api_logger = ApiLogger(f"[MONGODB] [USER ARTICLE INTERACTION] [SAVE] : {self.to_json()}")
        try:
            if self.interaction_id:
                data = self.to_json()
                del data["interaction_id"]
                result = UserArticleInteractionManager.collection().update_one(
                    {"_id": ObjectId(self.interaction_id)},
                    {"$set": data}
                )
            else:
                result = UserArticleInteractionManager.collection().insert_one(self.to_bson())
        except DuplicateKeyError:
            api_logger.print_error("User already exists")
            return None
        self.interaction_id = result.inserted_id
        api_logger.print_log(f"Interaction ID: {self.interaction_id}")
        return self.interaction_id

    @staticmethod
    def scache_interaction(user_id: str, article_id: str, comment_id: str = None):
        api_logger = ApiLogger(f"[REDIS] [USER ARTICLE INTERACTION] [SCACHE] : user={user_id}, article={article_id} and comment={comment_id}")

        delete_result = RedisManagerInstance.get_instance().delete(key=UserArticleInteractionManager.generate_user_article_interaction_key(user_id=user_id, article_id=article_id, comment_id=comment_id))

        api_logger.print_log(f"Delete result: {delete_result}")

    @classmethod
    def update_interaction_read(cls, user_id: str, article_id: str, comment_id: str = None):
        api_logger = ApiLogger(f"[MONGODB] [USER ARTICLE INTERACTION] [UPDATE] : user : {user_id}, article : {article_id} and comment={comment_id}")
        filter_key = {"user_id": user_id, "article_id": article_id}
        filter_key |= {"comment_id": comment_id} if comment_id else {}
        datetime_operation = datetime.now(timezone.utc)
        data_on_insert = {
            "level_interaction": "comment" if comment_id else "article",
            "liked": False,
            "shared": False,
            "saved": False
        }
        result = UserArticleInteractionManager.collection().update_one(
            filter=filter_key,
            update={
                "$set": {
                    "read_at": datetime_operation,
                    "updated_at": datetime_operation
                },
                "$setOnInsert": data_on_insert,
                "$inc": {
                    "time_spent": 30  # increment by 30 seconds
                }
            },
            upsert=True
        )
        cls.scache_interaction(user_id=user_id, article_id=article_id)
        api_logger.print_log(f"Update result: {result.modified_count > 0}")

    @classmethod
    def update_interaction(cls, interaction: UserArticleInteraction, user_id: str, article_id: str, comment_id: str = None):
        api_logger = ApiLogger(f"[MONGODB] [USER ARTICLE INTERACTION] [UPDATE] : user={user_id}, article={article_id}, comment={comment_id} and interaction={interaction}")
        filter_key = {"user_id": user_id, "article_id": article_id}
        filter_key |= {"comment_id": comment_id} if comment_id else {}

        preview_interaction = cls.get_by_user_article(user_id=user_id, article_id=article_id, comment_id=comment_id)
        if preview_interaction is None:
            level_interaction = "comment" if comment_id else "article"
            preview_interaction = cls(_id=None, level_interaction=level_interaction, user_id=user_id, article_id=article_id, comment_id=comment_id)
        preview_interaction.update(interaction)
        b = preview_interaction.save()

        api_logger.print_log()

        return not b is None

    @classmethod
    def get(cls, interaction_id: str):
        api_logger = ApiLogger(f"[MONGODB] [USER ARTICLE INTERACTION] [GET] : {interaction_id}")
        interaction = UserArticleInteractionManager.collection().find_one({"_id": ObjectId(interaction_id)})
        if interaction is None:
            api_logger.print_error("User Article Interaction does not exist")
            return None
        api_logger.print_log()
        return cls(**interaction)

    @classmethod
    def get_by_user_article(cls, user_id: str, article_id: str, comment_id: str = None):
        api_logger = ApiLogger(f"[MONGODB] [USER ARTICLE INTERACTION] [GET] [BY USER ARTICLE] : user={user_id}, article={article_id} and comment={comment_id}")
        interaction = UserArticleInteractionManager.collection().find_one(
            {
                "user_id": user_id,
                "article_id": article_id,
                "comment_id": comment_id,
            }
        )
        if interaction is None:
            api_logger.print_error("User Article Interaction does not exist")
            return None
        api_logger.print_log()
        return cls(**interaction)

    @classmethod
    def get_read_history(cls, user_id: str, limit: int = 5):
        api_logger = ApiLogger(f"[MONGODB] [USER ARTICLE INTERACTION] [GET] [HISTORY] : user={user_id}")

        result = UserArticleInteractionManager.collection().find(
            {"user_id": user_id, "read_at": {"$exists": True}},
            # {"_id": 0, "article_id": 1, "read_at": 1, "time_spent": 1}
        ).sort("read_at", -1).limit(limit)

        if result:
            api_logger.print_log()
            histories = [cls(**history) for history in result]
            return histories
        api_logger.print_error(message_error=f"User Article Interaction does not exist")
        return []


class UserArticleInteraction(BaseModel):

    time_spent: Optional[int] = Field(default=None, ge=0)
    liked: Optional[bool] = False
    shared: Optional[bool] = False
    saved: Optional[bool] = False
    report: Optional[str] = None

    @staticmethod
    def to_model(name_space: Namespace):
        return name_space.model('UserArticleInteraction', {
            'time_spent': fields.Integer(required=False),
            'liked': fields.Boolean(required=False),
            'shared': fields.Boolean(required=False),
            'saved': fields.Boolean(required=False),
            'report': fields.String(required=False),
        })

