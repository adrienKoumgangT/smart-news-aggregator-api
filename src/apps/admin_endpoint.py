import datetime

from flask import g, request, jsonify
from flask_restx import Namespace, Resource, fields, Api

from src.apps import token_required
from src.lib.configuration.configuration import config_manager
from src.lib.exception.exception_server import NotFoundException
from src.models.article.article_model import ArticleModel
from src.models.article.comment_model import CommentModel
from src.models.article.user_article_interaction_models import ArticleInteractionDashboard, UserArticleInteractionModel
from src.models.model import Model
from src.models.server.server_model import ServerErrorLogModel
from src.models.user.auth_model import UserToken
from src.models.user.user_model import User, UserMe, UserPreferencesDashboard

ns_admin = Namespace("admin", description="Administration endpoint")


# Manages Articles

@ns_admin.route('/articles')
@ns_admin.param('page', 'Page')
@ns_admin.param('limit', 'Number of articles to return')
class AdminArticles(Resource):

    @token_required
    @ns_admin.marshal_with(ArticleModel.to_model_list(name_space=ns_admin), code=200)
    def get(self):
        page_arg = request.args.get('page', default=1, type=int)
        limit_arg = request.args.get('limit', default=10, type=int)

        page = page_arg if page_arg > 0 else 1
        limit = limit_arg if limit_arg > 0 else 10

        user_token: UserToken = g.user

        total = ArticleModel.get_list_count()
        articles = ArticleModel.get_list(page=page, limit=limit)

        ArticleModel.cache_articles(user_token, articles=articles)

        return {
            "articles": [article.to_summary() for article in articles],
            "total": total,
            "page": page,
            "limit": limit,
            "pageCount": len(articles),
        }


@ns_admin.route('/article/<string:article_id>')
@ns_admin.param('article_id', 'The article ID')
class AdminArticle(Resource):

    @token_required
    @ns_admin.marshal_with(ArticleModel.to_model(name_space=ns_admin), code=200)
    def get(self, article_id):
        user_token: UserToken = g.user

        article = ArticleModel.get(user_token, article_id)

        if not article:
            raise NotFoundException("Article not found")

        return article.to_json()

    @token_required
    @ns_admin.marshal_with(Model.get_message_response_model(name_space=ns_admin), code=200)
    def delete(self, article_id):
        user_token: UserToken = g.user

        article = ArticleModel.get(user_token, article_id)

        if not article:
            raise NotFoundException("Article not found")

        article.delete()

        return {"success": True, "message": "Article deleted"}


# Manages Users

@ns_admin.route('/users')
@ns_admin.param('page', 'Page')
@ns_admin.param('limit', 'Number of users to return')
class AdminUsers(Resource):

    @token_required
    @ns_admin.marshal_with(UserMe.to_model_list(name_space=ns_admin), code=200)
    def get(self):
        page_arg = request.args.get('page', default=1, type=int)
        limit_arg = request.args.get('limit', default=10, type=int)

        page = page_arg if page_arg > 0 else 1
        limit = limit_arg if limit_arg > 0 else 10

        user_token: UserToken = g.user

        total = User.get_list_count()
        users = User.get_all(user_token, page=page, limit=limit)

        users_me = [user.to_me() for user in users]
        print(users_me)
        return {
            "users": [user_me.to_json() for user_me in users_me],
            "total": total,
            "page": page,
            "limit": limit,
            "pageCount": len(users),
        }


@ns_admin.route('/user/<string:user_id>')
@ns_admin.param('user_id', 'The user ID')
class AdminUser(Resource):

    @token_required
    @ns_admin.marshal_with(UserMe.to_model(name_space=ns_admin), code=200)
    def get(self, user_id):
        user_token: UserToken = g.user

        user = User.get(user_token, user_id)
        if not user:
            raise NotFoundException("User not found")

        return user.to_me().to_json()

    @token_required
    @ns_admin.marshal_with(UserMe.to_model(name_space=ns_admin), code=200)
    def put(self, user_id):
        user_token: UserToken = g.user

        data = request.get_json()
        user_me = UserMe(**data)

        user = User.get(user_token, user_id)
        if not user:
            raise NotFoundException("User not found")

        user.firstname = user_me.firstname
        user.lastname = user_me.lastname
        user.account = user_me.account
        user.address = user_me.address

        is_updated = user.update_user()
        if is_updated:
            # TODO: force to update token with new name value
            return user.to_me().to_json()
        return jsonify({"message": "Error during update"}), 400

    @token_required
    @ns_admin.marshal_with(Model.get_message_response_model(name_space=ns_admin), code=200)
    def delete(self, user_id):
        user_token: UserToken = g.user

        user = User.get(user_token, user_id)

        if not user:
            raise NotFoundException("User not found")

        user.delete()

        return {"success": True, "message": "User deleted"}


# Manages Dashboard


