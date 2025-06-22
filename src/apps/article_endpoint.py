from flask import g, jsonify, request
from flask_restx import Namespace, Resource

from src.apps import token_required
from src.lib.exception.exception_server import NotFoundException, UnauthorizedException
from src.models.article.article_model import ArticleSummaryModel, ArticleModel, ArticleWithInteractionModel, \
    ArticleTagsModel, ArticleUtility
from src.models.article.comment_model import CommentModel
from src.models.article.user_article_interaction_models import UserArticleInteractionModel, UserArticleInteraction, \
    ArticleInteractionStatus, ArticleInteractionType
from src.models.model import Model
from src.models.user.auth_model import UserToken
from src.models.user.user_model import UserAuthor, User

ns_article = Namespace('article', description='Article endpoint')


@ns_article.route('/tags')
class ArticleTags(Resource):

    @token_required
    @ns_article.marshal_with(ArticleTagsModel.to_model(name_space=ns_article), code=200)
    def get(self):
        user_token: UserToken = g.user

        tags = ArticleModel.get_all_tags()

        result = ArticleTagsModel(tags=tags)

        return result.to_json()

    @token_required
    @ns_article.expect(Model.get_search_model(name_space=ns_article))
    @ns_article.marshal_with(ArticleTagsModel.to_model(name_space=ns_article), code=200)
    def post(self):
        user_token: UserToken = g.user

        data = request.get_json()
        search = data.get('search', None)

        tags = ArticleModel.get_all_tags(search=search)

        result = ArticleTagsModel(tags=tags)

        return result.to_json()



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

        user = User.get(user_id=user_token.user_id)

        if user.preferences_enable and user.preferences:
            total = ArticleModel.last_articles_count(preferences=user.preferences)
            articles = ArticleModel.last_articles(preferences=user.preferences, page=page, limit=limit)
        else:
            total = ArticleModel.last_articles_count()
            articles = ArticleModel.last_articles(page=page, limit=limit)

        ArticleUtility.cache_articles(articles=articles)

        return {
            "articles": [article.to_summary() for article in articles],
            "total": total,
            "page": page,
            "limit": limit,
            "pageCount": len(articles),
        }


@ns_article.route('/history')
@ns_article.param('page', 'Page')
@ns_article.param('limit', 'Number of articles to return')
class ArticleHistoryResource(Resource):

    @token_required
    @ns_article.marshal_with(UserArticleInteractionModel.to_model_list(name_space=ns_article))
    def get(self):
        page_arg = request.args.get('page', default=1, type=int)
        limit_arg = request.args.get('limit', default=5, type=int)

        page = page_arg if page_arg > 0 else 1
        limit = limit_arg if limit_arg > 0 else 10

        user_token: UserToken = g.user

        total = UserArticleInteractionModel.read_history_count(user_id=user_token.user_id)
        histories = UserArticleInteractionModel.get_read_history(user_id=user_token.user_id, page=page, limit=limit)

        result = [history.to_json() for history in histories]

        return {
            "interactions": result,
            "page": page,
            "limit": limit,
            "pageCount": len(histories),
            "total": total,
        }


@ns_article.route('/<string:article_id>')
@ns_article.param('article_id', 'The article ID')
class ArticleSummaryResource(Resource):

    @token_required
    @ns_article.marshal_with(ArticleModel.to_model(name_space=ns_article))
    def get(self, article_id):
        user_token: UserToken = g.user

        article = ArticleWithInteractionModel.get(article_id=article_id)

        if not article:
            raise NotFoundException("Article not found")

        current_user_interaction = UserArticleInteractionModel.get_by_user_article(user_id=user_token.user_id, article_id=article_id)
        if current_user_interaction:
            article.current_user_interaction = ArticleInteractionStatus.from_interaction(interaction=current_user_interaction)

        total_user_interaction = UserArticleInteractionModel.get_stats(article_id=article_id)
        if total_user_interaction:
            article.total_user_interaction = total_user_interaction

        UserArticleInteractionModel.update_interaction_read(
            user_id=user_token.user_id,
            article_id=article_id,
            article_title=article.title
        )

        return article.to_json()


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
        return article.to_summary()


@ns_article.route('/<string:article_id>/interaction')
@ns_article.param('article_id', 'The article ID')
class ArticleInteractionResource(Resource):

    @token_required
    @ns_article.marshal_with(UserArticleInteractionModel.to_model(name_space=ns_article))
    def get(self, article_id):
        user_token: UserToken = g.user

        interaction = UserArticleInteractionModel.get_by_user_article(user_id=user_token.user_id, article_id=article_id)

        if interaction:
            return interaction.to_json()

        return UserArticleInteractionModel(_id=None, level_interaction="article", user_id=user_token.user_id, article_id=article_id).to_json()

    @token_required
    @ns_article.expect(ArticleInteractionType.to_model(name_space=ns_article))
    @ns_article.marshal_with(Model.get_message_response_model(name_space=ns_article))
    def post(self, article_id):
        user_token: UserToken = g.user

        data = request.get_json()
        interaction = ArticleInteractionType(**data)
        result = UserArticleInteractionModel.update_interaction(interaction=interaction, user_id=user_token.user_id, article_id=article_id)

        if result:
            return {"success": True, "message": "Interaction updated"}
        return {"success": False, "message": "Interaction could not be updated"}


@ns_article.route('/<string:article_id>/comment')
@ns_article.param('article_id', 'The article ID')
@ns_article.param('page', 'Page')
@ns_article.param('limit', 'Number of articles to return')
class ArticleCommentResource(Resource):

    @token_required
    @ns_article.marshal_with(CommentModel.to_model_list(name_space=ns_article))
    def get(self, article_id):
        page_arg = request.args.get('page', default=1, type=int)
        limit_arg = request.args.get('limit', default=10, type=int)

        page = page_arg if page_arg > 0 else 1
        limit = limit_arg if limit_arg > 0 else 10

        user_token: UserToken = g.user

        comments = CommentModel.last_comments(article_id=article_id, page=page, limit=limit)
        comments_result = []
        for comment in comments:
            user_author = User.get(user_id=comment.user_id).to_author()
            comments_result.append(comment.to_json() | {"author": (user_author.to_json() if user_author else None)})

        return {'comments': comments_result}


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

        article = ArticleModel.get(article_id=article_id)

        if article is None:
            raise NotFoundException("Article not found")

        comment = CommentModel.get(comment_id=comment_id)

        if comment is None:
            raise NotFoundException("Comment not found")

        UserArticleInteractionModel.update_interaction_read(
            user_id=user_token.user_id,
            article_id=article_id,
            article_title=article.title,
            comment_id=comment_id
        )

        current_user_interaction = UserArticleInteractionModel.get_by_user_article(user_id=user_token.user_id, article_id=article_id, comment_id=comment_id)
        if current_user_interaction:
            comment.current_user_interaction = ArticleInteractionStatus.from_interaction(interaction=current_user_interaction)

        total_user_interaction = UserArticleInteractionModel.get_stats(article_id=article_id, comment_id=comment_id)
        if total_user_interaction:
            comment.total_user_interaction = total_user_interaction

        user_author = UserAuthor.get(user_id=comment.user_id)

        return comment.to_json() | {"author": (user_author.to_json() if user_author else None)}


    @token_required
    def delete(self, article_id, comment_id):
        user_token: UserToken = g.user

        comment = CommentModel.get(comment_id=comment_id)

        if comment is None:
            raise NotFoundException("Comment not found")

        if comment.user_id != user_token.user_id:
            raise UnauthorizedException("You are not authorized to perform this action")

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



