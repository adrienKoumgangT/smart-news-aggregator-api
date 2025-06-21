from flask_restx import fields, Namespace


class Model:

    @staticmethod
    def get_list_of_string_model(name_space: Namespace):
        return name_space.model('ListStringModel', {
                'preferences': fields.List(fields.String, description="List of string ..."),
            })

    @staticmethod
    def get_message_response_model(name_space: Namespace):
        return name_space.model('MessageResponseModel', {
            'success': fields.Boolean(required=True),
            'message': fields.String(required=True),
        })

    @staticmethod
    def get_search_model(name_space: Namespace):
        return name_space.model('SearchModel', {
            'search': fields.String(required=False),
        })

