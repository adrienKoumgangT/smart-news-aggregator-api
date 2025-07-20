import json
import re
from datetime import datetime, timedelta
from threading import Thread
from typing import Optional, List

from bson import ObjectId
from flask_restx import fields, Namespace
from pydantic import Field, field_serializer, BaseModel

from src.lib.database.nosql.document.mongodb.base import MongoDBBaseModel
from src.lib.database.nosql.document.mongodb.mongodb_monitoring_middleware import MONGO_QUERY_TIME
from src.lib.database.nosql.document.mongodb.objectid import PydanticObjectId
from src.lib.database.nosql.keyvalue.redis.redis_manager import RedisManagerInstance
from src.lib.log.api_logger import ApiLogger
from src.lib.utility.utils import my_json_decoder, MyJSONEncoder
from src.models import DataBaseModel
from src.models.article.article_source_model import ArticleSourceModel
from src.models.article.comment_model import CommentModel
from src.models.article.user_article_interaction_models import ArticleInteractionStatus, ArticleInteractionStats
from src.models.user.auth_model import UserToken


class ArticleSummaryModel(MongoDBBaseModel):
    article_id: Optional[PydanticObjectId] = Field(None, alias="_id")
    extern_id: Optional[str] = None
    extern_api: Optional[str]

    title: str
    description: Optional[str] = None
    author: Optional[ArticleSourceModel] = None
    source: Optional[ArticleSourceModel] = None
    image_url: Optional[str] = None

    published_at: str | datetime

    tags: List[str]

    @field_serializer("article_id")
    def serialize_id(self, id_value: PydanticObjectId, _info):
        return str(id_value) if id_value else None

    @classmethod
    def _name(cls) -> str:
        return "article"

    @classmethod
    def _id_name(cls) -> str:
        return "article_id"

    def _data_id(self) -> ObjectId:
        return self.article_id

    @classmethod
    def init(cls):
        try:
            # cls.collection().create_index([("extern_api", 1), ("extern_id", 1), ("title", 1)], unique=True)
            pass
        except Exception as e:
            print(e)
        try:
            cls.collection().createIndex({"tags": 1})
        except Exception as e:
            print(e)
        try:
            cls.collection().createIndex({"published_at": -1})
        except Exception as e:
            print(e)
        try:
            cls.collection().create_index([("tags", 1), ("published_at", -1)])
        except Exception as e:
            print(e)
        try:
            cls.collection().createIndex({"title": 1})
        except Exception as e:
            print(e)
        try:
            cls.collection().createIndex({"description": 1})
        except Exception as e:
            print(e)
        try:
            """
                    try:
                        cls.collection().create_index(
                            {
                                "title": "text",
                                "description": "text"
                            },
                            {
                                "name": "title_desc_search_index",
                                "weights": {
                                    "title": 3, # Higher relevance for title matches
                                    "description": 2
                                },
                                "default_language": "none"
                            }
                        )
                    except Exception as e:
                        print(e)
                    """

            cls.collection().create_index([("title", 1), ("description", 1)])
        except Exception as e:
            print(e)

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

    def _cache(self, user_token: UserToken, expire: Optional[timedelta] = timedelta(hours=1), **kwargs):
        super()._cache(user_token, expire=expire, **kwargs)

    def save(self, user_token: UserToken):
        article_check = {
                'extern_api': self.extern_api,
                'extern_id': self.extern_id,
                'title': self.title
            }

        api_logger = ApiLogger(f"[MONGODB] [ARTICLE] [CHECK ALREADY EXISTS] : {article_check}")

        article = self.collection().find_one(article_check)
        if article:
            api_logger.print_error("Article already exists")
            return None

        self.article_id = super().save(user_token)
        return self.article_id

    @classmethod
    def _cache_all_tags_key(cls):
        return f"article:tags"

    @classmethod
    def _cache_all_tags(cls, tags: list[str], expire: Optional[timedelta] = timedelta(hours=1)):
        key = cls._cache_all_tags_key()

        api_logger = ApiLogger(f"[REDIS] [ARTICLE TAGS] [CACHE] : key={key} and expire={expire}")

        data_json = json.dumps(tags, cls=MyJSONEncoder)
        RedisManagerInstance.get_instance().set(key=key, value=data_json, ex=expire)

        api_logger.print_log()

    @classmethod
    def _scache_all_tags(cls):
        key = cls._cache_all_tags_key()

        api_logger = ApiLogger(f"[REDIS] [ARTICLE TAGS] [SCACHE] : {key}")

        RedisManagerInstance.get_instance().delete(key=key)

        api_logger.print_log()

    @classmethod
    def _get_all_tags(cls):
        key = cls._cache_all_tags_key()

        api_logger = ApiLogger(f"[REDIS] [ARTICLE TAGS] [GET] : {key}")
        data_caching = RedisManagerInstance.get_instance().get(key=key)
        if data_caching:
            data_json = json.loads(data_caching, object_hook=my_json_decoder)
            api_logger.print_log()
            return data_json
        api_logger.print_error(message_error="Cache missing")
        return None

    @classmethod
    def get_all_tags(cls, user_token, search: str = None):
        tags = cls._get_all_tags()
        if tags:
            return tags

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

        with MONGO_QUERY_TIME.time():
            data = cls.collection().aggregate(pipeline)

        result = list(data)
        tags = result[0]['matchedTags'] if result else []

        api_logger.print_log()

        cls._cache_all_tags(tags)

        return tags

    @classmethod
    def _cache_last_articles_count_key(cls, user_token: UserToken, preferences: list[str] = None):
        if preferences is None or len(preferences) == 0:
            return f"article:last:count"
        return f"article:last:{user_token.user_id}:count"

    @classmethod
    def _last_articles_count(cls, user_token: UserToken, preferences: list[str] = None):
        key = cls._cache_last_articles_count_key(user_token, preferences)

        api_logger = ApiLogger(f"[REDIS] [{cls._name().upper()}] [GET LAST COUNT] : {key}")
        data_caching = RedisManagerInstance.get_instance().get(key=key)
        if data_caching:
            api_logger.print_log()
            return int(data_caching)
        api_logger.print_error(message_error="Cache missing")
        return None

    @classmethod
    def _cache_last_articles_count(cls
                                   , user_token: UserToken
                                   , total: int
                                   , preferences: list[str] = None
                                   , expire: Optional[timedelta] = timedelta(hours=1)
                                   ):
        key = cls._cache_last_articles_count_key(user_token, preferences)

        api_logger = ApiLogger(f"[REDIS] [{cls._name().upper()}] [LAST COUNT] [CACHE] : {key}")

        total_str = str(total)
        RedisManagerInstance.get_instance().set(key=key, value=total_str, ex=expire)

        api_logger.print_log()

    @classmethod
    def scache_last_articles_count(cls, user_token: UserToken, preferences: list[str] = None):
        key = cls._cache_last_articles_count_key(user_token, preferences)

        api_logger = ApiLogger(f"[REDIS] [{cls._name().upper()}] [LAST COUNT] [SCACHE] : {key}")

        RedisManagerInstance.get_instance().delete(key=key)

        api_logger.print_log()

    @classmethod
    def last_articles_count(cls, user_token: UserToken, preferences: list[str] = None):
        total = cls._last_articles_count(user_token, preferences)
        if total:
            return total

        api_logger = ApiLogger(f"[MONGODB] [ARTICLE LASTEST COUNT] [GET] : preferences={preferences}")
        if preferences:
            filter_search = {
                'tags': {
                    '$in': preferences
                }
            }
        else:
            filter_search = {}
        with MONGO_QUERY_TIME.time():
            total = cls.collection().count_documents(filter_search)
        api_logger.print_log()

        total = total if (total and total > 0) else 0

        cls._cache_last_articles_count(user_token, total, preferences)

        return total

    @classmethod
    def _cache_last_articles_key(cls, user_token: UserToken, preferences: list[str] = None, page: int = 1, limit: int = 10):
        if preferences is None or len(preferences) == 0:
            return f"article:last:{page}:{limit}"
        return f"article:last:{user_token.user_id}:{page}:{limit}"

    @classmethod
    def _cache_last_articles_key_pattern(cls, user_token: UserToken, preferences: list[str] = None):
        if preferences is None or len(preferences) == 0:
            return f"article:last:*"
        return f"article:last:{user_token.user_id}:*"

    @classmethod
    def _last_articles(cls, user_token: UserToken, preferences: list[str] = None, page: int = 1, limit: int = 10):
        key = cls._cache_last_articles_key(user_token, preferences, page, limit)

        api_logger = ApiLogger(f"[REDIS] [ARTICLE LATEST] [GET] : page={page}, limit={limit} and preferences={preferences}")
        data_caching = RedisManagerInstance.get_instance().get(key=key)
        if data_caching:
            api_logger.print_log()
            data_list = json.loads(data_caching)
            results = []
            for data_json in data_list:
                # data_json = json.loads(data, object_hook=my_json_decoder)
                data_json['_id'] = ObjectId(data_json[cls._id_name()])
                api_logger.print_log()
                results.append(cls(**data_json))
            return results
        api_logger.print_error(message_error="Cache missing")
        return None

    @classmethod
    def _cache_last_articles(cls
                             , user_token: UserToken
                             , data: list
                             , preferences: list[str] = None
                             , page: int = 1, limit: int = 10
                             , expire: Optional[timedelta] = timedelta(hours=1)
                             ):
        key = cls._cache_last_articles_key(user_token, preferences, page, limit)

        api_logger = ApiLogger(f"[REDIS] [{cls._name().upper()}] [LATEST] [CACHE] : {key}")

        data_json = json.dumps(data, cls=MyJSONEncoder)
        RedisManagerInstance.get_instance().set(key=key, value=data_json, ex=expire)

        api_logger.print_log()

    @classmethod
    def scache_last_articles(cls, user_token: UserToken, preferences: list[str] = None):
        key_pattern = cls._cache_last_articles_key_pattern(user_token, preferences)

        api_logger = ApiLogger(f"[REDIS] [{cls._name().upper()}] [LATEST] [SCACHE] : {key_pattern}")

        RedisManagerInstance.get_instance().delete_pattern(pattern=key_pattern)

        api_logger.print_log()

    @classmethod
    def last_articles(cls, user_token: UserToken, preferences: list[str] = None, page: int = 1, limit: int = 10):
        data_last_cache = cls._last_articles(user_token, preferences, page, limit)
        if data_last_cache:
            return data_last_cache

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

        with MONGO_QUERY_TIME.time():
            results = cls.collection().find(
                filter=filter_search,
                sort=sort,
                skip=limit * (page - 1),
                limit=limit
            )

        api_logger.print_log()

        last_all = [cls(**result) for result in results]

        cls._cache_last_articles(user_token, last_all, preferences, page, limit)

        return last_all

    @classmethod
    def _create_search_query(cls, query):
        # Create case-insensitive regex pattern
        regex_pattern = f'.*{re.escape(query)}.*'
        regex_options = 'i'  # Case-insensitive

        return {
            '$or': [
                {'title': {'$regex': regex_pattern, '$options': regex_options}},
                {'description': {'$regex': regex_pattern, '$options': regex_options}}
            ]
        }

    @classmethod
    def search_articles_count(cls, user_token: UserToken, query: str):
        api_logger = ApiLogger(f"[MONGODB] [ARTICLE COUNT] [GET] : query={query}")

        with MONGO_QUERY_TIME.time():
            total = cls.collection().count_documents(cls._create_search_query(query=query))
        api_logger.print_log()
        return total if (total and total > 0) else 0

    @classmethod
    def search_articles(cls, user_token: UserToken, query: str, page: int = 1, limit: int = 10):
        if not query:
            return cls.last_articles(user_token, page=page, limit=limit)

        api_logger = ApiLogger(f"[MONGODB] [ARTICLE SEARCH] [GET] : query={query}, page={page} and limit={limit}")

        with MONGO_QUERY_TIME.time():
            results = cls.collection().find(cls._create_search_query(query=query)).sort('published_at', -1).skip((page - 1) * limit).limit(limit)

        api_logger.print_log()

        if results:
            return [cls(**result) for result in results]
        return []

    @classmethod
    def _cache_articles(cls, user_token: UserToken, articles: list):
        for article in articles:
            _ = cls.get(user_token, str(article.article_id))

    @classmethod
    def cache_articles(cls, user_token: UserToken, articles: list):
        thread = Thread(target=cls._cache_articles, args=(user_token, articles,))
        thread.daemon = True
        thread.start()


