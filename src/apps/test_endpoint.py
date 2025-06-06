from flask_restx import Namespace, Resource

from src.lib.exception.exception_server import UnsafeException

ns_test = Namespace('test', description='Test related operations')


@ns_test.route('/error')
class TestErrorResource(Resource):

    def get(self):
        raise UnsafeException("Test Error: GET")

    def post(self):
        raise UnsafeException("Test Error: POST")
