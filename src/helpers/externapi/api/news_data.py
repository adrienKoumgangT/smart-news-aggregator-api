import time
from typing import Optional, List

import requests

from src.helpers.externapi.externapi_base import ExternApiBase, LogRequest, LogRequestRequest, LogRequestResponse
from src.lib.configuration import configuration
from src.lib.log.api_logger import ApiLogger, EnumColor
from src.models.article.article_model import ArticleModel, ArticleSourceModel


class NewsData(ExternApiBase):
    api_name = "NewsData"
    base_url = "https://newsdata.io/api/1/latest"
    data_field = "results"
    page_size = 100

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.api_key = api_key if api_key else configuration.get_env_var("externapi.newsdata.api_key")

    def fetch_news(self) -> List[dict]:
        """
        Fetch news from News Data API.
        """
        if self.api_key:
            api_log = ApiLogger(f"Retrieving news from {self.api_name} API.")

            all_articles = []

            params = {
                'apikey': f'{self.api_key}'
            }

            request_number = 0
            while True:
                request_number += 1
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

                    params['page'] = response_data['nextPage']
                else:
                    try:
                        ApiLogger(f"Error while fetching news from {self.api_name} API: status code: {response.status_code} --- info {response.json()}", color=EnumColor.RED)
                    except Exception as e:
                        ApiLogger(f"Error while fetching news from {self.api_name} API: {e}", color=EnumColor.RED)
                    break

                if request_number >= 5:
                    break

                time.sleep(1)

            api_log.print_log(extend_message=f"Retrieved {len(all_articles)} articles")
            return all_articles

        return []

    @classmethod
    def to_article(cls, data: dict) -> ArticleModel:
        return ArticleModel(
            _id=None,
            extern_id=data.get('article_id'),
            extern_api=cls.api_name,

            title=data.get('title'),
            description=data.get('description'),
            content=data.get('content'),
            url=data.get('link'),
            author=ArticleSourceModel(
                name=data.get('creator')[0] if data.get('creator') else None,
                url=None
            ),
            source=ArticleSourceModel(
                name=data.get('source_name') if data.get('source_name') else data.get('source_id'),
                url=data.get('source_url')
            ),
            image_url=data.get('image_url'),
            published_at=data.get('pubDate'),
            language=data.get('language'),
            country=data.get('country')[0] if data.get('country') else None,
            tags=(data.get('keywords', []) if data.get('keywords') else [])
        )


example_news_data = {
    "status": "success",
    "totalResults": 1514,
    "results": [
        {
            "article_id": "41fe05dd7f354f41d6b9e3e4ba5e8c9a",
            "title": "Marcos declines resignation of DICT chief Aguda",
            "link": "https://newsinfo.inquirer.net/2066428/fwd-bbm-declines-resignation-of-aguda-as-dict-chief-ca-suspends-confirmation-of-his-appointment-due-to-lack-of-material-time",
            "keywords": [
                "dict",
                "latest news stories",
                "nation",
                "bongbong marcos jr."
            ],
            "creator": None,
            "description": "MANILA, Philippines – President Ferdinand R. Marcos Jr.has declined the resignation of Department of Information and Communications Technology (DICT) chief Henry Rhoel Aguda Aguda disclosed this before the Committee on Appointments’ panel on information and communications technology on Tuesday. “I received a call from the executive secretary that my resignation was declined by the President.",
            "content": "DICT chief Henry Rhoel Aguda (Photo from DICT/Facebook) MANILA, Philippines – President Ferdinand R. Marcos Jr.has declined the resignation of Department of Information and Communications Technology (DICT) chief Henry Rhoel Aguda Aguda disclosed this before the Committee on Appointments’ panel on information and communications technology on Tuesday. “I received a call from the executive secretary that my resignation was declined by the President. Just for the record, it’s almost the day after the courtesy resignation was hoisted,” said Aguda. He submitted his courtesy resignation following Marcos’ order for all his Cabinet secretaries to resign in a bid to recalibrate the administration following the midterm election results. The CA panel, meanwhile, suspended the consideration of Aguda’s appointment due to a lack of material time. Aguda took the helm of the DICT in March, replacing Ivan Uy, who resigned from his post in February. Before he was appointed DICT chief, Aguda was the president and chief executive of UnionDigital Bank. He also previously served as the Digital Infrastructure Lead at the Private Sector Advisory Council created by Marcos to assist his administration in boosting innovative synergies between the private and public sectors. Aguda has experience across the banking, technology, and telecommunications industries. Subscribe to our daily newsletter By providing an email address. I agree to the Terms of Use and acknowledge that I have read the Privacy Policy .",
            "pubDate": "2025-06-03 06:18:19",
            "pubDateTZ": "UTC",
            "image_url": "https://newsinfo.inquirer.net/files/2025/03/aguda-dict-03212025.jpg",
            "video_url": None,
            "source_id": "inquirer",
            "source_name": "Inquirer",
            "source_priority": 9835,
            "source_url": "https://www.inquirer.net",
            "source_icon": "https://n.bytvi.com/inquirer.png",
            "language": "english",
            "country": [
                "philippines"
            ],
            "category": [
                "top"
            ],
            "sentiment": "neutral",
            "sentiment_stats": {
                "positive": 0.19,
                "neutral": 96.03,
                "negative": 3.78
            },
            "ai_tag": [
                "politics"
            ],
            "ai_region": [
                "manila,metro manila,philippines,asia",
                "philippines,asia"
            ],
            "ai_org": [
                "dict",
                "department of information and communications technology"
            ],
            "duplicate": False
        }
    ],
    "nextPage": "1748935140887478048"
}


if __name__ == '__main__':
    news_data = NewsData()
    data = news_data.fetch_news()
    print(data)




