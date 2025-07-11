from typing import Optional, List

import requests

from src.helpers.externapi.externapi_base import ExternApiBase
from src.lib.configuration import configuration
from src.lib.log.api_logger import ApiLogger, EnumColor
from src.models.article.article_model import ArticleModel, ArticleSourceModel


# https://newsapi.org
class NewsApi(ExternApiBase):
    api_name = "NewsApi"
    base_url = "https://newsapi.org/v2/everything"
    data_field = "articles"

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.api_key = api_key if api_key else configuration.get_env_var("externapi.newsapi.api_key")

    def fetch_news(self) -> List[dict]:
        """
        Fetch news from News API.
        """
        if self.api_key:
            api_log = ApiLogger(f"Retrieving news from {self.api_name} API.")

            all_articles = []

            params = {
                'apiKey': f'{self.api_key}',
                'sortBy': 'publishedAt',
                'q': 'technology',
            }

            response = requests.get(self.base_url, params=params)
            status_code = response.status_code
            response_data = response.json()
            is_success = status_code == 200 and self.data_field in response_data

            fetched_count = len(response_data[self.data_field]) if status_code == 200 and self.data_field in response_data else None
            total_articles = response_data['totalResults'] if status_code == 200 and 'totalResults' in response_data else None

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
            else:
                try:
                    ApiLogger(f"Error while fetching news from {self.api_name} API: status code: {response.status_code} --- info {response.json()}", color=EnumColor.RED)
                except Exception as e:
                    ApiLogger(f"Error while fetching news from {self.api_name} API: {e}", color=EnumColor.RED)

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
                url=data.get('author')
            ),
            source=ArticleSourceModel(
                name=data.get('source').get('name') if data.get('source') else None,
                url=data.get('source').get('name') if data.get('source') else None
            ),
            image_url=data.get('urlToImage'),
            published_at=data.get('publishedAt'),
            language=data.get('language'),
            country=data.get('country'),
            tags=[data.get('category')] if data.get('category') else [],
        )


example_news_api = {
    "status": "ok",
    "totalResults": 8461,
    "articles": [
        {
            "source": {
                "id": None,
                "name": "Biztoc.com"
            },
            "author": "techcrunch.com",
            "title": "Tesla files new ‘Robotaxi’ trademark applications after prior attempt stalls",
            "description": "Tesla has filed trademark applications for the term “Tesla Robotaxi,” after the company’s previous attempts to secure trademarks for its planned self-driving vehicle service hit roadblocks. The company originally applied in October 2024 for the trademark of t…",
            "url": "https://biztoc.com/x/02c57ffeff48e8fe",
            "urlToImage": "https://biztoc.com/cdn/948/og.png",
            "publishedAt": "2025-06-02T17:48:07Z",
            "content": "Tesla has filed trademark applications for the term Tesla Robotaxi, after the companys previous attempts to secure trademarks for its planned self-driving vehicle service hit roadblocks. The company … [+138 chars]"
        },
        [...]
    ]
}


if __name__ == '__main__':
    news_api = NewsApi()
    data = news_api.fetch_news()
    print(data)


