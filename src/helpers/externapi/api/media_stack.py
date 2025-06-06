import time
from typing import Optional, List

import requests

from src.helpers.externapi.externapi_base import ExternApiBase
from src.lib.configuration import configuration
from src.lib.log.api_logger import ApiLogger
from src.models.article.article_model import ArticleModel, ArticleSourceModel


# https://mediastack.com
class MediaStack(ExternApiBase):
    api_name = "MediaStack"
    base_url = "https://api.mediastack.com/v1/news"
    data_field = "data"
    limit = 100

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.api_key = api_key if api_key else configuration.get_configuration("externapi.mediastack.access_key")

    def fetch_news(self) -> List[dict]:
        """
        Fetch news from MediaStack API.
        """
        if self.api_key:
            api_log = ApiLogger(f"[EXTERN API] Retrieving news from {self.api_name} API.")

            all_articles = []
            params = {
                "access_key": self.api_key,
                "limit": self.limit,
                "offset": 0,
                "sort": "published_desc"
            }
            while True:
                response = requests.get(self.base_url, params=params)
                status_code = response.status_code
                response_data = response.json()
                is_success = status_code == 200 and self.data_field in response_data

                fetched_count = len(response_data[self.data_field]) if status_code == 200 and self.data_field in response_data else None
                total_articles = response_data['pagination']['total'] if status_code == 200 and 'pagination' in response_data else None

                self.log_request(
                    api_name=self.api_name,
                    url=self.base_url,
                    headers={},
                    params=params,
                    status_code=status_code,
                    data=response_data,
                    total_articles=total_articles,
                    fetched_count=fetched_count,
                    is_success=is_success
                )

                if is_success:
                    all_articles.extend(response_data[self.data_field])

                    params["offset"] += self.limit
                    if params["offset"] >= response_data["pagination"]["total"]:
                        break
                else:
                    break

                time.sleep(1)

            api_log.print_log(extend_message=f"Retrieved {len(all_articles)} articles")
            return all_articles

        return []

    @classmethod
    def to_article(cls, data: dict) -> ArticleModel:
        return ArticleModel(
            _id=None,
            extern_id=None,
            extern_api=cls.api_name,

            title=data.get('title'),
            description=data.get('description'),
            content=data.get('content'),
            url=data.get('url'),
            author=ArticleSourceModel(
                name=data.get('author'),
                url=data.get('source')
            ),
            source=ArticleSourceModel(
                name=data.get('author'),
                url=data.get('source')
            ),
            image_url=data.get('image'),
            published_at=data.get('published_at'),
            language=data.get('language'),
            country=data.get('country'),
            tags=[data.get('category')] if data.get('category') else [],
        )


example_media_stack_api_response = {
    "pagination": {
        "limit": 100,
        "offset": 0,
        "count": 100,
        "total": 293
    },
    "data": [
        {
            "author": "TMZ Staff",
            "title": "Rafael Nadal Pulls Out Of U.S. Open Over COVID-19 Concerns",
            "description": "Rafael Nadal is officially OUT of the U.S. Open ... the tennis legend said Tuesday it's just too damn unsafe for him to travel to America during the COVID-19 pandemic. \"The situation is very complicated worldwide,\" Nadal wrote in a statement. \"The…",
            "url": "https://www.tmz.com/2020/08/04/rafael-nadal-us-open-tennis-covid-19-concerns/",
            "source": "TMZ.com",
            "image": "https://imagez.tmz.com/image/fa/4by3/2020/08/04/fad55ee236fc4033ba324e941bb8c8b7_md.jpg",
            "category": "general",
            "language": "en",
            "country": "us",
            "published_at": "2020-08-05T05:47:24+00:00"
        },
        [...]
    ]
}

example_media_stack_api_error = {
   "error": {
      "code": "validation_error",
      "message": "Validation error",
      "context": {
         "date": [
            "NO_SUCH_CHOICE_ERROR"
         ]
      }
   }
}



if __name__ == '__main__':
    media_stack = MediaStack()
    data = media_stack.fetch_news()
    print(data)
