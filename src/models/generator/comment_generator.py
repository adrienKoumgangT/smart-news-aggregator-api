import datetime
import random
from datetime import timedelta
from typing import Optional

from bson import ObjectId
from faker import Faker

from src.lib.log.api_logger import ApiLogger
from src.lib.utility.utils import convert_str_to_datetime, random_datetime
from src.models.article.article_model import ArticleModel
from src.models.article.comment_model import CommentManager, CommentModel
from src.models.article.user_article_interaction_models import UserArticleInteractionModel
from src.models.user.user_model import User


def generate_random_comment_for_random_user():
    fake = Faker()

    limit = 100

    article_count = ArticleModel.get_list_count()
    total_pages = int(article_count / limit)

    for page in range(1, total_pages+1):
        articles = ArticleModel.last_articles(page=page, limit=limit)

        users = User.get_list(page=random.randint(1, 5), limit=random.randint(5, 100))

        users_use = random.sample(users, random.randint(5, len(users)))

        for article in articles:
            comment: Optional[CommentModel] = None
            for user in users_use:
                comment_data = {
                    'user_id': str(user.user_id),
                    'author': user.to_author(),
                    'article_id': str(article.article_id),
                    'content': fake.text(),
                    'created_at': random_datetime(start=convert_str_to_datetime(article.published_at).replace(tzinfo=None), end=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))
                }

                if random.randint(0, 1) and comment is not None:
                    comment_data['comment_fk'] = str(comment.comment_id)

                comment = CommentModel(**comment_data)
                # print(comment.to_bson())
                comment.save()

                try:
                    UserArticleInteractionModel.update_interaction_read(
                        user_id=str(user.user_id),
                        article_id=str(article.article_id),
                        article_title=article.title,
                        comment_id=comment.comment_fk
                    )
                except:
                    pass


def update_comment_with_user_author_data():
    limit = 100

    user_count = User.get_list_count()
    total_pages = int(user_count / limit)
    users_map = dict()
    for page in range(1, total_pages+1):
        users = User.get_list(page=page, limit=limit)
        for user in users:
            users_map[str(user.user_id)] = user

    comment_count = CommentModel.get_list_count()
    total_pages = int(comment_count / limit)
    for page in range(1, total_pages+1):
        comments = CommentModel.get_list(page=page, limit=limit)

        for comment in comments:
            user = users_map.get(str(comment.user_id))
            if user:
                comment.update_author(author=user.to_author())


def remove_from_comment_field_name():
    api_logger = ApiLogger(f"[MONGODB] [COMMENT] [DELETE FIELD NAME]")

    CommentManager.collection().update_many(
        {},
        {'$unset': {'name': None}},
    )

    api_logger.print_log()




def update_article_published_at():
    limit = 1000
    total = ArticleModel.get_list_count()
    total_page = int(total / limit)
    for page in range(1, total_page+1):
        articles = ArticleModel.get_list(page=page, limit=limit)
        print(len(articles))
        for article in articles:
            api_logger = ApiLogger(f"[MONGODB] [ARTICLE] [SET] : {article.article_id}")

            result = CommentManager.collection().update_one(
                filter={"_id": ObjectId(article.article_id)},
                update={
                    "$set": {
                        "published_att": convert_str_to_datetime(article.published_at),
                    }
                }
            )

            api_logger.print_log()

            print(result)


def modify():
    api_logger = ApiLogger(f"[MONGODB] [ARTICLE] [SET] : published_at -> published_att")
    result = CommentManager.collection().update_many(
        {},
        { "$rename": {"published_at": "published_att"} }
    )
    api_logger.print_log()
    print(result)


if __name__ == '__main__':

    generate_random_comment_for_random_user()




