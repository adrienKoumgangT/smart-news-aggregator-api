from typing import Optional, List

import requests

from src.helpers.externapi.externapi_base import ExternApiBase
from src.lib.configuration import configuration
from src.lib.log.api_logger import ApiLogger, EnumColor
from src.models.article.article_model import ArticleModel, ArticleSourceModel


# https://gnews.io
class GNews(ExternApiBase):
    api_name = "GNews"
    base_url = "https://gnews.io/api/v4/search"
    data_field = "articles"

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.api_key = api_key if api_key else configuration.get_env_var("externapi.gnews.api_key")

    def fetch_news(self) -> List[dict]:
        """
        Fetch news from GNews API.
        """
        if self.api_key:
            api_log = ApiLogger(f"[EXTERN API] Retrieving news from {self.api_name} API.")

            all_articles = []

            params = {
                'apikey': f'{self.api_key}',
                'q': 'technology',
            }

            response = requests.get(self.base_url, params=params)
            status_code = response.status_code
            response_data = response.json()
            is_success = status_code == 200 and self.data_field in response_data

            fetched_count = len(response_data[self.data_field]) if status_code == 200 and self.data_field in response_data else None
            total_articles = response_data['totalArticles'] if status_code == 200 and 'totalArticles' in response_data else None

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
                name=data.get('source').get('name') if 'source' in data else None,
                url=data.get('source').get('url') if 'source' in data else None
            ),
            source=ArticleSourceModel(
                name=data.get('source').get('name') if 'source' in data else None,
                url=data.get('source').get('url') if 'source' in data else None
            ),
            image_url=data.get('image'),
            published_at=data.get('publishedAt'),
            language=None,
            country=None,
            tags=[]
        )



example_gnews_api_response = {
  "totalArticles": 54904,
  "articles": [
    {
      "title": "Google's Pixel 7 and 7 Pro’s design gets revealed even more with fresh crisp renders",
      "description": "Now we have a complete image of what the next Google flagship phones will look like. All that's left now is to welcome them during their October announcement!",
      "content": "Google’s highly anticipated upcoming Pixel 7 series is just around the corner, scheduled to be announced on October 6, 2022, at 10 am EDT during the Made by Google event. Well, not that there is any lack of images showing the two new Google phones, b... [1419 chars]",
      "url": "https://www.phonearena.com/news/google-pixel-7-and-pro-design-revealed-even-more-fresh-renders_id142800",
      "image": "https://m-cdn.phonearena.com/images/article/142800-wide-two_1200/Googles-Pixel-7-and-7-Pros-design-gets-revealed-even-more-with-fresh-crisp-renders.jpg",
      "publishedAt": "2022-09-28T08:14:24Z",
      "source": {
        "name": "PhoneArena",
        "url": "https://www.phonearena.com"
      }
    },
    [...]
  ]
}


if __name__ == '__main__':
    gnews_api = GNews()
    data = gnews_api.fetch_news()
    print(data)
