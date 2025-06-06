from typing import Optional, List

import requests

from src.helpers.externapi.externapi_base import ExternApiBase
from src.lib.configuration import configuration
from src.lib.log.api_logger import ApiLogger
from src.models.article.article_model import ArticleModel, ArticleSourceModel


# https://currentsapi.services/en/docs/
class CurrentsAPI(ExternApiBase):
    api_name = "CurrentsAPI"
    base_url = "https://api.currentsapi.services/v1/latest-news"
    data_field = "news"

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.api_key = api_key if api_key else configuration.get_configuration("externapi.currentsapi.api_key")

    def fetch_news(self) -> List[dict]:
        """
        Fetch news from currents API.
        """
        if self.api_key:
            api_log = ApiLogger(f"[EXTERN API] Retrieving news from {self.api_name} API.")

            all_articles = []

            headers = {
                'Authorization': f'{self.api_key}'
            }

            response = requests.get(self.base_url, headers=headers)
            status_code = response.status_code
            response_data = response.json()
            is_success = status_code == 200 and self.data_field in response_data

            total_articles = None
            fetched_count = len(response_data[self.data_field]) if status_code == 200 and self.data_field in response_data else None

            self.log_request(
                api_name=self.api_name,
                url=self.base_url,
                headers=headers,
                params={},
                status_code=status_code,
                data=response_data,
                total_articles=total_articles,
                fetched_count=fetched_count,
                is_success=is_success
            )

            if is_success:
                all_articles.extend(response_data[self.data_field])

            api_log.print_log(extend_message=f"Retrieved {len(all_articles)} articles")
            return all_articles

        return []

    @classmethod
    def to_article(cls, data: dict) -> ArticleModel:
        return ArticleModel(
            _id=None,
            extern_id=data.get('id'),
            extern_api=cls.api_name,

            title=data.get('title'),
            description=data.get('description'),
            content=None,
            url=data.get('url'),
            author=ArticleSourceModel(name=data.get('author'), url=None),
            source=ArticleSourceModel(name=data.get('author'), url=None),
            image_url=None,
            published_at=data.get('published'),
            language=data.get('language'),
            country=None,
            tags= data.get('category', [])
        )


example_currents_api_response = {
    "status": "ok",
    "news": [
        {
            "id": "e1749cf0-8a49-4729-88b2-e5b4d03464ce",
            "title": "US House speaker Nancy Pelosi backs congressional legislation on Hong Kong",
            "description": "US House speaker Nancy Pelosi on Wednesday threw her support behind legislation meant to back Hong Kong's anti-government protesters.Speaking at a news conference featuring Hong Kong activists Joshua Wong Chi-fung and Denise Ho, who testified before the Congressional-Executive Commission on China (C...",
            "url": "https://www.scmp.com/news/china/politics/article/3027994/us-house-speaker-nancy-pelosi-backs-congressional-legislation",
            "author": "Robert Delaney",
            "image": "None",
            "language": "en",
            "category": [
                "world"
            ],
            "published": "2019-09-18 21:08:58 +0000"
        },
        [...]
    ]
}


if __name__ == '__main__':
    currents_api = CurrentsAPI()
    data = currents_api.fetch_news()
    print(data)
