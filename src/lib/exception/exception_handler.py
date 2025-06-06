from flask import request
from flask_restx import Api

from src.lib.exception.exception_server import UnsafeException
from src.models.server.server_model import ServerErrorLogModel


def register_error_handlers(api: Api):

    @api.errorhandler(UnsafeException)
    def handle_unsafe_exception(error: UnsafeException):
        server_error_log = ServerErrorLogModel.from_request(
            request=request,
            exception_name='UnsafeException',
            exception_message=error.message
        )
        server_error_log.save()
        return {"error": "unsafe error"}, 400

