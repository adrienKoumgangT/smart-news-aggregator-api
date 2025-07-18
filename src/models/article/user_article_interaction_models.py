from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional, Literal

from bson import ObjectId
from flask_restx import Namespace, fields
from pydantic import Field, field_serializer
from pymongo.errors import DuplicateKeyError

from src.lib.database.nosql.document.mongodb.base import MongoDBBaseModel
from src.lib.database.nosql.document.mongodb.mongodb_monitoring_middleware import MONGO_QUERY_TIME
from src.lib.database.nosql.document.mongodb.objectid import PydanticObjectId
from src.lib.log.api_logger import ApiLogger
from src.models import DataBaseModel
from src.models.user.auth_model import UserToken
from src.models.user.user_model import UserAuthor


class ArticleInteractionType(DataBaseModel):
    type: str
    value: bool

    @staticmethod
    def to_model(name_space: Namespace):
        return name_space.model('ArticleInteractionType', {
            'type': fields.String(required=True),
            'value': fields.Boolean(required=True),
        })


LEVEL_INTERACTION = Literal["article", "comment"]

class UserArticleInteractionModel(MongoDBBaseModel):
    interaction_id: Optional[PydanticObjectId] = Field(None, alias="_id")

    level_interaction: str

    user_id: str
    article_id: str
    comment_id: Optional[str] = None

    article_title: Optional[str] = None

    read_at: datetime = datetime.now()
    time_spent: Optional[int] = Field(default=None, ge=0)
    liked: Optional[bool] = False
    shared: Optional[bool] = False
    saved: Optional[bool] = False
    report: Optional[bool] = False

    @field_serializer("interaction_id")
    def serialize_id(self, id_value: PydanticObjectId, _info):
        return str(id_value) if id_value else None

    @classmethod
    def _name(cls) -> str:
        return "interaction"

    @classmethod
    def _id_name(cls) -> str:
        return "interaction_id"

    def _data_id(self) -> ObjectId:
        return self.interaction_id

    @staticmethod
    def to_model(name_space: Namespace):
        return name_space.model('UserArticleInteractionModel', {
            'interaction_id': fields.String(required=True),
            'level_interaction': fields.String(required=True),
            'user_id': fields.String(required=True),
            'article_id': fields.String(required=True),
            'comment_id': fields.String(required=False),
            'article_title': fields.String(required=False),
            'read_at': fields.DateTime(required=False),
            'time_spent': fields.Integer(required=False),
            'liked': fields.Boolean(required=False),
            'shared': fields.Boolean(required=False),
            'saved': fields.Boolean(required=False),
            'report': fields.Boolean(required=False),
        })

    @staticmethod
    def to_model_list(name_space: Namespace):
        return name_space.model('UserArticleInteractionModelList', {
            'interactions': fields.List(fields.Nested(UserArticleInteractionModel.to_model(name_space))),
            'total': fields.Integer,
            'page': fields.Integer,
            'limit': fields.Integer,
            'pageCount': fields.Integer,
        })

    def update(self, interaction: UserArticleInteraction | ArticleInteractionType):
        if isinstance(interaction, UserArticleInteraction):
            if not interaction.liked is None:
                self.liked = interaction.liked
            if not interaction.shared is None:
                self.shared = interaction.shared
            if not interaction.saved is None:
                self.saved = interaction.saved
            if not interaction.report is None:
                self.report = interaction.report
        else:
            if not interaction.value is None:
                if interaction.type == 'liked':
                    self.liked = interaction.value
                elif interaction.type == 'shared':
                    self.shared = interaction.value
                elif interaction.type == 'saved':
                    self.saved = interaction.value
                elif interaction.type == 'report':
                    self.report = interaction.value

    @classmethod
    def _cache_key(cls, user_token: UserToken, data_id: str, **kwargs) -> str:
        article_id = kwargs.get("article_id")
        comment_id = kwargs.get("comment_id")
        if comment_id:
            return f"user:{user_token.user_id}:article:{article_id}:comment:{comment_id}"
        return f"user:{user_token.user_id}:article:{article_id}"

    def save(self, user_token: UserToken):
        api_logger = ApiLogger(f"[MONGODB] [USER ARTICLE INTERACTION] [SAVE] : {self.to_json()}")
        try:
            # print(f"article title : {self.article_title}")
            if self.article_title is None:
                from src.lib.exception.exception_server import NotFoundException
                from src.models.article.article_model import ArticleModel

                article = ArticleModel.get(user_token, self.article_id)
                if article is None:
                    raise NotFoundException("Article not found")
                self.article_title = article.title
                # print(f"article title after update: {self.article_title}")

            if self.interaction_id:
                data = self.to_json()
                del data["interaction_id"]
                with MONGO_QUERY_TIME.time():
                    result = self.collection().update_one(
                        {"_id": ObjectId(self.interaction_id)},
                        {"$set": data}
                    )
            else:
                with MONGO_QUERY_TIME.time():
                    result = self.collection().insert_one(self.to_bson())
        except DuplicateKeyError:
            api_logger.print_error("User already exists")
            return None
        if self.interaction_id is None:
            self.interaction_id = result.inserted_id
        api_logger.print_log(f"Interaction ID: {self.interaction_id}")
        return self.interaction_id

    @classmethod
    def update_interaction_read(cls, user_token: UserToken, article_id: str, article_title: str, comment_id: str = None):
        api_logger = ApiLogger(f"[MONGODB] [USER ARTICLE INTERACTION] [UPDATE] : user={user_token.user_id}, article={article_id} and comment={comment_id}")
        filter_key = {"user_id": user_token.user_id, "article_id": article_id}
        filter_key |= {"comment_id": comment_id} if comment_id else {}
        datetime_operation = datetime.now(timezone.utc)
        data_on_insert = {
            "level_interaction": "comment" if comment_id else "article",
            "article_title": article_title,
            "liked": False,
            "shared": False,
            "saved": False
        }
        with MONGO_QUERY_TIME.time():
            result = cls.collection().update_one(
                filter=filter_key,
                update={
                    "$set": {
                        "read_at": datetime_operation,
                        "updated_at": datetime_operation
                    },
                    "$setOnInsert": data_on_insert,
                    "$inc": {
                        "time_spent": 1  # increment by 1 time
                    }
                },
                upsert=True
            )
        cls._scache(user_token, article_id)
        api_logger.print_log(f"Update result: {result.modified_count > 0}")

    @classmethod
    def update_interaction(cls, user_token: UserToken, interaction: UserArticleInteraction | ArticleInteractionType, article_id: str, comment_id: str = None):
        api_logger = ApiLogger(f"[MONGODB] [USER ARTICLE INTERACTION] [UPDATE] : user={user_token.user_id}, article={article_id}, comment={comment_id} and interaction={interaction}")
        filter_key = {"user_id": user_token.user_id, "article_id": article_id}
        filter_key |= {"comment_id": comment_id} if comment_id else {}

        preview_interaction = cls.get_by_user_article(user_id=user_token.user_id, article_id=article_id, comment_id=comment_id)
        if preview_interaction is None:
            level_interaction = "comment" if comment_id else "article"
            preview_interaction = cls(_id=None, level_interaction=level_interaction, user_id=user_token.user_id, article_id=article_id, comment_id=comment_id)
        preview_interaction.update(interaction)
        b = preview_interaction.save(user_token)

        api_logger.print_log()

        return not b is None

    @classmethod
    def get_by_user_article(cls, user_id: str, article_id: str, comment_id: str = None):
        api_logger = ApiLogger(f"[MONGODB] [USER ARTICLE INTERACTION] [GET] [BY USER ARTICLE] : user={user_id}, article={article_id} and comment={comment_id}")
        with MONGO_QUERY_TIME.time():
            interaction = cls.collection().find_one(
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
    def get_stats(cls, article_id: str, comment_id: str = None):
        api_logger = ApiLogger(f"[MONGODB] [USER ARTICLE INTERACTION] [GET STAT] : article={article_id} and comment={comment_id}")

        match = {"article_id": article_id} | ({"comment_id": comment_id} if comment_id else {})
        pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": "$article_id",
                    "liked": {"$sum": {"$cond": ["$liked", 1, 0]}},
                    "saved": {"$sum": {"$cond": ["$saved", 1, 0]}},
                    "shared": {"$sum": {"$cond": ["$shared", 1, 0]}},
                    "report": {"$sum": {"$cond": ["$report", 1, 0]}}
                }
            }
        ]

        with MONGO_QUERY_TIME.time():
            stats = cls.collection().aggregate(pipeline)
        if stats is None:
            api_logger.print_error("Error during retrieving statistics")
            return ArticleInteractionStats()
        api_logger.print_log()
        stats_list = list(stats)
        if stats_list:
            return ArticleInteractionStats(
                liked=stats_list[0]["liked"],
                saved=stats_list[0]["saved"],
                shared=stats_list[0]["shared"],
                report=stats_list[0]["report"],
            )
        return ArticleInteractionStats()

    @classmethod
    def read_history_count(cls, user_id: str):
        api_logger = ApiLogger(f"[MONGODB] [USER ARTICLE INTERACTION] [GET] [HISTORY] : user={user_id}")
        with MONGO_QUERY_TIME.time():
            total =  cls.collection().count_documents({"user_id": user_id, "read_at": {"$exists": True}})
        api_logger.print_log()
        return total if (total and total > 0) else 0

    @classmethod
    def get_read_history(cls, user_id: str, page: int = 1, limit: int = 5):
        api_logger = ApiLogger(f"[MONGODB] [USER ARTICLE INTERACTION] [GET] [HISTORY] : user={user_id}, page={page} and limit={limit}")

        with MONGO_QUERY_TIME.time():
            result = cls.collection().find(
                {"user_id": user_id, "read_at": {"$exists": True}},
                # {"_id": 0, "article_id": 1, "read_at": 1, "time_spent": 1}
            ).sort("read_at", -1).skip(limit * (page-1)).limit(limit)

        if result:
            api_logger.print_log()
            histories = [cls(**history) for history in result]
            return histories
        api_logger.print_error(message_error=f"User Article Interaction does not exist")
        return []


