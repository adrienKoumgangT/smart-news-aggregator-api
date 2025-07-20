from datetime import datetime
from typing import Optional

from bson import ObjectId
from flask_restx import Namespace, fields
from pydantic import Field, field_serializer

from src.lib.database.nosql.document.mongodb.base import MongoDBBaseModel
from src.lib.database.nosql.document.mongodb.mongodb_monitoring_middleware import MONGO_QUERY_TIME
from src.lib.database.nosql.document.mongodb.objectid import PydanticObjectId
from src.lib.log.api_logger import ApiLogger
from src.models import DataBaseModel
from src.models.article.article_source_model import ArticleSourceModel
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
        try:
            cls.collection().createIndex({"article_id": 1})
        except Exception as e:
            print(e)
        try:
            cls.collection().createIndex({"user_id": 1})
        except Exception as e:
            print(e)
        try:
            cls.collection().createIndex([("article_id", 1), ("created_at", -1)])
        except Exception as e:
            print(e)
        try:
            cls.collection().createIndex([("user_id", 1), ("created_at", -1)])
        except Exception as e:
            print(e)
        try:
            cls.collection().createIndex([("comment_fk", 1), ("created_at", -1)])
        except Exception as e:
            print(e)
        try:
            pass
        except Exception as e:
            print(e)

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
        with MONGO_QUERY_TIME.time():
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

        with MONGO_QUERY_TIME.time():
            results = cls.collection().find(
                {'article_id': article_id},
            ).sort('insert_at', -1).skip(limit * (page-1)).limit(limit)

        api_logger.print_log()

        if results:
            # print(results)
            return [cls(**result) for result in results]
        return []


class ArticleInfoModel(DataBaseModel):
    extern_api: Optional[str]
    title: str
    description: Optional[str] = None
    author: Optional[ArticleSourceModel] = None
    source: Optional[ArticleSourceModel] = None
    published_at: str | datetime

    @staticmethod
    def to_model(name_space: Namespace):
        return name_space.model('ArticleInfoModel', {
            'extern_api': fields.String(required=True),
            'title': fields.String(required=True),
            'description': fields.String(required=True),
            'author': fields.Nested(ArticleSourceModel.to_model(name_space)),
            'source': fields.Nested(ArticleSourceModel.to_model(name_space)),
            'published_at': fields.String(required=True),
        })


class CommentDetailsModel(CommentModel):
    article_info: Optional[ArticleInfoModel] = None

    @staticmethod
    def to_model(name_space: Namespace):
        return name_space.model('CommentDetailsModel', {
            'comment_id': fields.String(required=False),
            'user_id': fields.String(required=False),
            'author': fields.Nested(UserAuthor.to_model(name_space=name_space), required=False),
            'article_id': fields.String(required=False),
            'comment_fk': fields.String(required=False),
            'content': fields.String(required=True),
            'article_info': fields.Nested(ArticleInfoModel.to_model(name_space=name_space), required=False),
        })

    @staticmethod
    def to_model_list(name_space: Namespace):
        return name_space.model('CommentDetailsModelList', {
            'comments': fields.List(fields.Nested(CommentDetailsModel.to_model(name_space)), ),
            'total': fields.Integer,
            'page': fields.Integer,
            'limit': fields.Integer,
            'pageCount': fields.Integer,
        })

    @classmethod
    def get_comments_count(cls, user_token: UserToken, user_id: str = None):
        filter = {'user_id': user_id} if user_id else {'user_id': str(user_token.user_id)}

        api_logger = ApiLogger(f"[MONGODB] [COMMENT] [GET] : filter={filter}")

        with MONGO_QUERY_TIME.time():
            total = cls.collection().count_documents(filter=filter)

        api_logger.print_log()

        return total

    @classmethod
    def get_user_comments_with_article(cls, user_token: UserToken, user_id: str = None, page: int = 1, limit: int = 10):
        extra_filter = {}

        if user_id is None:
            user_id = str(user_token.user_id)

        pipeline = [
            {
                "$match": {
                    "user_id": user_id
                }
            },
            {
                "$sort": {
                    "created_at": -1
                }
            },
            {
                "$skip": (page - 1) * limit
            },
            {
                "$limit": limit
            },
            {
                "$addFields": {
                    "article_id_obj": {
                        "$toObjectId": "$article_id"  # Convert string to ObjectId
                    }
                }
            },
            {
                "$lookup": {
                    "from": "articles",
                    "localField": "article_id_obj",
                    "foreignField": "_id",
                    "as": "article"
                }
            },
            {
                "$unwind": "$article"
            },
            {
                "$project": {
                    "_id": 1,
                    "user_id": 1,
                    "author": 1,
                    "article_id": 1,
                    "comment_fk": 1,
                    "content": 1,
                    "created_at": 1,
                    "updated_at": 1,
                    "article_info": {
                        "extern_api": "$article.extern_api",
                        "title": "$article.title",
                        "description": "$article.description",
                        "author": "$article.author",
                        "source": "$article.source",
                        "published_at": "$article.published_at"
                    }
                }
            }
        ]

        api_logger = ApiLogger(f"[MONGODB] [COMMENT] [GET BY USER] : user_id={user_id}, page={page} and limit={limit}")

        with MONGO_QUERY_TIME.time():
            results = cls.collection().aggregate(pipeline)

        api_logger.print_log()

        if results:
            return [cls(**result) for result in results]
        return []


