from datetime import timedelta

from flask import jsonify, request
from flask_restx import Namespace, Resource

from src.lib.configuration.configuration import config_manager, config
from src.lib.database.nosql.document.mongodb.mongodb_manager import mongodb_client
from src.lib.database.nosql.keyvalue.redis.redis_manager import RedisManagerInstance
from src.lib.exception.exception_server import UnsafeException

ns_test = Namespace('test', description='Test related operations')


@ns_test.route('/error')
class TestErrorResource(Resource):

    def get(self):
        raise UnsafeException("Test Error: GET")

    def post(self):
        raise UnsafeException("Test Error: POST")


@ns_test.route('/data')
class TestDataResource(Resource):

    def get(self):
        return jsonify({"message": "Get Service"})

    def post(self):
        data = request.get_json()

        return jsonify({"data": data})


@ns_test.route('/test-redis')
class TestRedisResource(Resource):

    def get(self):
        try:
            RedisManagerInstance.get_instance().set("ping", "pong", timedelta(minutes=10))
            return jsonify({"message": RedisManagerInstance.get_instance().get("ping")})
        except Exception as e:
            return jsonify({"error": str(e)})


@ns_test.route('/test-mongo')
class TestMongoResource(Resource):

    def get(self):
        try:
            list_db = mongodb_client.list_database_names()
            return jsonify({"message": list_db})
        except Exception as e:
            return jsonify({"error": str(e)})


@ns_test.route('/test-reload-config')
class TestReloadConfigResource(Resource):

    def get(self):
        config_manager.reload()

        return jsonify(config)