class UserArticleInteraction(DataBaseModel):

    time_spent: Optional[int] = Field(default=None, ge=0)
    liked: Optional[bool] = False
    shared: Optional[bool] = False
    saved: Optional[bool] = False
    report: Optional[bool] = False

    author: Optional[UserAuthor]

    @staticmethod
    def to_model(name_space: Namespace):
        return name_space.model('UserArticleInteraction', {
            'time_spent': fields.Integer(required=False),
            'liked': fields.Boolean(required=False),
            'shared': fields.Boolean(required=False),
            'saved': fields.Boolean(required=False),
            'report': fields.Boolean(required=False),
            'author': fields.Nested(UserAuthor.to_model(name_space=name_space), required=False),
        })


class ArticleInteractionStatus(DataBaseModel):
    liked: Optional[bool] = False
    shared: Optional[bool] = False
    saved: Optional[bool] = False
    report: Optional[bool] = False

    @staticmethod
    def to_model(name_space: Namespace):
        return name_space.model('ArticleInteractionStatus', {
            'liked': fields.Boolean(required=False),
            'shared': fields.Boolean(required=False),
            'saved': fields.Boolean(required=False),
            'report': fields.Boolean(required=False),
        })

    @classmethod
    def from_interaction(cls, interaction: UserArticleInteractionModel):
        return cls(
            liked=interaction.liked,
            shared=interaction.shared,
            saved=interaction.saved,
            report=interaction.report,
        )


