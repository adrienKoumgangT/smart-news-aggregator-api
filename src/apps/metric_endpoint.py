from flask import Response
from flask_restx import Namespace, Resource
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST


ns_metrics = Namespace('metrics', description='Metrics endpoint')


@ns_metrics.route('/')
class MetricsEndpoint(Resource):

    def get(self):
        return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

