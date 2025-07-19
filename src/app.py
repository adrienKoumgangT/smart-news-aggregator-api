import ipaddress

from flask import Flask, Blueprint, render_template_string, request, abort, Response
from flask_cors import CORS
from flask_restx import Api
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from src.apps.admin_endpoint import ns_admin
from src.apps.article_endpoint import ns_article
from src.apps.auth_endpoint import ns_auth
from src.apps.metric_endpoint import ns_metrics
from src.apps.test_endpoint import ns_test
from src.apps.user_endpoint import ns_user
from src.lib.configuration.configuration import get_env_var, config
from src.lib.exception.exception_handler import register_error_handlers
from src.lib.utility.utils_server import RequestUtility

ALLOWED_NETWORKS = config.swagger_allowed_hosts


def create_app():
    app = Flask(__name__)

    app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024 # 100MB
    app.config["DEBUG"] = get_env_var("DEBUG", default=False, var_type=bool)

    CORS(
        app,
        resources={r"/*": {"origins": "*"}},
        supports_credentials=True,
        methods=["GET", "POST", "PUT", "PATCH", "HEAD", "PUT", "DELETE", "OPTIONS"],
        allow_headers=[
            'Content-Type',
            'Access-Control-Allow-Origin',
            'X-Requested-With',
            'Accept',
            'Origin',
            'Access-Control-Request-method',
            'Access-Control-Request-Headers',
            'Authorization',
            'App-Alert',
            'X-Total-Count',
            'File',
            'Filename',
            'X-File-Name',
            'Cache-Control'
        ],
        expose_headers=[
            'Access-Control-Allow-Origin',
            'Access-Control-Allow-Credentials',
            'Authorization',
            'app-alert',
            'app-alert-type',
            'X-Total-Count',
            'Filename'
        ]
    )

    """
    with app.app_context():
        MongoDBManagerInstance.init_database()

    @app.teardown_appcontext
    def close_db(exception=None):
        MongoDBManagerInstance.shutdown()
    """


    @app.before_request
    def restrict_swagger_access():
        RequestUtility.print_info_request(request)
        if request.path.startswith("/docs") or request.path.startswith("/swagger"):
            # print(f"swagger is allowed: {config.swagger_allowed}")
            if not config.swagger_allowed:
                allowed_networks = [ipaddress.ip_network(network) for network in ALLOWED_NETWORKS]
                # print(f"allowed networks: {ALLOWED_NETWORKS}")
                # print(f"is prod: {config.prod}")
                client_ip = ipaddress.ip_address(request.remote_addr)
                # print(f"client ip: {client_ip}")
                if not any(client_ip in net for net in allowed_networks):
                    abort(403)


    @app.route("/")
    def index():
        return render_template_string("""
            <html>
            <head>
                <title>Smart News Aggregator</title>
                <style>
                    body { font-family: sans-serif; margin: 5em; background: #f4f4f4; }
                    .container { background: white; padding: 2em; border-radius: 8px; max-width: 600px; }
                    h1 { color: #2b3e50; }
                    a.button {
                        display: inline-block;
                        padding: 10px 20px;
                        background: #007BFF;
                        color: white;
                        text-decoration: none;
                        border-radius: 5px;
                        margin-top: 1em;
                    }
                    a.button:hover { background: #0056b3; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Welcome to Smart News Aggregator API</h1>
                    <p>This platform provides intelligent news aggregation, personalization, and recommendation features powered by Flask, MongoDB, Redis, and JWT-secured endpoints.</p>
                    <a class="button" href="/api/docs">Go to Swagger</a>
                </div>
            </body>
            </html>
        """)

    authorizations = {
        'BearerAuth': {
            'type': 'apiKey',
            'in': 'header',
            'name': 'Authorization',
            'description': "JWT token with format: **Bearer &lt;token&gt;**"
        }
    }

    @app.route("/metrics")
    def metrics():
        return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

    blueprint = Blueprint('api', __name__, url_prefix='/api')
    api = Api(
        blueprint,
        title="Smart News Aggregator API",
        description="Articles from extern api",
        version="1.0",
        doc='/docs/',
        authorizations=authorizations,
        security="BearerAuth"  # Apply to all routes unless overridden
    )

    api.add_namespace(ns_metrics, path='/metrics')

    api.add_namespace(ns_admin, path='/admin')

    api.add_namespace(ns_auth, path='/auth')
    api.add_namespace(ns_user, path='/user')
    api.add_namespace(ns_article, path='/article')

    api.add_namespace(ns_test, path='/test')

    register_error_handlers(api)

    app.register_blueprint(blueprint)

    return app

application = create_app()

if __name__ == "__main__":
    application.run(host='0.0.0.0', port=5000, debug=True)
