from flask import g, jsonify, request
from flask_restx import Namespace, Resource

from src.apps import token_required
from src.lib.exception.exception_server import NotFoundException, UnauthorizedException
from src.models.article.article_model import ArticleSummaryModel, ArticleModel
from src.models.article.comment_model import CommentModel
from src.models.article.user_article_interaction_models import UserArticleInteractionModel, UserArticleInteraction
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


@ns_article.route('/<string:article_id>')
@ns_article.param('article_id', 'The article ID')
class ArticleSummaryResource(Resource):

    @token_required
    @ns_article.marshal_with(ArticleSummaryModel.to_model(name_space=ns_article))
    def get(self, article_id):
        user_token: UserToken = g.user

        article = ArticleModel.get(article_id=article_id)

        if not article:
            raise NotFoundException("Article not found")

        UserArticleInteractionModel.update_interaction_read(
            user_id=user_token.user_id,
            article_id=article_id
        )

        return article.to_json()

    @token_required
    def delete(self, article_id):
        user_token: UserToken = g.user

        if user_token.role != 'admin':
            raise UnauthorizedException("You are not authorized to perform this action")

        article = ArticleModel.get(article_id=article_id)

        if not article:
            raise NotFoundException("Article not found")

        article.delete()
        return {"success": True, "message": "Article deleted"}


@ns_article.route('/<string:article_id>/summary')
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

@ns_article.route('/<string:article_id>/history')
@ns_article.param('article_id', 'The article ID')
class ArticleHistoryResource(Resource):

    @token_required
    @ns_article.marshal_with(ArticleSummaryModel.to_model(name_space=ns_article))
    def get(self, article_id):
        user_token: UserToken = g.user

        histories = UserArticleInteractionModel.get_read_history(user_id=user_token.id)

        result = [history.to_json() for history in histories]

        return {"history": result}


@ns_article.route('/<string:article_id>/interaction')
@ns_article.param('article_id', 'The article ID')
class ArticleInteractionResource(Resource):

    @token_required
    @ns_article.marshal_with(UserArticleInteractionModel.to_model(name_space=ns_article))
    def get(self, article_id):
        user_token: UserToken = g.user

        interaction = UserArticleInteractionModel.get_by_user_article(user_id=user_token.id, article_id=article_id)

        if interaction:
            return interaction.to_json()

        return UserArticleInteractionModel(_id=None, level_interaction="article", user_id=user_token.id, article_id=article_id).to_json()

    @token_required
    @ns_article.expect(UserArticleInteraction.to_model(name_space=ns_article))
    @ns_article.marshal_with(UserArticleInteractionModel.to_model(name_space=ns_article))
    def post(self, article_id):
        user_token: UserToken = g.user

        data = request.get_json()
        interaction = UserArticleInteraction(**data)
        result = UserArticleInteractionModel.update_interaction(interaction=interaction, user_id=user_token.id, article_id=article_id)

        if result:
            return {"success": True, "message": "Interaction updated"}
        return {"success": False, "message": "Interaction could not be updated"}


@ns_article.route('/<string:article_id>/comment')
@ns_article.param('article_id', 'The article ID')
@ns_article.param('page', 'Page')
@ns_article.param('limit', 'Number of articles to return')
class ArticleCommentResource(Resource):

    @token_required
    @ns_article.marshal_with(CommentModel.to_model(name_space=ns_article))
    def get(self, article_id):
        page_arg = request.args.get('page', default=1, type=int)
        limit_arg = request.args.get('limit', default=10, type=int)

        page = page_arg if page_arg > 0 else 1
        limit = limit_arg if limit_arg > 0 else 10

        user_token: UserToken = g.user

        comments = CommentModel.last_comments(article_id=article_id, page=page, limit=limit)

        return [comment.to_json() for comment in comments]


    @token_required
    @ns_article.expect(CommentModel.to_model(name_space=ns_article))
    @ns_article.marshal_with(CommentModel.to_model(name_space=ns_article))
    def post(self, article_id):
        user_token: UserToken = g.user

        data = request.get_json()
        data['article_id'] = article_id
        data['user_id'] = user_token.user_id
        comment = CommentModel(**data)
        comment.save()

        if comment.comment_id is None:
            raise NotFoundException("Error during save comment")
        return comment.to_json()


@ns_article.route('/<string:article_id>/comment/<int:comment_id>')
@ns_article.param('article_id', 'The article ID')
class ArticleCommentResource2(Resource):

    @token_required
    @ns_article.marshal_with(CommentModel.to_model(name_space=ns_article))
    def get(self, article_id, comment_id):
        user_token: UserToken = g.user

        comment = CommentModel.get(comment_id=comment_id)

        if comment is None:
            raise NotFoundException("Comment not found")

        UserArticleInteractionModel.update_interaction_read(
            user_id=user_token.user_id,
            article_id=article_id,
            comment_id=comment_id
        )

        return comment.to_json()


    @token_required
    def delete(self, article_id, comment_id):
        user_token: UserToken = g.user

        comment = CommentModel.get(comment_id=comment_id)

        if comment is None:
            raise NotFoundException("Comment not found")

        comment.delete()

        return {"success": True, "message": "Comment deleted"}


@ns_article.route('/<string:article_id>/comment/<string:comment_id>/interaction')
@ns_article.param('article_id', 'The article ID')
@ns_article.param('comment_id', 'The comment ID')
class ArticleInteractionResource(Resource):

    @token_required
    @ns_article.marshal_with(UserArticleInteractionModel.to_model(name_space=ns_article))
    def get(self, article_id, comment_id):
        user_token: UserToken = g.user

        interaction = UserArticleInteractionModel.get_by_user_article(user_id=user_token.id, article_id=article_id, comment_id=comment_id)

        if interaction:
            return interaction.to_json()

        return UserArticleInteractionModel(_id=None, level_interaction="article", user_id=user_token.id, article_id=article_id).to_json()

    @token_required
    @ns_article.expect(UserArticleInteraction.to_model(name_space=ns_article))
    @ns_article.marshal_with(UserArticleInteractionModel.to_model(name_space=ns_article))
    def post(self, article_id, comment_id):
        user_token: UserToken = g.user

        data = request.get_json()
        interaction = UserArticleInteraction(**data)
        result = UserArticleInteractionModel.update_interaction(interaction=interaction, user_id=user_token.id, article_id=article_id, comment_id=comment_id)

        if result:
            return {"success": True, "message": "Interaction updated"}
        return {"success": False, "message": "Interaction could not be updated"}



