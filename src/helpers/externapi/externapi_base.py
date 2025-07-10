import json
import os
from datetime import datetime, timezone
from typing import List, Optional

from bson import ObjectId
from pydantic import Field, BaseModel, field_serializer

from src.lib.configuration import configuration
from src.lib.database.nosql.document.mongodb.base import MongoDBBaseModel
from src.lib.database.nosql.document.mongodb.objectid import PydanticObjectId
from src.lib.log.api_logger import ApiLogger, EnumColor
from src.models.article.article_model import ArticleModel
from src.models.user.auth_model import UserToken


class LogRequestManager:
    database_name = configuration.get_configuration("mongodb.database")
    collection_name = configuration.get_configuration("mongodb.collection.log_requests")

class LogRequestRequest(BaseModel):
    url: str
    headers: Optional[dict]
    params: Optional[dict]


class LogRequestResponse(BaseModel):
    status_code: int
    total_articles: Optional[int]
    returned: Optional[int]
    page: Optional[int]
    data_result: Optional[dict] = None

class LogRequest(MongoDBBaseModel):
    log_request_id: Optional[PydanticObjectId] = Field(None, alias="_id")

    source: str
    url: str
    request: LogRequestRequest
    response: LogRequestResponse
    fetched_count: Optional[int]
    file_result: Optional[str] = None

    @field_serializer("log_request_id")
    def serialize_id(self, id_value: PydanticObjectId, _info):
        return str(id_value) if id_value else None

    @classmethod
    def _name(cls) -> str:
        return "log_request"

    @classmethod
    def _id_name(cls) -> str:
        return "log_request_id"

    def _data_id(self) -> ObjectId:
        return self.log_request_id

    def save(self, user_token: UserToken):
        api_logger = ApiLogger(f"[MONGODB] [LOG REQUEST] [SAVE] save log request {self.source} : {self.url}")

        try:
            result = self.collection().insert_one(self.to_bson())
        except Exception as e:
            api_logger.print_error(message_error=str(e))
            return None
        self.log_request_id = result.inserted_id
        api_logger.print_log()
        return self.log_request_id

    def update_result(self):
        api_logger = ApiLogger(f"[MONGODB] [LOG REQUEST] [UPDATE] [FILE RESULT] save log request {self.log_request_id} : {self.file_result}")

        current_datetime = datetime.now(timezone.utc)

        result = self.collection().update_one(
            {"_id": ObjectId(self.log_request_id)},
            {
                "$set": {
                    "file_result": self.file_result,
                    "data_result": self.data_result,
                    "updated_at": current_datetime
                }
            }
        )

        api_logger.print_log(f"file result updated: {result.modified_count > 0}")
        return {"message": "Password updated"} if result.modified_count else {"error": "Update failed"}



class ExternApiBase:
    api_name = "Extern api"
    base_url = None
    data_field = "data"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    def fetch_news(self) -> List[dict]:
        raise NotImplementedError

    @staticmethod
    def get_dir_path() -> str:
        return os.path.dirname(__file__)

    @classmethod
    def to_article(cls, data: dict) -> ArticleModel:
        raise NotImplementedError

    @staticmethod
    def save_data(data_json: dict, api_name: str, folder_name: str = "data") -> str:
        now = datetime.now()

        year = now.strftime("%Y")
        month = now.strftime("%m")
        day = now.strftime("%d")
        time_str = now.strftime("%H-%M-%S")

        dir_path = os.path.join(os.path.dirname(__file__), folder_name, year, month, day)
        os.makedirs(dir_path, exist_ok=True)

        file_path = os.path.join(dir_path, f"{api_name} {time_str}.json")

        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(data_json, file, indent=4)

        ApiLogger(f"Save data from {api_name} to {file_path}", color=EnumColor.GREEN)

        return file_path

    @staticmethod
    def log_request(
            user_token: UserToken,
            api_name: str,
            url: str,
            headers: dict,
            params: dict,
            status_code:int,
            data: dict,
            total_articles: Optional[int],
            fetched_count: int,
            is_success: bool = True,
    ):

        file_path_result = ExternApiBase.save_data(data_json=data, api_name=api_name) if is_success else None

        log_request = LogRequest(
            _id=None,

            source=api_name,
            url=url,
            request=LogRequestRequest(
                url=url,
                headers=headers,
                params=params
            ),
            response=LogRequestResponse(
                status_code=status_code,
                total_articles=total_articles,
                returned=fetched_count if fetched_count else 0,
                page=None,
                data_result=data
            ),
            fetched_count=fetched_count,

            file_result=file_path_result
        )
        log_request.save(user_token)