@ns_admin.route('/dashboard/summary')
@ns_admin.param('after_date', 'Date of consideration')
@ns_admin.param('before_date', 'Date of consideration')
class AdminDashboardSummary(Resource):

    @token_required
    @ns_admin.marshal_with(ns_admin.model('DashboardSummary', {
            'total_articles': fields.Integer(required=False),
            'total_comments': fields.Integer(required=False),
            'total_users': fields.Integer(required=False),
            'total_interactions': fields.Integer(required=False),
            'total_errors': fields.Integer(required=False),
        }), code=200)
    def get(self):
        after_date_arg = request.args.get('after_date', default='', type=str)
        before_date_arg = request.args.get('before_date', default='', type=str)

        after_date = None
        if after_date_arg:
            try:
                after_date_obj = datetime.datetime.strptime(after_date_arg, "%Y-%m-%d")
                after_date = after_date_obj.replace(hour=0, minute=0, second=0, microsecond=0)
            except Exception:
                pass

        before_date = None
        if before_date_arg:
            try:
                before_date_obj = datetime.datetime.strptime(before_date_arg, "%Y-%m-%d")
                before_date = before_date_obj.replace(hour=0, minute=0, second=0, microsecond=0)
            except Exception:
                pass

        user_token: UserToken = g.user

        total_articles = ArticleModel.get_all_count(user_token, after_date=after_date, before_date=before_date)
        total_comments = CommentModel.get_all_count(user_token, after_date=after_date, before_date=before_date)
        total_users = User.get_all_count(user_token, after_date=after_date, before_date=before_date)
        total_interactions = UserArticleInteractionModel.get_all_count(user_token, after_date=after_date, before_date=before_date)
        total_errors = ServerErrorLogModel.get_all_count(user_token, after_date=after_date, before_date=before_date)

        return {
            "total_articles": total_articles,
            "total_comments": total_comments,
            "total_users": total_users,
            "total_interactions": total_interactions,
            "total_errors": total_errors
        }

@ns_admin.route('/dashboard/top-articles')
@ns_admin.param('date', 'Date of consideration')
@ns_admin.param('limit', 'Number of element to return')
class AdminDashboardTopArticles(Resource):

    @token_required
    @ns_admin.marshal_with(ArticleInteractionDashboard.to_model_list(name_space=ns_admin), code=200)
    def get(self):
        date_arg = request.args.get('date', default='', type=str)

        if date_arg:
            try:
                date_obj = datetime.datetime.strptime(date_arg, "%Y-%m-%d")
                date = date_obj.replace(hour=0, minute=0, second=0, microsecond=0)
            except Exception:
                date = (datetime.datetime.now()).replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            date = (datetime.datetime.now()).replace(hour=0, minute=0, second=0, microsecond=0)

        user_token: UserToken = g.user

        articles_stat = ArticleInteractionDashboard.get_most_interacted_articles(date_check=date)

        return [article.to_json() for article in articles_stat]


@ns_admin.route('/dashboard/top-tags')
class AdminDashboardTopTags(Resource):

    @token_required
    @ns_admin.marshal_with(UserPreferencesDashboard.to_model(name_space=ns_admin), code=200)
    def get(self):
        limit_arg = request.args.get('limit', default=10, type=int)

        limit = limit_arg if limit_arg > 0 else 10

        user_token: UserToken = g.user

        tags_stat = UserPreferencesDashboard.get_top_tags(limit=limit)

        return [tag.to_json() for tag in tags_stat]


@ns_admin.route('/dashboard/activity')
class AdminDashboardActivity(Resource):

    @token_required
    def get(self):
        user_token: UserToken = g.user


# Manages errors


@ns_admin.route('/dashboard/errors')
@ns_admin.param('page', 'Page')
@ns_admin.param('limit', 'Number of errors to return')
class AdminDashboardErrors(Resource):

    @token_required
    @ns_admin.marshal_with(ServerErrorLogModel.to_model_list(name_space=ns_admin), code=200)
    def get(self):
        page_arg = request.args.get('page', default=1, type=int)
        limit_arg = request.args.get('limit', default=10, type=int)

        page = page_arg if page_arg > 0 else 1
        limit = limit_arg if limit_arg > 0 else 10

        user_token: UserToken = g.user

        total = ServerErrorLogModel.get_all_count(user_token)
        errors = ServerErrorLogModel.get_all(user_token, page=page, limit=limit)

        return {
            "errors": [err.to_json() for err in errors],
            "total": total,
            "page": page,
            "limit": limit,
            "pageCount": len(errors),
        }


@ns_admin.route('/dashboard/errors/<server_error_log_id>')
class AdminDashboardError(Resource):

    @token_required
    @ns_admin.marshal_with(ServerErrorLogModel.to_model(name_space=ns_admin), code=200)
    def get(self, server_error_log_id):
        user_token: UserToken = g.user

        err = ServerErrorLogModel.get(user_token, server_error_log_id)

        if not err:
            raise NotFoundException("Error not found")

        return err.to_json()

    @token_required
    @ns_admin.marshal_with(Model.get_message_response_model(name_space=ns_admin), code=200)
    def delete(self, server_error_log_id):
        user_token: UserToken = g.user

        err = ServerErrorLogModel.get(user_token, server_error_log_id)

        if not err:
            raise NotFoundException("Error not found")

        return {"success": True, "message": "Error deleted"}


@ns_admin.route('/reload-config')
class AdminApiResource(Resource):

    @token_required
    @ns_admin.marshal_with(Model.get_message_response_model(name_space=ns_admin), code=200)
    def get(self):
        user_token: UserToken = g.user

        config_manager.reload()

        return {"success": True, "message": "Reloaded"}




