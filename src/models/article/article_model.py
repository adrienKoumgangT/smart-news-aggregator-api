import json
from datetime import datetime, timedelta
from threading import Thread
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
from src.models import DataManagerBase, DataBaseModel
from src.models.article.comment_model import CommentManager
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
        ArticleManager.collection().createIndex({ "tags": 1 })
        ArticleManager.collection().createIndex({ "published_at": -1 })
        ArticleManager.collection().create_index([("tags", 1), ("published_at", -1)])

    @staticmethod
    def generate_article_key(article_id: str):
        return f"article:{article_id}"

    @staticmethod
    def generate_article_stats_key(article_id: str):
        return f"article:{article_id}:stats"

    @staticmethod
    def generate_article_count_key(after_date: datetime = None, before_date: datetime = None):
        return f"article:count:{after_date}:{before_date}"


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
            'page': fields.Integer,
            'limit': fields.Integer,
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
    def  to_model_list(name_space: Namespace):
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

    def _scache(self):
        article_key = ArticleManager.generate_article_key(article_id=str(self.article_id))

        api_logger = ApiLogger(f"[REDIS] [ARTICLE] [SCACHE] : {article_key}")

        RedisManagerInstance.get_instance().delete(key=article_key)

        api_logger.print_log()

    def _cache(self):
        article_key = ArticleManager.generate_article_key(article_id=str(self.article_id))

        api_logger = ApiLogger(f"[REDIS] [ARTICLE] [CACHE] : {article_key}")

        article_json = json.dumps(self.to_json())
        RedisManagerInstance.get_instance().set(key=article_key, value=article_json, ex=timedelta(minutes=30))

        api_logger.print_log()

    @classmethod
    def _get(cls, article_id: str):
        article_key = ArticleManager.generate_article_key(article_id=article_id)

        api_logger = ApiLogger(f"[REDIS] [ARTICLE] [GET] : {article_id}")
        article_caching = RedisManagerInstance.get_instance().get(key=article_key)
        if article_caching:
            api_logger.print_log()
            # article_json = json.loads(article_caching, object_hook=my_json_decoder)
            article_json = json.loads(article_caching)
            return cls(**article_json)
        api_logger.print_error(message_error="Cache missing")
        return None

    @classmethod
    def get(cls, article_id: str):
        article = cls._get(article_id)
        if article:
            return article

        api_logger = ApiLogger(f"[MONGODB] [ARTICLE] [GET] : {article_id}")

        result = ArticleManager.collection().find_one({'_id': ObjectId(article_id)})
        if result is None:
            api_logger.print_error("Article does not exist")
            return None
        api_logger.print_log()

        article = cls(**result)

        article._cache()

        return article

    def delete(self):
        api_logger = ApiLogger(f"[MONGODB] [ARTICLE] [DELETE] : {self.article_id}")
        result = ArticleManager.collection().delete_one(
            {"_id": ObjectId(self.article_id)}
        )
        api_logger.print_log(f"Article deleted: {result.deleted_count > 0}")
        return result.deleted_count > 0

    @staticmethod
    def get_all_tags(search: str = None):
        api_logger = ApiLogger(f"[MONGODB] [ARTICLE TAGS] [GET ALL] : search = {search}")
        if search:
            pipeline = [
                {"$unwind": "$tags"},
                {"$match": {"tags": {"$regex": f"^{search}", "$options": "i"}}},
                {"$group": {"_id": None, "matchedTags": {"$addToSet": "$tags"}}},
                {"$project": {"_id": 0, "matchedTags": 1}}
            ]
        else:
            pipeline = [
                {"$unwind": "$tags"},
                {"$group": {"_id": None, "matchedTags": {"$addToSet": "$tags"}}},
                {"$project": {"_id": 0, "matchedTags": 1}}
            ]

        result = list(ArticleManager.collection().aggregate(pipeline))
        tags = result[0]['matchedTags'] if result else []

        api_logger.print_log()
        return tags

    @staticmethod
    def _cache_articles_count(article_count: int, after_date: datetime = None, before_date: datetime = None):
        api_logger = ApiLogger(f"[REDIS] [ARTICLE COUNT] [SET] : after_date = {after_date} and before_date = {before_date}")

        article_count_key = ArticleManager.generate_article_count_key(after_date=after_date, before_date=before_date)

        RedisManagerInstance.get_instance().set(key=article_count_key, value=str(article_count), ex=timedelta(minutes=30))

        api_logger.print_log()

    @staticmethod
    def _get_list_count(after_date: datetime = None, before_date: datetime = None):
        api_logger = ApiLogger(f"[REDIS] [ARTICLE COUNT] [GET] : after_date = {after_date} and before_date = {before_date}")

        article_count_key = ArticleManager.generate_article_count_key(after_date=after_date, before_date=before_date)

        article_count = RedisManagerInstance.get_instance().get(key=article_count_key)

        if article_count:
            api_logger.print_log()
            return int(article_count)
        api_logger.print_error("Cache missing")
        return None

    @staticmethod
    def get_list_count(after_date: datetime = None, before_date: datetime = None):
        total = ArticleModel._get_list_count(after_date=after_date, before_date=before_date)
        if total:
            return total

        api_logger = ApiLogger(f"[MONGODB] [ARTICLE COUNT] [ALL] : after_date = {after_date} and before_date = {before_date}")
        if after_date or before_date:
            match_created_at = ({}
                                | ({'$gt': after_date} if after_date else {})
                                | ({'$lt': before_date} if before_date else {}))
            pipeline = [
                {
                    '$match': {'created_at': match_created_at}
                }, {
                    '$count': 'articles_count'
                }
            ]
            result = ArticleManager.collection().aggregate(pipeline)
            if result:
                stats = list(result)
                print(stats)
                if stats:
                    total = stats[0]['articles_count']
                else:
                    total = 0
            else:
                total = 0
        else:
            # total = ArticleManager.collection().count_documents({})
            total = ArticleManager.collection().estimated_document_count({})
        api_logger.print_log()

        ArticleModel._cache_articles_count(article_count=total, after_date=after_date, before_date=before_date)

        return total if (total and total > 0) else 0

    @classmethod
    def get_list(cls, page: int = 1, limit: int = 10):
        api_logger = ApiLogger(f"[MONGODB] [ARTICLE] [LIST] : page={page} and limit={limit}")

        results = ArticleManager.collection().find(
            filter={},
            skip=limit * (page - 1),
            limit=limit
        )

        api_logger.print_log()

        if results:
            return [cls(**result) for result in results]
        return []

    @staticmethod
    def last_articles_count(preferences: list[str] = None):
        api_logger = ApiLogger(f"[MONGODB] [ARTICLE COUNT] [GET] : preferences={preferences}")
        if preferences:
            filter_search = {
                'tags': {
                    '$in': preferences
                }
            }
        else:
            filter_search = {}
        total = ArticleManager.collection().count_documents(filter_search)
        api_logger.print_log()
        return total if (total and total > 0) else 0


    @classmethod
    def last_articles(cls, preferences: list[str] = None, page: int = 1, limit: int = 10):
        api_logger = ApiLogger(f"[MONGODB] [ARTICLE LATEST] [GET] : page={page}, limit={limit} and preferences={preferences}")
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
            'page': fields.Integer,
            'limit': fields.Integer,
            'pageCount': fields.Integer,
        })


