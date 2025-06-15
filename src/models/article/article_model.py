import json
from typing import Optional, List

from bson import ObjectId
from flask_restx import fields, Namespace
from pydantic import Field, field_serializer, BaseModel
from pymongo.errors import DuplicateKeyError

from src.lib.configuration import configuration
from src.lib.database.nosql.document.mongodb.base import MongoDBBaseModel
from src.lib.database.nosql.document.mongodb.mongodb_manager import mongodb_client
from src.lib.database.nosql.document.mongodb.objectid import PydanticObjectId
from src.lib.database.nosql.keyvalue.redis.redis_manager import RedisManagerInstance
from src.lib.log.api_logger import ApiLogger
from src.lib.utility.utils import my_json_decoder, MyJSONEncoder
from src.models import DataManagerBase
from src.models.article.user_article_interaction_models import ArticleInteractionStatus, ArticleInteractionStats


class ArticleManager(DataManagerBase):
    database_name = configuration.get_configuration("mongodb.database")
    collection_name = configuration.get_configuration("mongodb.collection.articles")

    @staticmethod
    def collection():
        """
        return MongoDBManagerInstance.get_instance().get_collection(
            db_name=ArticleManager.database_name,
            collection_name=ArticleManager.collection_name
        )
        """
        return mongodb_client[ArticleManager.database_name][ArticleManager.collection_name]

    @staticmethod
    def init_database():
        ArticleManager.collection().createIndex({ "published_at": -1 })
        ArticleManager.collection().create_index([("tags", 1), ("published_at", -1)])

    @staticmethod
    def generate_article_key(article_id: str):
        return f"article:{article_id}"

    @staticmethod
    def generate_article_stats_key(article_id: str):
        return f"article:{article_id}:stats"


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
    description: Optional[str] = None
    author: Optional[ArticleSourceModel] = None
    source: Optional[ArticleSourceModel] = None
    image_url: Optional[str] = None

    published_at: str

    tags: List[str]

    @field_serializer("article_id")
    def serialize_id(self, id_value: PydanticObjectId, _info):
        return str(id_value) if id_value else None

    @staticmethod
    def to_model(name_space: Namespace):
        return name_space.model('ArticleSummaryModel', {
            'article_id': fields.String(required=False),
            'extern_id': fields.String(required=False),
            'extern_api': fields.String(required=True),
            'title': fields.String(required=True),
            'description': fields.String(required=True),
            'author': fields.Nested(ArticleSourceModel.to_model(name_space)),
            'source': fields.Nested(ArticleSourceModel.to_model(name_space)),
            'image_url': fields.String(required=True),
            'published_at': fields.String(required=True),
            'tags': fields.List(fields.String, description="List of tags"),
            'current_user_interaction': fields.Nested(ArticleInteractionStatus.to_model(name_space)),
            'total_user_interaction': fields.Nested(ArticleInteractionStats.to_model(name_space)),
        })

    @staticmethod
    def to_model_list(name_space: Namespace):
        return name_space.model('ArticleSummaryModelList', {
            'articles': fields.List(fields.Nested(ArticleSummaryModel.to_model(name_space)),),
            'total': fields.Integer,
            'pages': fields.Integer,
            'pageCount': fields.Integer,
        })


