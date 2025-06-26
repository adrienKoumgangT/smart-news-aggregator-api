from datetime import datetime, timedelta
from typing import Optional

from bson import ObjectId
from flask_restx import Namespace, fields
from pydantic import Field, field_serializer
from pymongo.errors import DuplicateKeyError

from src.lib.configuration import configuration
from src.lib.database.nosql.document.mongodb.base import MongoDBBaseModel
from src.lib.database.nosql.document.mongodb.mongodb_manager import mongodb_client
from src.lib.database.nosql.document.mongodb.objectid import PydanticObjectId
from src.lib.database.nosql.keyvalue.redis.redis_manager import RedisManagerInstance
from src.lib.log.api_logger import ApiLogger
from src.models import DataManagerBase
from src.models.user.user_model import UserAuthor


class CommentManager(DataManagerBase):
    database_name = configuration.get_configuration("mongodb.database")
    collection_name = configuration.get_configuration("mongodb.collection.comments")

    @staticmethod
    def collection():
        """
        return MongoDBManagerInstance.get_instance().get_collection(
            db_name=CommentManager.database_name,
            collection_name=CommentManager.collection_name
        )
        """
        return mongodb_client[CommentManager.database_name][CommentManager.collection_name]

    @staticmethod
    def init_database():
        CommentManager.collection().createIndex({ "article_id": 1 })
        CommentManager.collection().createIndex({ "article_id": 1, "created_at": 1 })

    @staticmethod
    def generate_comment_count_key(after_date: datetime = None, before_date: datetime = None):
        return f"comments:count:{after_date}:{before_date}"


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

    def save(self):
        api_logger = ApiLogger(f"[MONGODB] [COMMENT] [SAVE] : {self.to_json()}")

        comment = self.get_by_user_article(user_id=self.user_id, article_id=self.article_id, comment_fk=self.comment_fk)
        if comment is None:
            comment = self
        try:
            result = CommentManager.collection().insert_one(comment.to_bson())
            # TODO: scache comment
        except DuplicateKeyError:
            api_logger.print_error("Error during save")
            return None
        self.comment_id = result.inserted_id
        api_logger.print_log(f"Comment ID: {self.comment_id}")
        return self.comment_id

    def update_author(self, author: Optional[UserAuthor]):
        api_logger = ApiLogger(f"[MONGODB] [COMMENT] [UPDATE] [AUTHOR] : {self.user_id} ({author.to_json()})")
        result = CommentManager.collection().update_one(
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

    def delete(self):
        api_logger = ApiLogger(f"[MONGODB] [COMMENT] [DELETE] : {self.comment_id}")
        result = CommentManager.collection().delete_one({"_id": ObjectId(self.comment_id)})
        # TODO: scache comment
        api_logger.print_log(f"Comment deleted: {result.deleted_count > 0}")
        return result.deleted_count > 0

    @classmethod
    def get(cls, comment_id: str):
        api_logger = ApiLogger(f"[MONGODB] [COMMENT] [GET] : {comment_id}")

        comment = CommentManager.collection().find_one({"_id": ObjectId(comment_id)})

        if comment is None:
            api_logger.print_error("Comment not found")
            return None
        api_logger.print_log()
        return cls(**comment)

    @classmethod
    def get_by_user_article(cls, user_id: str, article_id: str, comment_fk: str = None):
        api_logger = ApiLogger(f"[MONGODB] [COMMENT] [GET] : user={user_id}, article={article_id} and comment={comment_fk}")

        comment = CommentManager.collection().find_one({
            "user_id": user_id,
            "article_id": article_id,
            "comment_fk": comment_fk
        })

        if comment is None:
            api_logger.print_error("Comment not found")
            return None
        api_logger.print_log()
        return cls(**comment)

    @classmethod
    def get_by_user(cls, user_id: str, page: int = 1, limit: int = 3):
        api_logger = ApiLogger(f"[MONGODB] [COMMENT] [GET] : user={user_id}")

        # TODO: take in cache

        results = CommentManager.collection().find(
            {'user_id': user_id},
        ).sort('insert_at', -1).skip(limit * (page-1)).limit(limit)

        api_logger.print_log()

        if results:
            return [cls(**result) for result in results]
        return []

    @staticmethod
    def _cache_comments_count(comment_count: int, after_date: datetime = None, before_date: datetime = None):
        api_logger = ApiLogger(f"[REDIS] [COMMENT COUNT] [SET] : comment_count = {comment_count}, after_date = {after_date} and before_date = {before_date}")

        user_count_key = CommentManager.generate_comment_count_key(after_date=after_date, before_date=before_date)

        RedisManagerInstance.get_instance().set(key=user_count_key, value=str(comment_count), ex=timedelta(hours=1))

        api_logger.print_log()

    @staticmethod
    def _scache_comments_count(after_date: datetime = None, before_date: datetime = None):
        api_logger = ApiLogger(
            f"[REDIS] [COMMENT COUNT] [DELETE] : after_date = {after_date} and before_date = {before_date}")

        user_count_key = CommentManager.generate_comment_count_key(after_date=after_date, before_date=before_date)

        RedisManagerInstance.get_instance().delete(key=user_count_key)

        api_logger.print_log()

    @staticmethod
    def _get_list_count(after_date: datetime = None, before_date: datetime = None):
        api_logger = ApiLogger(f"[REDIS] [COMMENT COUNT] [GET] : after_date = {after_date} and before_date = {before_date}")

        user_count_key = CommentManager.generate_comment_count_key(after_date=after_date, before_date=before_date)

        user_count = RedisManagerInstance.get_instance().get(key=user_count_key)

        if user_count:
            api_logger.print_log()
            return int(user_count)

        api_logger.print_error("Cache missing")
        return None

    @staticmethod
    def get_list_count(article_id: str =None, after_date: datetime = None, before_date: datetime = None):
        total = CommentModel._get_list_count(after_date=after_date, before_date=before_date)
        if total:
            return total

        api_logger = ApiLogger(f"[MONGODB] [COMMENT COUNT] [ALL] : after_date = {after_date} and before_date = {before_date}")
        if after_date or before_date:
            match_created_at = ({}
                                | ({'$gt': after_date} if after_date else {})
                                | ({'$lt': before_date} if before_date else {}))
            match = ({'article_id': article_id} if article_id else {}) | {'created_at': match_created_at}
            pipeline = [
                {
                    '$match': match
                }, {
                    '$count': 'comments_count'
                }
            ]
            result = CommentManager.collection().aggregate(pipeline)
            if result:
                stats = list(result)
                print(stats)
                if stats:
                    total = stats[0]['comments_count']
                else:
                    total = 0
            else:
                total = 0
        else:
            if article_id:
                total = CommentManager.collection().count_documents(filter={'article_id': article_id})
            else:
                # total = CommentManager.collection().count_documents({})
                total = CommentManager.collection().estimated_document_count({})
        api_logger.print_log()

        CommentModel._cache_comments_count(comment_count=total, after_date=after_date, before_date=before_date)

        return total if (total and total > 0) else 0

    @classmethod
    def get_list(cls, article_id: str =None, page: int = 1, limit: int = 10):
        api_logger = ApiLogger(f"[MONGODB] [COMMENT] [LIST] : page={page} and limit={limit}")

        results = CommentManager.collection().find(
            filter={'article_id': article_id} if article_id else {},
            skip=limit * (page - 1),
            limit=limit
        )

        api_logger.print_log()

        if results:
            return [cls(**result) for result in results]
        return []

    @classmethod
    def last_comments(cls, article_id: str, page: int = 1, limit: int = 3):
        api_logger = ApiLogger(f"[MONGODB] [COMMENT] [GET] : article={article_id}, page={page} and limit={limit}")

        results = CommentManager.collection().find(
            {'article_id': article_id},
        ).sort('insert_at', -1).skip(limit * (page-1)).limit(limit)

        api_logger.print_log()

        if results:
            # print(results)
            return [cls(**result) for result in results]
        return []



