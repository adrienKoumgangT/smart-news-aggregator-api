from typing import Optional

from flask_restx import Namespace, fields
from pydantic import BaseModel


class ArticleSourceModel(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None

    @staticmethod
    def to_model(name_space: Namespace):
        return name_space.model('ArticleSourceModel', {
            'name': fields.String(required=True),
            'url': fields.String(required=True),
        })


