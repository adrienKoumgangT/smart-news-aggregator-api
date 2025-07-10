from datetime import datetime
from typing import Optional

from bson import ObjectId
from flask_restx import Namespace, fields
from pydantic import Field, field_serializer

from src.lib.database.nosql.document.mongodb.base import MongoDBBaseModel
from src.lib.database.nosql.document.mongodb.objectid import PydanticObjectId
from src.lib.log.api_logger import ApiLogger
from src.models.user.auth_model import UserToken
from src.models.user.user_model import UserAuthor



class CommentModel(MongoDBBaseModel):
    comment_id: Optional[PydanticObjectId] = Field(None, alias="_id")

    user_id: str
    author: Optional[UserAuthor] = None
    article_id: str
    comment_fk: Optional[str] = None
    content: str

    @field_serializer("comment_id")
    def serialize_id(self, id_value: PydanticObjectId, _info):
        return str(id_value) if id_value else None

    @classmethod
    def _name(cls) -> str:
        return "comment"

    @classmethod
    def _id_name(cls) -> str:
        return "comment_id"

    def _data_id(self) -> ObjectId:
        return self.comment_id

    @classmethod
    def init(cls):
        cls.collection().createIndex({"article_id": 1})
        cls.collection().createIndex({"article_id": 1, "created_at": 1})

    @staticmethod
    def to_model(name_space: Namespace):
        return name_space.model('CommentModel', {
            'comment_id': fields.String(required=False),
            'user_id': fields.String(required=False),
            'author': fields.Nested(UserAuthor.to_model(name_space=name_space), required=False),
            'article_id': fields.String(required=False),
            'comment_fk': fields.String(required=False),
            'content': fields.String(required=True),
        })

    @staticmethod
    def to_model_list(name_space: Namespace):
        return name_space.model('CommentModelList', {
            'comments': fields.List(fields.Nested(CommentModel.to_model(name_space)), )
        })

    @classmethod
    def _cache_key(cls, user_token: UserToken, data_id: str, *args, **kwargs) -> str:
        return f"comment:{data_id}"


    def save(self, user_token: UserToken):
        self.comment_id = super().save(user_token)

    def update_author(self, author: Optional[UserAuthor]):
        api_logger = ApiLogger(f"[MONGODB] [COMMENT] [UPDATE] [AUTHOR] : {self.user_id} ({author.to_json()})")
        result = self.collection().update_one(
            filter={'_id': ObjectId(self.comment_id)},
            update={
                '$set': {
                    'author': author.to_json()
                }
            }
        )
        if result.modified_count > 0:
            self.author = author
        api_logger.print_log(f"comment updated: {result.modified_count > 0}")
        return result.modified_count > 0

    @classmethod
    def get_by_user_article(cls, user_token: UserToken, user_id: str, article_id: str, comment_fk: str = None):
        extra_filter = {
            "user_id": user_id,
            "article_id": article_id,
            "comment_fk": comment_fk
        }

        return cls.get_by(user_token, extra_filter)

    @classmethod
    def get_by_user(cls, user_token: UserToken, user_id: str, page: int = 1, limit: int = 3):
        extra_filter = {'user_id': user_id}

        return cls.get_by(user_token, extra_filter=extra_filter, page=page, limit=limit)

    @classmethod
    def get_all_count(cls, user_token: UserToken, extra_match: dict = None, after_date: datetime = None, before_date: datetime = None, article_id: str =None):
        extra_match = {} | ({'article_id': article_id} if article_id else {})

        return super().get_all_count(user_token, extra_match, after_date, before_date)

    @classmethod
    def get_all(cls, user_token: UserToken, extra_match: dict = None, page: int = 1, limit: Optional[int] = 10, article_id: str =None):
        if extra_match is None:
            extra_match = {}
        extra_match |= ({'article_id': article_id} if article_id else {})

        return super().get_all(user_token, extra_match=extra_match, page=page, limit=limit)

    @classmethod
    def last_comments(cls, article_id: str, page: int = 1, limit: int = 3):
        api_logger = ApiLogger(f"[MONGODB] [COMMENT] [GET] : article={article_id}, page={page} and limit={limit}")

        results = cls.collection().find(
            {'article_id': article_id},
        ).sort('insert_at', -1).skip(limit * (page-1)).limit(limit)

        api_logger.print_log()

        if results:
            # print(results)
            return [cls(**result) for result in results]
        return []



