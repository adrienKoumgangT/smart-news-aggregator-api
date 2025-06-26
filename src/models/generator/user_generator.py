import random
from datetime import datetime

import requests

from src.lib.authentication.password import hash_password
from src.models.article.article_model import ArticleModel
from src.models.user.user_model import User


def generate_random_user(num_users: int = 1):
    tags = ArticleModel.get_all_tags()

    url = f'https://randomuser.me/api/?results={num_users}'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()

        print(f'Successfully generated random {len(data['results'])} users')

        user_number = 0
        for user_info in data['results']:

            # Extract fields from response
            registered_date_str = data["results"][0]["registered"]["date"]

            n = random.randint(0, 20)
            random_tags_list = []
            for i in range(n):
                random_number = random.randint(0, len(tags)-1)
                if tags[random_number] not in random_tags_list:
                    random_tags_list.append(tags[random_number])

            user_data = {
                "firstname": user_info['name']['first'],
                "lastname": user_info['name']['last'],
                "email": user_info['email'],
                "phone": user_info['phone'],
                "cell": user_info['cell'],
                "address": {
                    "street": f"{user_info['location']['street']['name']} {user_info['location']['street']['number']}",
                    "city": user_info['location']['city'],
                    "state": user_info['location']['state'],
                    "zip": str(user_info['location']['postcode']),
                    "country": user_info['location']['country']
                },
                # "password": user_info['login']['password'],
                "password": hash_password(user_info['login']['password']),
                # "username": user_info['login']['username'],

                "account": {
                    "status": "active",
                    "role": "user"
                },
                "preferences": random_tags_list,
                "preferences_enable": random.randint(0, 1) > 0,

                "created_at": datetime.fromisoformat(registered_date_str.replace("Z", "+00:00")),
            }

            # print(user_info)
            # print(user)
            # print()

            user = User(**user_data)
            user.save()

            user_number += 1

        print(f'Successfully saved {user_number} users')
    else:
        raise Exception("Failed to fetch user")


if __name__ == '__main__':

    # Example usage
    generate_random_user(num_users=5000)


