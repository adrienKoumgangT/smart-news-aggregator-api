from flask import Flask, Blueprint, render_template_string, request, Response
from flask_cors import CORS
from flask_restx import Api

from src.apps.article_endpoint import ns_article
from src.apps.auth_endpoint import ns_auth
from src.apps.test_endpoint import ns_test
from src.apps.user_endpoint import ns_user
from src.lib.exception.exception_handler import register_error_handlers


def create_app():
    app = Flask(__name__)

    app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024 # 100MB

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

    api.add_namespace(ns_auth, path='/auth')
    api.add_namespace(ns_user, path='/user')
    api.add_namespace(ns_article, path='/article')

    api.add_namespace(ns_test, path='/test')

    register_error_handlers(api)

    app.register_blueprint(blueprint)

    return app


if __name__ == "__main__":
    application = create_app()

    application.run(host='0.0.0.0', port=5000, debug=True)
