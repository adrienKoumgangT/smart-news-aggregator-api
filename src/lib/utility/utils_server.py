from typing import Optional

from flask import Request
from flask_restx import Namespace, fields

from src.lib.log.api_logger import ApiLogger, EnumColor
from src.models import DataBaseModel


class RequestData(DataBaseModel):
    url: Optional[str]
    method: Optional[str]
    body: Optional[dict] = {}
    args: Optional[dict] = {}
    headers: Optional[dict] = {}
    form: Optional[dict] = {}

    @staticmethod
    def to_model(name_space: Namespace):
        return name_space.model('UserMePreferencesModel', {
            'url': fields.String(required=False),
            'method': fields.String(required=False),
            'body': fields.Raw(required=False),
            'args': fields.Raw(required=False),
            'headers': fields.Raw(required=False),
            'form': fields.Raw(required=False),
        })

    @classmethod
    def from_request(cls, request: Request):
        url = request.url
        method = request.method
        args_data = {k: v for k, v in request.args.items()}
        headers_data = {key: value for key, value in request.headers}
        form_data = request.form.copy().to_dict()
        data = request.get_json() if request.is_json else {}

        return cls(
            url=url,
            method=method,
            body=data,
            args=args_data,
            headers=headers_data,
            form=form_data,
        )

class RequestUtility:

    @classmethod
    def print_info_request(cls, request: Request):
        request_data = RequestData.from_request(request=request)

        ApiLogger(f"[HTTP REQUEST] [{request_data.method}] {request_data.url} {request_data.body if request_data.body else ''}", color=EnumColor.CYAN)