class ArticleModel(ArticleSummaryModel):
    content: Optional[str] = None
    url: Optional[str] = None
    language: Optional[str] = None
    country: Optional[str] = None

    @staticmethod
    def to_model(name_space: Namespace):
        return name_space.model('ArticleModel', {
            'article_id': fields.String(required=False),
            'extern_id': fields.String(required=False),
            'extern_api': fields.String(required=True),
            'title': fields.String(required=True),
            'description': fields.String(required=True),
            'author': fields.Nested(ArticleSourceModel.to_model(name_space)),
            'source': fields.Nested(ArticleSourceModel.to_model(name_space)),
            'image_url': fields.String(required=True),
            'published_at': fields.String(required=True),
            'content': fields.String(required=True),
            'url': fields.String(required=False),
            'language': fields.String(required=False),
            'country': fields.String(required=False),
            'tags': fields.List(fields.String, description="List of tags"),
        })

    @staticmethod
    def to_model_list(name_space: Namespace):
        return name_space.model('ArticleModelList', {
            'articles': fields.List(fields.Nested(ArticleModel.to_model(name_space)), ),
            'total': fields.Integer,
            'pages': fields.Integer,
            'pageCount': fields.Integer,
        })

    def to_summary(self):
        return self.model_dump(
            by_alias=False,
            exclude_none=True,
            include=ArticleSummaryModel.model_fields.keys(),
            exclude={"created_at", "updated_at"},
        )

    def save(self):
        api_logger = ApiLogger(f"[MONGODB] [ARTICLE] [SAVE] : {self.to_json()}")

        article = ArticleManager.collection().find_one(
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
            result = ArticleManager.collection().insert_one(self.to_bson())
        except DuplicateKeyError:
            api_logger.print_error("Article already exists")
            return None
        self.article_id = result.inserted_id
        api_logger.print_log(f"Article ID: {self.article_id}")

        return self.article_id

    @classmethod
    def get(cls, article_id: str):
        article_key = ArticleManager.generate_article_key(article_id=article_id)

        api_logger = ApiLogger(f"[REDIS] [ARTICLE] [GET] : {article_id}")
        article_caching = RedisManagerInstance.get_instance().get(key=article_key)
        if article_caching:
            api_logger.print_log()
            # article_json = json.loads(article_caching, object_hook=my_json_decoder)
            article_json = json.loads(article_caching)
            return cls(**article_json)
        api_logger.print_error(message_error="Cache missing")

        api_logger = ApiLogger(f"[MONGODB] [ARTICLE] [GET] : {article_id}")

        result = ArticleManager.collection().find_one({'_id': ObjectId(article_id)})
        if result is None:
            api_logger.print_error("Article does not exist")
            return None
        api_logger.print_log()

        article = cls(**result)

        # article_json = json.dumps(article, cls=MyJSONEncoder)
        article_json = json.dumps(article.to_json())
        RedisManagerInstance.get_instance().set(key=article_key, value=article_json, ex=60*10)

        return article

    @classmethod
    def last_articles(cls, preferences: list[str] = None, page: int = 1, limit: int = 10):
        api_logger = ApiLogger(f"[MONGODB] [ARTICLE SUMMARY] [GET] : page={page} and limit={limit}")
        if preferences:
            filter_search = {
                'tags': {
                    '$in': preferences
                }
            }
        else:
            filter_search = {}
        sort = list({
                        'published_at': -1
                    }.items())
        limit = 10

        results = ArticleManager.collection().find(
            filter=filter_search,
            sort=sort,
            skip=limit * (page - 1),
            limit=limit
        )

        api_logger.print_log()

        if results:
            return [cls(**result) for result in results]
        return []


class ArticleWithInteractionModel(ArticleModel):

    current_user_interaction: Optional[ArticleInteractionStatus] = ArticleInteractionStatus()
    total_user_interaction: Optional[ArticleInteractionStats] = ArticleInteractionStats()

    @staticmethod
    def to_model(name_space: Namespace):
        return name_space.model('ArticleWithInteractionModel', {
            'article_id': fields.String(required=False),
            'extern_id': fields.String(required=False),
            'extern_api': fields.String(required=True),
            'title': fields.String(required=True),
            'description': fields.String(required=True),
            'author': fields.Nested(ArticleSourceModel.to_model(name_space)),
            'source': fields.Nested(ArticleSourceModel.to_model(name_space)),
            'image_url': fields.String(required=True),
            'published_at': fields.String(required=True),
            'tags': fields.List(fields.String, description="List of tags"),
            'content': fields.String(required=True),
            'url': fields.String(required=False),
            'language': fields.String(required=False),
            'country': fields.String(required=False),
            'current_user_interaction': fields.Nested(ArticleInteractionStatus.to_model(name_space)),
            'total_user_interaction': fields.Nested(ArticleInteractionStats.to_model(name_space)),
        })

    @staticmethod
    def to_model_list(name_space: Namespace):
        return name_space.model('ArticleWithInteractionModelList', {
            'articles': fields.List(fields.Nested(ArticleWithInteractionModel.to_model(name_space)), ),
            'total': fields.Integer,
            'pages': fields.Integer,
            'pageCount': fields.Integer,
        })


