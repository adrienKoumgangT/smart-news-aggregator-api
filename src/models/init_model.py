from src.models.article.article_model import ArticleModel
from src.models.article.comment_model import CommentModel
from src.models.article.user_article_interaction_models import UserArticleInteraction
from src.models.user.user_model import User


def init_user_model():
    print(f"Initializing model user: begin")

    User.init_database()

    print(f"Initializing model user: end")


def init_article_model():
    print(f"Initializing model article: begin")

    ArticleModel.init_database()

    print(f"Initializing model article: end")


def init_comment_model():
    print(f"Initializing model comment: begin")

    CommentModel.init_database()

    print(f"Initializing model comment: end")


def init_interaction_model():
    print(f"Initializing model interaction: begin")

    UserArticleInteraction.init_database()

    print(f"Initializing model interaction: end")


def init_model():
    init_user_model()
    init_article_model()
    init_comment_model()
    init_interaction_model()


if __name__ == '__main__':
    init_model()

