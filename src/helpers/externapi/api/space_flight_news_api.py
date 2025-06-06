from typing import Optional, List

import requests

from src.helpers.externapi.externapi_base import ExternApiBase
from src.lib.configuration import configuration
from src.lib.log.api_logger import ApiLogger, EnumColor
from src.models.article.article_model import ArticleModel, ArticleSourceModel


class SpaceFlightNewsAPI(ExternApiBase):
    api_name = "SpaceFlightNewsAPI"
    base_url = "https://api.spaceflightnewsapi.net/v4/articles/?limit=500"
    data_field = "results"

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.api_key = api_key if api_key else configuration.get_configuration("externapi.spaceflightnewsapi.api_key")

    def fetch_news(self) -> List[dict]:
        """
        Fetch news from News API.
        """
        if self.api_key:
            api_log = ApiLogger(f"Retrieving news from {self.api_name} API.")

            all_articles = []

            url = self.base_url

            while url:
                response = requests.get(url)
                status_code = response.status_code
                response_data = response.json()
                is_success = status_code == 200 and self.data_field in response_data

                fetched_count = len(response_data[self.data_field]) if status_code == 200 and self.data_field in response_data else None
                total_articles = response_data['count'] if status_code == 200 and 'count' in response_data else None

                self.log_request(
                    api_name=self.api_name,
                    url=url,
                    headers={},
                    params={},
                    status_code=status_code,
                    data=response_data,
                    total_articles=total_articles,
                    fetched_count=fetched_count,
                    is_success=is_success
                )

                if is_success:
                    all_articles.extend(response_data[self.data_field])

                    url = response_data["next"]
                else:
                    try:
                        ApiLogger(f"Error while fetching news from {self.api_name} API: status code: {response.status_code} --- info {response.json()}", color=EnumColor.RED)
                    except Exception as e:
                        ApiLogger(f"Error while fetching news from {self.api_name} API: {e}", color=EnumColor.RED)
                    break

            api_log.print_log(extend_message=f"Retrieved {len(all_articles)} articles")
            return all_articles

        return []

    @classmethod
    def to_article(cls, data: dict) -> ArticleModel:
        return ArticleModel(
            _id=None,
            extern_id=str(data.get('id')),
            extern_api=cls.api_name,

            title=data.get('title'),
            description=data.get('summary'),
            content=None,
            url=data.get('url'),
            author=ArticleSourceModel(
                name=data.get('authors')[0].get('name'),
                url=None
            ) if 'authors' in data and data['authors'] else None,
            source=ArticleSourceModel(
                name=data.get('news_site'),
                url=None
            ),
            image_url=data.get('image_url'),
            published_at=data.get('published_at'),
            language=data.get('language'),
            country=data.get('country'),
            tags=[],
        )


example_space_flight_news_api = {
  "count": 123,
  "next": "http://api.example.org/accounts/?offset=400&limit=100",
  "previous": "http://api.example.org/accounts/?offset=200&limit=100",
  "results": [
    {
      "id": 0,
      "title": "string",
      "authors": [
        {
          "name": "string",
          "socials": {
            "x": "string",
            "youtube": "string",
            "instagram": "string",
            "linkedin": "string",
            "mastodon": "string",
            "bluesky": "string"
          }
        }
      ],
      "url": "string",
      "image_url": "string",
      "news_site": "string",
      "summary": "string",
      "published_at": "2025-06-03T19:33:32.304Z",
      "updated_at": "2025-06-03T19:33:32.304Z",
      "featured": True,
      "launches": [
        {
          "launch_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
          "provider": "string"
        }
      ],
      "events": [
        {
          "event_id": 2147483647,
          "provider": "string"
        }
      ]
    }
  ]
}



if __name__ == '__main__':
    space_flight_news_api = SpaceFlightNewsAPI()
    data = space_flight_news_api.fetch_news()
    print(data)

