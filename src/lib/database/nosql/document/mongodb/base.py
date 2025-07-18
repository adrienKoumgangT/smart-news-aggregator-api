import json
from datetime import datetime, timezone, timedelta
from typing import Optional

from bson import ObjectId
from flask_restx import Namespace
from pydantic import BaseModel
from pymongo.errors import DuplicateKeyError

from src.lib.database.nosql.document.mongodb.mongodb_manager import MongoDBManager, mongodb_client
from src.lib.database.nosql.document.mongodb.mongodb_monitoring_middleware import MONGO_QUERY_TIME
from src.lib.database.nosql.keyvalue.redis.redis_manager import RedisManagerInstance
from src.lib.log.api_logger import ApiLogger
from src.lib.utility.utils import my_json_decoder, MyJSONEncoder
from src.models.user.auth_model import UserToken


class MongoDBBaseModel(BaseModel):

    created_at: Optional[datetime] = datetime.now(timezone.utc)
    updated_at: Optional[datetime] = datetime.now(timezone.utc)


    @classmethod
    def _name(cls) -> str:
        raise NotImplementedError

    @classmethod
    def _id_name(cls) -> str:
        raise NotImplementedError

    def _data_id(self) -> ObjectId:
        raise NotImplementedError

    @classmethod
    def database_name(cls) -> str:
        return MongoDBManager.database_name()

    @classmethod
    def collection_name(cls) -> str:
        return MongoDBManager.collection_name(cls._name())

    @classmethod
    def collection(cls):
        return mongodb_client[cls.database_name()][cls.collection_name()]

    @classmethod
    def init(cls):
        pass

    @classmethod
    def _exclude_fields_to_json(cls) -> set:
        return {"created_at", "updated_at"}

    def to_json(self) -> dict:
        return self.model_dump(
            by_alias=False,
            exclude_none=False,
            exclude=self._exclude_fields_to_json()
        )

    def to_bson(self) -> dict:
        data = self.model_dump(by_alias=True, exclude_none=True)
        if data.get("_id") is None:
            data.pop("_id", None)
        return data

    def to_update(self) -> dict:
        data = self.model_dump(by_alias=True, exclude_none=True)
        data.pop("_id", None)
        data.pop("created_at", None)
        return data



    @staticmethod
    def to_model(name_space: Namespace):
        raise NotImplementedError

    @staticmethod
    def to_model_list(name_space: Namespace):
        raise NotImplementedError

    @classmethod
    def _cache_key(cls, user_token: UserToken, data_id: str, **kwargs) -> str:
        r = ''
        if len(kwargs) > 0:
            for k, v in kwargs.items():
                r += f":{k}:{v}"
        return f"{cls._name()}:{data_id}{r}"

    def _cache(self, user_token: UserToken, expire: Optional[timedelta] = timedelta(minutes=10), **kwargs):
        key = self._cache_key(user_token, str(self._data_id()), **kwargs)

        api_logger = ApiLogger(f"[REDIS] [{self._name().upper()}] [CACHE] : key={key} and expire={expire}")

        data_json = json.dumps(self, cls=MyJSONEncoder)
        RedisManagerInstance.get_instance().set(key=key, value=data_json, ex=expire)

        api_logger.print_log()

    @classmethod
    def _scache(cls, user_token: UserToken, data_id: str, **kwargs):
        key = cls._cache_key(user_token, data_id, **kwargs)

        api_logger = ApiLogger(f"[REDIS] [{cls._name().upper()}] [SCACHE] : {key}")

        RedisManagerInstance.get_instance().delete(key=key)

        api_logger.print_log()

    @classmethod
    def _get(cls, user_token: UserToken, data_id: str):
        key = cls._cache_key(user_token, data_id)

        api_logger = ApiLogger(f"[REDIS] [{cls._name().upper()}] [GET] : {key}")
        data_caching = RedisManagerInstance.get_instance().get(key=key)
        if data_caching:
            data_json = json.loads(data_caching, object_hook=my_json_decoder)
            data_json['_id'] = ObjectId(data_json[cls._id_name()])
            api_logger.print_log()
            return cls(**data_json)
        api_logger.print_error(message_error="Cache missing")
        return None

    # CRUD OPERATION

    @classmethod
    def get(cls, user_token: UserToken, data_id: str):
        try:
            data = cls._get(user_token, data_id)
            if data:
                return data
        except Exception as e:
            print(e)

        api_logger = ApiLogger(f"[MONGODB] [{cls._name().upper()}] [GET] : {data_id}")

        with MONGO_QUERY_TIME.time():
            result = cls.collection().find_one({"_id": ObjectId(data_id)})

        if result is None:
            api_logger.print_error(f"{cls._name()} not found")
            return None

        api_logger.print_log()

        data = cls(**result)

        data._cache(user_token)

        return data

    def save(self, user_token: UserToken):
        api_logger = ApiLogger(f"[MONGODB] [{self._name().upper()}] [SAVE] : {self.to_json()}")

        try:
            if self._data_id() is None:
                with MONGO_QUERY_TIME.time():
                    result = self.collection().insert_one(self.to_bson())
            else:
                self.updated_at = datetime.now(timezone.utc)
                with MONGO_QUERY_TIME.time():
                    result = self.collection().update_one(
                        {"_id": ObjectId(self._data_id())},
                        {"$set": self.to_update()}
                    )
                self._scache(user_token, str(self._data_id()))
        except DuplicateKeyError:
            api_logger.print_error("Error during save")
            return None
        api_logger.print_log(f"{self._name().upper()} ID: {result.inserted_id}")
        return result.inserted_id

    def delete(self, user_token: UserToken):
        api_logger = ApiLogger(f"[MONGODB] [{self._name().upper()}] [DELETE] : {self._data_id()}")
        with MONGO_QUERY_TIME.time():
            result = self.collection().delete_one({"_id": ObjectId(self._data_id())})
        self._scache(user_token, str(self._data_id()))
        api_logger.print_log(f"{self._name()} deleted: {result.deleted_count > 0}")
        return result.deleted_count > 0

    @classmethod
    def _cache_all_count_key(cls, user_token: UserToken, after_date: datetime = None, before_date: datetime = None):
        return f"{cls._name()}:count:{after_date}:{before_date}"

    @classmethod
    def _get_all_count(cls, user_token: UserToken, after_date: datetime = None, before_date: datetime = None):
        key = cls._cache_all_count_key(user_token, after_date, before_date)

        api_logger = ApiLogger(f"[REDIS] [{cls._name().upper()}] [GET LIST COUNT] : {key}")
        data_caching = RedisManagerInstance.get_instance().get(key=key)
        if data_caching:
            api_logger.print_log()
            return int(data_caching)
        api_logger.print_error(message_error="Cache missing")
        return None

    @classmethod
    def _cache_all_count(cls
                         , user_token: UserToken
                         , total: int
                         , after_date: datetime = None
                         , before_date: datetime = None
                         , expire: Optional[timedelta] = timedelta(minutes=10)
                         ):
        key = cls._cache_all_count_key(user_token, after_date, before_date)

        api_logger = ApiLogger(f"[REDIS] [{cls._name().upper()}] [LIST COUNT] [CACHE] : {key}")

        total_str = str(total)
        RedisManagerInstance.get_instance().set(key=key, value=total_str, ex=expire)

        api_logger.print_log()

    @classmethod
    def _scache_all_count(cls, user_token: UserToken, after_date: datetime = None, before_date: datetime = None):
        key = cls._cache_all_count_key(user_token, after_date, before_date)

        api_logger = ApiLogger(f"[REDIS] [{cls._name().upper()}] [LIST COUNT] [SCACHE] : {key}")

        RedisManagerInstance.get_instance().delete(key=key)

        api_logger.print_log()

    @classmethod
    def get_all_count(cls
                      , user_token: UserToken
                      , extra_match: dict = None
                      , after_date: datetime = None
                      , before_date: datetime = None
                      ):
        if extra_match is None:
            extra_match = {}

        total = cls._get_all_count(user_token, after_date, before_date)
        if total:
            return total

        if after_date or before_date:
            match_created_at = ({}
                                | ({'$gt': after_date} if after_date else {})
                                | ({'$lt': before_date} if before_date else {}))

            pipeline = [
                {
                    '$match': {
                                  'meta_delete': False,
                              } | extra_match | match_created_at
                }, {
                    '$count': 'count'
                }
            ]

            api_logger = ApiLogger(f"[MONGODB] [{cls._name().upper()} COUNT] [GET] : pipline : {pipeline}")

            with MONGO_QUERY_TIME.time():
                result = cls.collection().aggregate(pipeline)

            if result:
                stats = list(result)
                # print(stats)
                if stats:
                    total = stats[0]['count']
                else:
                    total = 0
        else:
            if len(extra_match) > 0:
                api_logger = ApiLogger(f"[MONGODB] [{cls._name().upper()} COUNT] [GET] : filter : {extra_match}")
                with MONGO_QUERY_TIME.time():
                    total = cls.collection().count_documents(filter=extra_match)
            else:
                api_logger = ApiLogger(f"[MONGODB] [{cls._name().upper()} COUNT] [GET] : estimated document count")
                with MONGO_QUERY_TIME.time():
                    total = cls.collection().estimated_document_count({})

        api_logger.print_log()

        cls._cache_all_count(user_token, total, after_date, before_date)
        return total

    @classmethod
    def get_all(cls, user_token: UserToken, extra_match: dict = None, page: int = 1, limit: Optional[int] = 10):
        if extra_match is None:
            extra_match = {}
        query_params = {
                            'filter': extra_match,
                           'sort': [('created_at', -1)]
                       } | ({'skip': limit * (page - 1), 'limit': limit} if limit else {})

        api_logger = ApiLogger(f"[MONGODB] [{cls._name().upper()}] [GET] [LIST] : query={query_params}")

        with MONGO_QUERY_TIME.time():
            results = cls.collection().find(**query_params)

        api_logger.print_log()

        return [cls(**result) for result in results]

    @classmethod
    def get_by(cls, user_token: UserToken, extra_filter: dict = {}, page: int = 1, limit: Optional[int] = 10):

        query_params = {
                           'filter': extra_filter,
                           'sort': [('created_at', -1)]
                       } | ({'skip': limit * (page - 1), 'limit': limit} if limit else {})

        api_logger = ApiLogger(f"[MONGODB] [{cls._name().upper()}] [GET BY] [LIST] : query={query_params}")

        with MONGO_QUERY_TIME.time():
            results = cls.collection().find(**query_params)

        api_logger.print_log()

        return [cls(**result) for result in results]


