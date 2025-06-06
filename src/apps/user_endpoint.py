from flask import g, jsonify
from flask_restx import Namespace, Resource

from src.apps import token_required
from src.lib.authentication.auth_token import UserToken
from src.models.user.user_model import User, UserMe

ns_user = Namespace('user', description='User related operations')


@ns_user.route('/me')
class UserMeResource(Resource):

    @token_required
    @ns_user.marshal_with(UserMe.to_model(name_space=ns_user))
    def get(self):
        user_token: UserToken = g.user

        user = User.get_by_email(user_token.email)

        if user is None:
            return jsonify({"message": "Invalid user"}), 400

        user_me = UserMe.from_user(user)
        return jsonify(user_me.to_json())

