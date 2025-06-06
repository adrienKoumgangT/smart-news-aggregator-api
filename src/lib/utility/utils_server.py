from typing import Optional

from flask import Request
from pydantic import BaseModel


class RequestData(BaseModel):
    url: Optional[str]
    method: Optional[str]
    body: Optional[dict] = {}
    args: Optional[dict] = {}
    headers: Optional[dict] = {}
    form: Optional[dict] = {}

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



