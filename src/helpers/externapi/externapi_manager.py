import json
import os

from src.helpers.externapi.api.currents_api import CurrentsAPI
from src.helpers.externapi.api.g_news import GNews
from src.helpers.externapi.api.market_aux import MarketAux
from src.helpers.externapi.api.media_stack import MediaStack
from src.helpers.externapi.api.news_api import NewsApi
from src.helpers.externapi.api.news_data import NewsData
from src.helpers.externapi.api.ny_times import NYTimes
from src.helpers.externapi.api.space_flight_news_api import SpaceFlightNewsAPI

class ExternApiManager:

    @staticmethod
    def save_data_from_files(folder_name: str = "data"):
        folder_path = os.path.join(os.path.dirname(__file__), folder_name)
        print(folder_path)
        print()
        # files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
        # print(files[:5])

        all_files = []
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                all_files.append(os.path.join(root, file))

        # print(all_files[:5])
        # /Users/adrienkoumgangtegantchouang/PycharmProjects/smart-news-aggregator-api/src/helpers/externapi/data/2025/06/03/NewsData 21-30-54.json

        for file in all_files:
            print(file)
            with open(file) as f:
                data = json.loads(f.read())
                # print(data)

                if 'CurrentsAPI' in file:
                    if 'news' in data:
                        for article in data['news']:
                            current_data = CurrentsAPI.to_article(article)
                            print(current_data.to_json())
                            current_data.save()
                elif 'GNews' in file:
                    if 'articles' in data:
                        for article in data['articles']:
                            g_news = GNews.to_article(article)
                            print(g_news.to_json())
                            g_news.save()
                elif 'MarketAux' in file:
                    if 'data' in data:
                        for article in data['data']:
                            market_aux = MarketAux.to_article(article)
                            print(market_aux.to_json())
                            market_aux.save()
                elif 'MediaStack' in file:
                    if 'data' in data:
                        for article in data['data']:
                            media_stack = MediaStack.to_article(article)
                            print(media_stack.to_json())
                            media_stack.save()
                elif 'NewsApi' in file:
                    if 'articles' in data:
                        for article in data['articles']:
                            news_api = NewsApi.to_article(article)
                            print(news_api.to_json())
                            news_api.save()
                elif 'NewsData' in file:
                    if 'results' in data:
                        for article in data['results']:
                            news_data = NewsData.to_article(article)
                            print(news_data.to_json())
                            news_data.save()
                elif 'NYTimes' in file:
                    if 'response' in data:
                        if 'docs' in data['response']:
                            for article in data['response']['docs']:
                                nytimes = NYTimes.to_article(article)
                                print(nytimes.to_json())
                                nytimes.save()
                elif 'SpaceFlightNewsAPI' in file:
                    if 'results' in data:
                        for article in data['results']:
                            spaceflight_news = SpaceFlightNewsAPI.to_article(article)
                            print(spaceflight_news.to_json())
                            spaceflight_news.save()

            print()

    @staticmethod
    def save_data_from_extern_files(folder_name: str = "extern_data"):
        folder_path = os.path.join(os.path.dirname(__file__), folder_name)
        print(folder_path)
        print()

        all_files = []
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                all_files.append(os.path.join(root, file))

        for file in all_files:
            print(file)
            with open(file) as f:
                data = json.loads(f.read())
                # print(data)

                for article in data:
                    news_data = NewsData.to_article(article)
                    print(news_data.to_json())
                    news_data.save()
            print()




if __name__ == '__main__':
    # ExternApiManager.save_data_from_files()
    ExternApiManager.save_data_from_extern_files()

