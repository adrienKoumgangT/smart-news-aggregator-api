from flask_restx import fields


class Model:

    @staticmethod
    def get_list_of_string_model(name_space):
        return name_space.model('ListStringModel', {
                'preferences': fields.List(fields.String, description="List of string ..."),
            })

