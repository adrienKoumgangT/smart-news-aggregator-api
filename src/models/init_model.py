from src.helpers.externapi.externapi_base import LogRequest
from src.lib.log.api_logger import ApiLogger
from src.models.article.article_model import ArticleModel
from src.models.article.comment_model import CommentModel
from src.models.article.user_article_interaction_models import UserArticleInteractionModel
from src.models.user.user_model import User


def init_user_model():
    api_logger = ApiLogger(f"[MONGODB] [USER] [INDEX CREATION] ")

    User.init()

    api_logger.print_log()


def init_article_model():
    api_logger = ApiLogger(f"[MONGODB] [ARTICLE] [INDEX CREATION] ")

    ArticleModel.init()

    api_logger.print_log()


def init_comment_model():
    api_logger = ApiLogger(f"[MONGODB] [COMMENT] [INDEX CREATION] ")

    CommentModel.init()

    api_logger.print_log()


def init_interaction_model():
    api_logger = ApiLogger(f"[MONGODB] [INTERACTION] [INDEX CREATION] ")

    UserArticleInteractionModel.init()

    api_logger.print_log()


def init_article_log_request_model():
    api_logger = ApiLogger(f"[MONGODB] [ARTICLE LOG REQUEST] [INDEX CREATION] ")

    LogRequest.init()

    api_logger.print_log()


def init_all_model():
    init_user_model()
    init_article_model()
    init_comment_model()
    init_interaction_model()
    init_article_log_request_model()

if __name__ == '__main__':
    init_all_model()

