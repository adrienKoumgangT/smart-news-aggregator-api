from flask import g, request
from flask_restx import Namespace, Resource

from src.apps import token_required
from src.lib.exception.exception_server import NotFoundException, UnauthorizedException
from src.models.article.article_model import ArticleSummaryModel, ArticleModel, ArticleWithInteractionModel, \
    ArticleTagsModel, ArticleSearchModel
from src.models.article.comment_model import CommentModel, CommentDetailsModel
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

        tags = ArticleModel.get_all_tags(user_token)

        result = ArticleTagsModel(tags=tags)

        return result.to_json()

    @token_required
    @ns_article.expect(Model.get_search_model(name_space=ns_article))
    @ns_article.marshal_with(ArticleTagsModel.to_model(name_space=ns_article), code=200)
    def post(self):
        user_token: UserToken = g.user

        data = request.get_json()
        search = data.get('search', None)

        tags = ArticleModel.get_all_tags(user_token, search=search)

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

        user = User.get(user_token, user_token.user_id)

        if user.preferences_enable and user.preferences:
            total = ArticleModel.last_articles_count(user_token, preferences=user.preferences)
            articles = ArticleModel.last_articles(user_token, preferences=user.preferences, page=page, limit=limit)
        else:
            total = ArticleModel.last_articles_count(user_token)
            articles = ArticleModel.last_articles(user_token, page=page, limit=limit)

        ArticleModel.cache_articles(user_token, articles=articles)

        return {
            "articles": [article.to_summary() for article in articles],
            "total": total,
            "page": page,
            "limit": limit,
            "pageCount": len(articles),
        }


@ns_article.route('/search')
@ns_article.param('q', 'Query search')
@ns_article.param('page', 'Page')
@ns_article.param('limit', 'Number of articles to return')
class SearchArticleResource(Resource):

    @token_required
    @ns_article.marshal_with(ArticleSummaryModel.to_model_list(name_space=ns_article), code=200)
    def get(self):
        query_arg = request.args.get('q', default='', type=str)
        page_arg = request.args.get('page', default=1, type=int)
        limit_arg = request.args.get('limit', default=10, type=int)

        query = query_arg if query_arg else ''
        page = page_arg if page_arg > 0 else 1
        limit = limit_arg if limit_arg > 0 else 10

        user_token: UserToken = g.user

        total = ArticleModel.search_articles_count(user_token, query=query)
        articles = ArticleModel.search_articles(user_token, query=query, page=page, limit=limit)

        ArticleModel.cache_articles(user_token, articles=articles)

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
    @ns_article.marshal_with(ArticleWithInteractionModel.to_model(name_space=ns_article))
    def get(self, article_id):
        user_token: UserToken = g.user

        article = ArticleWithInteractionModel.get(user_token, article_id)

        if not article:
            raise NotFoundException("Article not found")

        current_user_interaction = UserArticleInteractionModel.get_by_user_article(user_id=user_token.user_id, article_id=article_id)
        if current_user_interaction:
            article.current_user_interaction = ArticleInteractionStatus.from_interaction(interaction=current_user_interaction)

        total_user_interaction = UserArticleInteractionModel.get_stats(article_id=article_id)
        if total_user_interaction:
            article.total_user_interaction = total_user_interaction

        UserArticleInteractionModel.update_interaction_read(
            user_token=user_token,
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

        article = ArticleModel.get(user_token, article_id)

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
        result = UserArticleInteractionModel.update_interaction(user_token, interaction=interaction, article_id=article_id)

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

        comments = CommentModel.get_all(user_token, article_id=article_id, page=page, limit=limit)

        return {'comments': [comment.to_json() for comment in comments]}


    @token_required
    @ns_article.expect(CommentModel.to_model(name_space=ns_article))
    @ns_article.marshal_with(CommentModel.to_model(name_space=ns_article))
    def post(self, article_id):
        user_token: UserToken = g.user

        data = request.get_json()
        data['article_id'] = article_id
        data['user_id'] = user_token.user_id

        user = User.get(user_token, user_token.user_id)
        data['author'] = user.to_author()

        comment = CommentModel(**data)
        comment.save(user_token)

        if comment.comment_id is None:
            raise NotFoundException("Error during save comment")
        return comment.to_json()


@ns_article.route('/<string:article_id>/comment/<string:comment_id>')
@ns_article.param('article_id', 'The article ID')
class ArticleCommentResource2(Resource):

    @token_required
    @ns_article.marshal_with(CommentModel.to_model(name_space=ns_article))
    def get(self, article_id, comment_id):
        user_token: UserToken = g.user

        article = ArticleModel.get(user_token, article_id)

        if article is None:
            raise NotFoundException("Article not found")

        comment = CommentModel.get(user_token, comment_id)

        if comment is None:
            raise NotFoundException("Comment not found")

        UserArticleInteractionModel.update_interaction_read(
            user_token=user_token,
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

        user_author = UserAuthor.get(user_token, comment.user_id)

        return comment.to_json() | {"author": (user_author.to_json() if user_author else None)}


    @token_required
    def delete(self, article_id, comment_id):
        user_token: UserToken = g.user

        article = ArticleModel.get(user_token, article_id)

        if article is None:
            raise NotFoundException("Article not found")

        comment = CommentModel.get(user_token, comment_id)

        if comment is None:
            raise NotFoundException("Comment not found")

        if comment.user_id != user_token.user_id:
            raise UnauthorizedException("You are not authorized to perform this action")

        if comment.article_id != article_id:
            raise UnauthorizedException("You are not authorized to perform this action")

        comment.delete(user_token)

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
        result = UserArticleInteractionModel.update_interaction(user_token, interaction=interaction, article_id=article_id, comment_id=comment_id)

        if result:
            return {"success": True, "message": "Interaction updated"}
        return {"success": False, "message": "Interaction could not be updated"}


@ns_article.route('/comment/me')
@ns_article.param('page', 'Page')
@ns_article.param('limit', 'Number of articles to return')
class ArticleCommentUserResource(Resource):

    @token_required
    @ns_article.marshal_with(CommentDetailsModel.to_model_list(name_space=ns_article))
    def get(self):
        page_arg = request.args.get('page', default=1, type=int)
        limit_arg = request.args.get('limit', default=10, type=int)

        page = page_arg if page_arg > 0 else 1
        limit = limit_arg if limit_arg > 0 else 10

        user_token: UserToken = g.user

        total = CommentDetailsModel.get_comments_count(user_token)
        comments = CommentDetailsModel.get_user_comments_with_article(user_token, page=page, limit=limit)

        return {
            'comments': [comment.to_json() for comment in comments],
            "page": page,
            "limit": limit,
            "pageCount": len(comments),
            "total": total,
        }



