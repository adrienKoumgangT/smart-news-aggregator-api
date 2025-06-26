import random

from src.models.article.article_model import ArticleModel
from src.models.article.comment_model import CommentModel
from src.models.article.user_article_interaction_models import ArticleInteractionType, UserArticleInteractionModel
from src.models.user.user_model import User


def get_random_interaction_type():
    interaction_type = random.randint(1, 5)

    if interaction_type == 1:
        return ArticleInteractionType(type='liked', value=True)
    elif interaction_type == 2:
        return ArticleInteractionType(type='shared', value=True)
    elif interaction_type == 3:
        return ArticleInteractionType(type='saved', value=True)
    elif interaction_type == 4:
        return ArticleInteractionType(type='report', value=True)
    else:
        return None


def generate_random_interaction_for_random_user():
    limit = 100

    article_count = ArticleModel.get_list_count()
    total_pages = int(article_count / limit)

    for page in range(1, total_pages + 1):
        articles = ArticleModel.last_articles(page=page, limit=limit)

        users = User.get_list(page=random.randint(1, 5), limit=random.randint(5, limit))

        users_use = random.sample(users, random.randint(5, len(users)))

        for article in articles:
            for user in users_use:

                UserArticleInteractionModel.update_interaction_read(
                    user_id=str(user.user_id),
                    article_id=str(article.article_id),
                    article_title=article.title,
                )

                if random.randint(0, 1):
                    interaction = get_random_interaction_type()
                    if interaction:
                        UserArticleInteractionModel.update_interaction(interaction=interaction,
                                                                       user_id=str(user.user_id),
                                                                       article_id=str(article.article_id),
                                                                       )


def generate_interaction_from_comment():
    limit = 100

    article_count = ArticleModel.get_list_count()
    total_pages = int(article_count / limit)

    for page in range(1, total_pages + 1):
        articles = ArticleModel.last_articles(page=page, limit=limit)

        for article in articles:

            comment_count = CommentModel.get_list_count(article_id=str(article.article_id))
            total_pages_comment = int(comment_count / limit)

            for page_comment in range(1, total_pages_comment + 1):
                comments = CommentModel.get_list(article_id=str(article.article_id), page=page_comment, limit=limit)

                for comment in comments:

                    UserArticleInteractionModel.update_interaction_read(
                        user_id=comment.user_id,
                        article_id=str(article.article_id),
                        article_title=article.title,
                        comment_id=comment.comment_fk
                    )

                    if random.randint(0, 1):
                        interaction = get_random_interaction_type()
                        if interaction:
                            UserArticleInteractionModel.update_interaction(interaction=interaction,
                                                                           user_id=comment.user_id,
                                                                           article_id=str(article.article_id),
                                                                           comment_id=comment.comment_fk)


if __name__ == '__main__':
    generate_random_interaction_for_random_user()

