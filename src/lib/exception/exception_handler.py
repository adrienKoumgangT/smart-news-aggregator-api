from flask import request
from flask_restx import Api

from src.lib.exception.exception_server import UnsafeException, UnauthorizedException
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
        return {"error": "unsafe error", "message": "Contact administration"}, 400

    @api.errorhandler(UnauthorizedException)
    def handle_unauthorized_exception(error: UnauthorizedException):
        server_error_log = ServerErrorLogModel.from_request(
            request=request,
            exception_name='UnauthorizedException',
            exception_message=error.message
        )
        server_error_log.save()
        return {"error": "unauthorized error", "message": f"You are not authorized to perform this operation: {error}"}, 403


