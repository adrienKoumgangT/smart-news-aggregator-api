from typing import Optional, List

from bson import ObjectId
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
    name: Optional[str] = None
    url: Optional[str] = None

    @staticmethod
    def to_model(name_space: Namespace):
        return name_space.model('ArticleSourceModel', {
            'name': fields.String(required=True),
            'url': fields.String(required=True),
        })


class ArticleSummaryModel(MongoDBBaseModel):
    article_id: Optional[PydanticObjectId] = Field(None, alias="_id")
    extern_id: Optional[str] = None
    extern_api: Optional[str]

    title: str
    description: Optional[str]
    author: Optional[ArticleSourceModel]
    source: Optional[ArticleSourceModel]
    image_url: Optional[str] = None

    published_at: str

    tags: List[str]

    @field_serializer("article_id")
    def serialize_id(self, id_value: PydanticObjectId, _info):
        return str(id_value) if id_value else None

    @staticmethod
    def to_model(name_space: Namespace):
        return name_space.model('ArticleSummaryModel', {
            'article_id': fields.String(required=True),
            'extern_id': fields.String(required=False),
            'extern_api': fields.String(required=True),
            'title': fields.String(required=True),
            'description': fields.String(required=True),
            'author': fields.Nested(ArticleSourceModel.to_model(name_space)),
            'source': fields.Nested(ArticleSourceModel.to_model(name_space)),
            'image_url': fields.String(required=True),
            'published_at': fields.String(required=True),
            'tags': fields.List(fields.String, description="List of tags"),
        })

    @staticmethod
    def to_model_list(name_space: Namespace):
        return name_space.model('ArticleSummaryModelList', {
            'articles': fields.List(fields.Nested(ArticleSummaryModel.to_model(name_space)),)
        })

    @classmethod
    def last_articles(cls, page: int = 1, limit: int = 10):
        api_logger = ApiLogger(f"[MONGODB] [ARTICLE SUMMARY] [GET] : page={page} and limit={limit}")

        articles_collection = MongoDBManagerInstance.get_instance().get_collection(
            db_name=ArticleManager.database_name,
            collection_name=ArticleManager.collection_name
        )

        results = (articles_collection.find(
            {},
            {
                '_id': 1,
                'extern_id': 1,
                'extern_api': 1,
                'title': 1,
                'description': 1,
                'author': 1,
                'source': 1,
                'image_url': 1,
                'published_at': 1,
                'tags': 1,
            }
        )
                   .sort('published_at', -1)
                   .skip(limit * (page-1))
                   .limit(limit))

        api_logger.print_log()

        if results:
            return [cls(**result) for result in results]
        return []




class ArticleModel(ArticleSummaryModel):
    content: Optional[str]
    url: Optional[str]
    language: Optional[str]
    country: Optional[str]

    comments: List[CommentModel] = []

    def to_summary(self):
        return ArticleSummaryModel(
            _id=self.article_id,
            extern_id= self.extern_id,
            extern_api= self.extern_api,
            title=self.title,
            description=self.description,
            author=self.author,
            source=self.source,
            image_url=self.image_url,
            published_at=self.published_at,
            tags=self.tags,
        )

    def save(self):
        api_logger = ApiLogger(f"[MONGODB] [ARTICLE] [SAVE] : {self.to_json()}")

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

    @classmethod
    def get(cls, article_id: str):
        api_logger = ApiLogger(f"[MONGODB] [ARTICLE] [GET] : {article_id}")
        articles_collection = MongoDBManagerInstance.get_instance().get_collection(
            db_name=ArticleManager.database_name,
            collection_name=ArticleManager.collection_name
        )

        article = articles_collection.find_one({'_id': ObjectId(article_id)})
        if article is None:
            api_logger.print_error("Article does not exist")
            return None

        api_logger.print_log()
        return cls(**article)

