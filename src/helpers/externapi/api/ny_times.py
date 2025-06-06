import time
from typing import Optional, List

import requests

from src.helpers.externapi.externapi_base import ExternApiBase
from src.lib.configuration import configuration
from src.lib.log.api_logger import ApiLogger, EnumColor
from src.models.article.article_model import ArticleModel, ArticleSourceModel


# https://developer.nytimes.com/docs/articlesearch-product/1/overview
class NYTimes(ExternApiBase):
    api_name = "NewYork Times"
    base_url = "https://api.nytimes.com/svc/search/v2/articlesearch.json"
    limit = 100
    data_field = "response"

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.api_key = api_key if api_key else configuration.get_configuration("externapi.nytimes.api_key")

    def fetch_news(self) -> List[dict]:
        """
        Fetch news from Market Aux API.
        """
        if self.api_key:
            api_log = ApiLogger(f"Retrieving news from {self.api_name} API.")

            all_articles = []

            params = {
                'api-key': f'{self.api_key}',
                'page': 0
            }

            while True:
                response = requests.get(self.base_url, params=params)
                status_code = response.status_code
                response_data = response.json()
                is_success = status_code == 200 and self.data_field in response_data

                fetched_count = len(response_data[self.data_field]['docs']) if status_code == 200 and self.data_field in response_data else None
                total_articles = response_data['metadata']['hits'] if status_code == 200 and 'metadata' in response_data else None

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
                    all_articles.extend(response_data[self.data_field]['docs'])

                    params['page'] += 1
                else:
                    try:
                        ApiLogger(f"Error while fetching news from {self.api_name} API: status code: {response.status_code} --- info {response.json()}", color=EnumColor.RED)
                    except Exception as e:
                        ApiLogger(f"Error while fetching news from {self.api_name} API: {e}", color=EnumColor.RED)
                    break

                if params['page'] >= 10:
                    break

                time.sleep(1)

            api_log.print_log(extend_message=f"Retrieved {len(all_articles)} articles")
            return all_articles

        return []

    @classmethod
    def to_article(cls, data: dict) -> ArticleModel:
        return ArticleModel(
            _id=None,
            extern_id=data.get('_id'),
            extern_api=cls.api_name,

            title=data.get('abstract'),
            description=data.get('headline').get('main'),
            content=data.get('snippet'),
            url=data.get('web_url'),
            author=None,
            source=ArticleSourceModel(
                name=data.get('source'),
                url=None
            ),
            image_url=data['multimedia']['default']['url'] if 'multimedia' in data and 'default' in data['multimedia'] and 'url' in data['multimedia']['default'] else None,
            published_at=data.get('pub_date'),
            language=data.get('language'),
            country=data.get('country'),
            tags=[k['value'] for k in data['keywords']] if data.get('keywords') else [],
        )


if __name__ == '__main__':
    ny = NYTimes()
    data= ny.fetch_news()
    print(data)