class ArticleSearchModel(DataBaseModel):
    article_id: str
    extern_api: str
    title: Optional[str]
    description: Optional[str]
    published_at: Optional[str]
    source: Optional[ArticleSourceModel] = None
    author: Optional[ArticleSourceModel] = None

    @staticmethod
    def to_model(name_space: Namespace):
        return name_space.model('ArticleSearchModel', {
            'article_id': fields.String(required=False),
            'extern_id': fields.String(required=False),
            'extern_api': fields.String(required=False),
            'title': fields.String(required=True),
            'description': fields.String(required=False),
            'author': fields.Nested(ArticleSourceModel.to_model(name_space)),
            'source': fields.Nested(ArticleSourceModel.to_model(name_space)),
            'published_at': fields.String(required=True),
        })

    @staticmethod
    def to_model_list(name_space: Namespace):
        return name_space.model('ArticleSearchModelList', {
            'articles': fields.List(fields.Nested(ArticleWithInteractionModel.to_model(name_space)), ),
            'total': fields.Integer,
            'page': fields.Integer,
            'limit': fields.Integer,
            'pageCount': fields.Integer,
        })

    @classmethod
    def _cache_search_articles_key(cls, user_token: UserToken, query: str, page: int = 1, limit: int = 10):
        return f"article:search:{query}:{page}:{limit}"

    @classmethod
    def _cache_search_articles(cls, user_token: UserToken, articles: list, query: str, page: int = 1, limit: int = 10):
        key = cls._cache_search_articles_key(user_token, query, page, limit)

        api_logger = ApiLogger(f"[REDIS] [ARTICLE] [SEARCH] [CACHE] : {key}")

    @classmethod
    def search_articles(cls, user_token: UserToken, query: str, page: int = 1, limit: int = 10):
        if not query:
            return ArticleModel.last_articles(user_token, page=page, limit=limit)

        api_logger = ApiLogger(f"[MONGODB] [ARTICLE] [SEARCH] [GET] : query={query}, page={page} and limit={limit}")

        pipeline = [
            {
                "$match": {
                    "$text": {
                        "$search": query,
                        # "$language": "english"
                    }
                }
            },
            {
                "$project": {
                    'article_id': '$_id',
                    'extern_api': 1,
                    'extern_id': 1,
                    "title": 1,
                    "description": 1,
                    'source': 1,
                    'author': 1,
                    "score": {"$meta": "textScore"},
                    "published_at": 1
                }
            },
            {
                "$sort": {"score": -1, "published_at": -1}  # Relevance + recency
            },
            {
                "$skip": (page - 1) * limit
            },
            {
                "$limit": limit
            }
        ]

        with MONGO_QUERY_TIME.time():
            results = ArticleModel.collection().aggregate(pipeline)

        if results is None:
            api_logger.print_error("Error occurred during article search")
            return []

        api_logger.print_log()
        return [cls(**result) for result in list(results)]


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
    def _cache_key_stats(cls, article_id: str, comment_id: str = None):
        if comment_id is None:
            return f"article:{article_id}:comment:stats"
        return f"article:{article_id}:comment:{comment_id}:stats"

    @classmethod
    def _cache(cls, stats_list, article_id: str, comment_id: str = None, expire: Optional[timedelta] = timedelta(minutes=10), **kwargs):
        key = cls._cache_key_stats(article_id, comment_id)

        api_logger = ApiLogger(f"[REDIS] [ARTICLE] [MOST COMMENT] [SET] : key={key} and expire={expire}")

        data_json = json.dumps(stats_list, cls=MyJSONEncoder)
        RedisManagerInstance.get_instance().set(key=key, value=data_json, ex=expire)

        api_logger.print_log()

    @classmethod
    def _get_stats(cls, article_id: str, comment_id: str = None):
        key = cls._cache_key_stats(article_id, comment_id)
        api_logger = ApiLogger(f"[REDIS] [ARTICLE] [MOST COMMENT] [GET] : {key}")
        data_caching = RedisManagerInstance.get_instance().get(key=key)
        if data_caching:
            data_json = json.loads(data_caching, object_hook=my_json_decoder)
            api_logger.print_log()
            return cls(**data_json)
        api_logger.print_error(message_error="Cache missing")
        return None

    @classmethod
    def get_stats(cls, article_id: str, comment_id: str = None):
        stats_list = cls._get_stats(article_id, comment_id)
        if stats_list is not None:
            return stats_list

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

        with MONGO_QUERY_TIME.time():
            stats = CommentModel.collection().aggregate(pipeline)
        if stats is None:
            api_logger.print_error("Error during retrieving statistics")
            return []
        api_logger.print_log()
        stats_list = [cls(**stat) for stat in list(stats)]

        cls._cache(stats_list, article_id, comment_id)

        return stats_list



