from typing import Optional

from bson import ObjectId
from flask_restx import Namespace, fields
from pydantic import Field, field_serializer
from pymongo.errors import DuplicateKeyError

from src.lib.configuration import configuration
from src.lib.database.nosql.document.mongodb.base import MongoDBBaseModel
from src.lib.database.nosql.document.mongodb.mongodb_manager import mongodb_client
from src.lib.database.nosql.document.mongodb.objectid import PydanticObjectId
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


class CommentModel(MongoDBBaseModel):
    comment_id: Optional[PydanticObjectId] = Field(None, alias="_id")

    user_id: str
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
            'article_id': fields.String(required=False),
            'comment_fk': fields.String(required=False),
            'content': fields.String(required=True),
            'author': fields.Nested(UserAuthor.to_model(name_space=name_space), required=False),
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



