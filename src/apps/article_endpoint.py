from flask import g, jsonify, request
from flask_restx import Namespace, Resource

from src.apps import token_required
from src.lib.exception.exception_server import NotFoundException
from src.models.article.article_model import ArticleSummaryModel, ArticleModel
from src.models.user.auth_model import UserToken

ns_article = Namespace('article', description='Article endpoint')


@ns_article.route('/latest')
@ns_article.param('page', 'Page')
@ns_article.param('limit', 'Number of articles to return')
class LatestArticleResource(Resource):

    @token_required
    @ns_article.marshal_with(ArticleSummaryModel.to_model_list(name_space=ns_article), code=200)
    def get(self):
        page_arg = request.args.get('page', default=1, type=int)
        limit_arg = request.args.get('limit', default=10, type=int)

        page = page_arg if page_arg > 0 else 1
        limit = limit_arg if limit_arg > 0 else 10

        user_token: UserToken = g.user

        articles = ArticleSummaryModel.last_articles(page=page, limit=limit)

        return {"articles": [article.to_json() for article in articles]}


@ns_article.route('/summary/<string:article_id>')
@ns_article.param('article_id', 'The article ID')
class ArticleSummaryResource(Resource):

    @token_required
    @ns_article.marshal_with(ArticleSummaryModel.to_model(name_space=ns_article))
    def get(self, article_id):
        user_token: UserToken = g.user

        article = ArticleModel.get(article_id=article_id)

        if not article:
            raise NotFoundException("Article not found")
        return article.to_summary().to_json()

