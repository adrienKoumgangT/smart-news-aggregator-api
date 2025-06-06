from typing import Optional, List

from flask_restx import fields, Namespace
from pydantic import Field, field_serializer, BaseModel
from pymongo.errors import DuplicateKeyError

from src.lib.configuration import configuration
from src.lib.database.nosql.document.mongodb.base import MongoDBBaseModel
from src.lib.database.nosql.document.mongodb.mongodb_manager import MongoDBManagerInstance
from src.lib.database.nosql.document.mongodb.objectid import PydanticObjectId
from src.lib.log.api_logger import ApiLogger
from src.models.article.comment_model import CommentModel

class ArticleManager:
    database_name = configuration.get_configuration("mongodb.database")
    collection_name = configuration.get_configuration("mongodb.collection.articles")


class ArticleSourceModel(BaseModel):
    name: Optional[str]
    url: Optional[str]

    @staticmethod
    def to_model(name_space: Namespace):
        return name_space.model('ArticleSourceModel', {
            'name': fields.String(required=True),
            'url': fields.String(required=True),
        })


class ArticleModel(MongoDBBaseModel):
    article_id: Optional[PydanticObjectId] = Field(None, alias="_id")
    extern_id: Optional[str]
    extern_api: Optional[str]

    title: str
    description: Optional[str]
    content: Optional[str]
    url: Optional[str]
    author: Optional[ArticleSourceModel]
    source: Optional[ArticleSourceModel]
    image_url: Optional[str]
    published_at: str
    language: Optional[str]
    country: Optional[str]
    tags: List[str]

    comments: List[CommentModel] = []

    @field_serializer("article_id")
    def serialize_id(self, id_value: PydanticObjectId, _info):
        return str(id_value) if id_value else None


    def save(self):
        api_logger = ApiLogger(f"[MONGODB] [ARTICLES] [SAVE] : {self.to_json()}")

        articles_collection = MongoDBManagerInstance.get_instance().get_collection(
            db_name=ArticleManager.database_name,
            collection_name=ArticleManager.collection_name
        )

        article = articles_collection.find_one(
            {
                'extern_api': self.extern_api,
                'extern_id': self.extern_id,
                'title': self.title
            }
        )
        if article:
            api_logger.print_error("Article already exists")
            return None

        try:
            result = articles_collection.insert_one(self.to_bson())
        except DuplicateKeyError:
            api_logger.print_error("Article already exists")
            return None
        self.article_id = result.inserted_id
        api_logger.print_log(f"Article ID: {self.article_id}")
        return self.article_id