class ArticleInteractionStats(DataBaseModel):
    liked: Optional[int] = 0
    shared: Optional[int] = 0
    saved: Optional[int] = 0
    report: Optional[int] = 0

    @staticmethod
    def to_model(name_space: Namespace):
        return name_space.model('ArticleInteractionStats', {
            'liked': fields.Integer(required=False),
            'shared': fields.Integer(required=False),
            'saved': fields.Integer(required=False),
            'report': fields.Integer(required=False),
        })


class ArticleInteractionDashboard(DataBaseModel):
    read_count: int = 0
    like_count: int = 0
    save_count: int = 0
    share_count: int = 0
    total_interactions: int = 0

    article_id: str
    extern_api: str
    title: str
    published_at: str
    author: dict
    source: dict

    @staticmethod
    def to_model(name_space: Namespace):
        from src.models.article.article_model import ArticleSourceModel

        return name_space.model('ArticleInteractionDashboard', {
            'read_count': fields.Integer(required=False),
            'like_count': fields.Integer(required=False),
            'save_count': fields.Integer(required=False),
            'share_count': fields.Integer(required=False),
            'total_interactions': fields.Integer(required=False),
            'article_id': fields.String(required=False),
            'extern_api': fields.String(required=False),
            'title': fields.String(required=False),
            'published_at': fields.String(required=False),
            'author': fields.Nested(ArticleSourceModel.to_model(name_space), required=False),
            'source': fields.Nested(ArticleSourceModel.to_model(name_space), required=False),
        })

    @staticmethod
    def to_model_list(name_space: Namespace):
        return name_space.model('ArticleInteractionDashboardList', {
            'stats': fields.List(fields.Nested(ArticleInteractionDashboard.to_model(name_space))),
        })

    @classmethod
    def get_most_interacted_articles(cls, date_check = None):
        api_logger = ApiLogger(f"[MONGODB] [USER ARTICLE INTERACTION] [DASHBOARD] [MOST INTERACTED ARTICLES] ")

        if date_check:
            pipeline = [
                {
                    '$match': {
                        'updated_at': {'$gte': date_check}
                    }
                }, {
                    '$addFields': {
                        'articleObjectId': {'$toObjectId': '$article_id'}
                    }
                }, {
                    '$group': {
                        '_id': '$articleObjectId',
                        'read_count': {'$sum': {'$cond': [{'$ifNull': ['$read_at', False]}, 1, 0]}},
                        'like_count': {'$sum': {'$cond': ['$liked', 1, 0]}},
                        'save_count': {'$sum': {'$cond': ['$saved', 1, 0]}},
                        'share_count': {'$sum': {'$cond': ['$shared', 1, 0]}}
                    }
                }, {
                    '$addFields': {
                        'total_interactions': {
                            '$add': ['$read_count', '$like_count', '$save_count', '$share_count']
                        }
                    }
                }, {
                    '$sort': {
                        'total_interactions': -1
                    }
                }, {
                    '$limit': 5
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
                        'published_at': '$article.published_at',
                        'author': '$article.author',
                        'source': '$article.source',
                        'total_interactions': 1,
                        'read_count': 1,
                        'like_count': 1,
                        'save_count': 1,
                        'share_count': 1,
                        '_id': 0
                    }
                }
            ]
        else:
            pipeline = [
                {
                    '$addFields': {
                        'articleObjectId': {'$toObjectId': '$article_id'}
                    }
                }, {
                    '$group': {
                        '_id': '$articleObjectId',
                        'read_count': {'$sum': {'$cond': [{'$ifNull': ['$read_at', False]}, 1, 0]}},
                        'like_count': {'$sum': {'$cond': ['$liked', 1, 0]}},
                        'save_count': {'$sum': {'$cond': ['$saved', 1, 0]}},
                        'share_count': {'$sum': {'$cond': ['$shared', 1, 0]}}
                    }
                }, {
                    '$addFields': {
                        'total_interactions': {'$add': ['$read_count', '$like_count', '$save_count', '$share_count']}
                    }
                }, {
                    '$sort': {
                        'total_interactions': -1
                    }
                }, {
                    '$limit': 5
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
                        'published_at': '$article.published_at',
                        'author': '$article.author',
                        'source': '$article.source',
                        'total_interactions': 1,
                        'read_count': 1,
                        'like_count': 1,
                        'save_count': 1,
                        'share_count': 1,
                        '_id': 0
                    }
                }
            ]

        with MONGO_QUERY_TIME.time():
            stats = UserArticleInteractionModel.collection().aggregate(pipeline)
        if stats is None:
            api_logger.print_error("Error during retrieving statistics")

        stat_list = list(stats)
        api_logger.print_log()
        # print(stat_list)

        for stat in stat_list:
            stat['article_id'] = str(stat['article_id'])

        return [cls(**data) for data in stat_list]



