from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel


class MongoDBBaseModel(BaseModel):

    created_at: Optional[datetime] = datetime.now(timezone.utc)
    updated_at: Optional[datetime] = datetime.now(timezone.utc)

    def to_json(self) -> dict:
        return self.model_dump(by_alias=False, exclude_none=True, exclude={"created_at", "updated_at"})

    def to_bson(self) -> dict:
        data = self.model_dump(by_alias=True, exclude_none=True)
        if data.get("_id") is None:
            data.pop("_id", None)
        return data

    def save(self):
        raise NotImplementedError

    def delete(self):
        raise NotImplementedError

    @staticmethod
    def get_list_count():
        raise NotImplementedError

    @classmethod
    def get_list(cls):
        raise NotImplementedError

