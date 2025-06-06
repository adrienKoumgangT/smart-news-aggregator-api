from typing import Optional

from pydantic import Field

from src.lib.database.nosql.document.mongodb.base import MongoDBBaseModel
from src.lib.database.nosql.document.mongodb.objectid import PydanticObjectId


class CommentModel(MongoDBBaseModel):
    comment_id: Optional[PydanticObjectId] = Field(None, alias="_id")

    user_id: str
    article_id: str
    comment_fk: Optional[str] = None
    content: str

