import time
from typing import Optional, List

import requests

from src.helpers.externapi.externapi_base import ExternApiBase
from src.lib.configuration import configuration
from src.lib.log.api_logger import ApiLogger, EnumColor
from src.models.article.article_model import ArticleModel, ArticleSourceModel


# https://www.marketaux.com/documentation
class MarketAux(ExternApiBase):
    api_name = "MarketAux"
    base_url = "https://api.marketaux.com/v1/news/all"
    data_field = "data"

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.api_key = api_key if api_key else configuration.get_configuration("externapi.marketaux.api_key")

    def fetch_news(self) -> List[dict]:
        """
        Fetch news from Market Aux API.
        """
        if self.api_key:
            api_log = ApiLogger(f"[EXTERN API] Retrieving news from {self.api_name} API.")

            all_articles = []

            params = {
                'api_token': f'{self.api_key}',
                'limit': 100,
                'page': 1
            }

            num_request = 0
            while True:
                num_request += 1
                response = requests.get(self.base_url, params=params)
                status_code = response.status_code
                response_data = response.json()
                is_success = status_code == 200 and self.data_field in response_data

                fetched_count = len(response_data[self.data_field]) if status_code == 200 and self.data_field in response_data else None
                total_articles = response_data['meta']['found'] if status_code == 200 and 'meta' in response_data else None

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

                if response.status_code == 200 and self.data_field in response.json():
                    all_articles.extend(response_data[self.data_field])

                    params['page'] += 1
                else:
                    try:
                        ApiLogger(f"Error while fetching news from {self.api_name} API: status code: {response.status_code} --- info {response.json()}", color=EnumColor.RED)
                    except Exception as e:
                        ApiLogger(f"Error while fetching news from {self.api_name} API: {e}", color=EnumColor.RED)
                    break
                if num_request >= 5:
                    break

                time.sleep(1)

            api_log.print_log(extend_message=f"Retrieved {len(all_articles)} articles")
            return all_articles

        return []

    @classmethod
    def to_article(cls, data: dict) -> ArticleModel:
        return ArticleModel(
            _id=None,
            extern_id=data.get('uuid'),
            extern_api=cls.api_name,

            title=data.get('title'),
            description=data.get('description'),
            content=data.get('snippet'),
            url=data.get('url'),
            author=None,
            source=ArticleSourceModel(
                name=data.get('source'),
                url=data.get('source')
            ),
            image_url=data.get('image_url'),
            published_at=data.get('published_at'),
            language=data.get('language'),
            country=data.get('country'),
            tags=[phrase.strip() for phrase in data.get('keywords', '').split(",")]
        )


example_market_aux_api_response = {
    "meta": {
        "found": 2196,
        "returned": 10,
        "limit": 10,
        "page": 1
    },
    "data": [
        {
            "uuid": "57d4b70c-1184-4f4a-ac04-66cf36babfe5",
            "title": "Denny's: The $1 Slam That Could Cost A Fortune (NASDAQ:DENN)",
            "description": "Denny’s struggles with declining sales, compressed margins, and franchisee challenges despite aggressive promotions. See why DENN stock is a Hold.",
            "keywords": "",
            "snippet": "Since then, the stock has dropped more than 22.5% in just a little over three months. And it’s not like the broader market\n\nI am an Equity Analyst and Account...",
            "url": "https://seekingalpha.com/article/4791901-dennys-the-1-slam-that-could-cost-a-fortune",
            "image_url": "https://static.seekingalpha.com/cdn/s3/uploads/getty_images/1305390311/image_1305390311.jpg?io=getty-c-w1536",
            "language": "en",
            "published_at": "2025-06-03T10:15:17.000000Z",
            "source": "seekingalpha.com",
            "relevance_score": None,
            "entities": [
                {
                    "symbol": "DENN",
                    "name": "Denny's Corporation",
                    "exchange": None,
                    "exchange_long": None,
                    "country": "us",
                    "type": "equity",
                    "industry": "Consumer Cyclical",
                    "match_score": 84.39447,
                    "sentiment_score": -0.3818,
                    "highlights": [
                        {
                            "highlight": "<em>Denny's</em>: The $1 Slam That Could Cost A Fortune (<em>NASDAQ:DENN</em>)",
                            "sentiment": -0.3818,
                            "highlighted_in": "title"
                        }
                    ]
                }
            ],
            "similar": []
        },
        [...]
    ]
}



if __name__ == '__main__':
    market_aux = MarketAux()
    data = market_aux.fetch_news()
    print(data)