class ArticleTagsModel(DataBaseModel):
    tags: list[str] = []

    @staticmethod
    def to_model(name_space: Namespace):
        return name_space.model('ArticleTagsModel', {
            'tags': fields.List(fields.String, description="List of tags"),
        })


class ArticleUtility:

    @staticmethod
    def _cache_articles(articles: list[ArticleModel]):
        for article in articles:
            _ = ArticleModel.get(article_id=str(article.article_id))

    @staticmethod
    def cache_articles(articles: list[ArticleModel]):
        thread = Thread(target=ArticleUtility._cache_articles, args=(articles,))
        thread.daemon = True
        thread.start()



class ArticleCommentStats(DataBaseModel):
    article_id: str
    extern_api: str
    title: Optional[str]
    published_at: Optional[str]
    source: Optional[ArticleSourceModel] = None
    author: Optional[ArticleSourceModel] = None

    comment_count: int

    @staticmethod
    def to_model(name_space: Namespace):
        return name_space.model('ArticleModel', {
            'article_id': fields.String(required=False),
            'extern_api': fields.String(required=False),
            'title': fields.String(required=False),
            'author': fields.Nested(ArticleSourceModel.to_model(name_space)),
            'source': fields.Nested(ArticleSourceModel.to_model(name_space)),
            'published_at': fields.String(required=False),
            'comment_count': fields.Integer(required=False),
        })

    @classmethod
    def get_stats(cls, article_id: str, comment_id: str = None):
        api_logger = ApiLogger(f"[MONGODB] [ARTICLE] [MOST COMMENT] : article={article_id} and comment={comment_id}")

        pipeline = [
            {
                '$addFields': {
                    'articleObjectId': { '$toObjectId': '$article_id' }
                }
            }, {
                '$group': {
                    '_id': '$articleObjectId',
                    'comment_count': { '$sum': 1 }
                }
            }, {
                '$sort': {
                    'comment_count': -1
                }
            }, {
                '$limit': 10
            }, {
                '$lookup': {
                    'from': 'articles',
                    'localField': '_id',
                    'foreignField': '_id',
                    'as': 'article'
                }
            }, {
                '$unwind': '$article'
            }, {
                '$project': {
                    'article_id': '$_id',
                    'extern_api': '$article.extern_api',
                    'title': '$article.title',
                    'source': '$article.source',
                    'author': '$article.author',
                    'published_at': '$article.published_at',
                    'comment_count': 1,
                    '_id': 0
                }
            }
        ]

        stats = CommentManager.collection().aggregate(pipeline)
        if stats is None:
            api_logger.print_error("Error during retrieving statistics")
            return []
        api_logger.print_log()
        stats_list = list(stats)
        return [cls(**stat) for stat in stats_list]



