from flask import g, jsonify, request
from flask_restx import Namespace, Resource

from src.apps import token_required
from src.lib.authentication.auth_token import UserToken
from src.models.user.user_model import User, UserMe, UserMePreferences

ns_user = Namespace('user', description='User related operations')


@ns_user.route('/me')
class UserMeResource(Resource):

    @token_required
    @ns_user.marshal_with(UserMe.to_model(name_space=ns_user))
    def get(self):
        user_token: UserToken = g.user

        user_me = UserMe.get(user_id=user_token.user_id)
        return user_me.to_json()

    @token_required
    @ns_user.expect(UserMe.to_model(name_space=ns_user))
    @ns_user.marshal_with(UserMe.to_model(name_space=ns_user))
    def post(self):
        user_token: UserToken = g.user

        data = request.get_json()
        post_data = UserMe(**data)

        user = User.get(user_id=user_token.user_id)

        if user is None:
            return jsonify({"message": "Invalid user"}), 400

        user.update(post_data)
        is_updated = user.update_user()
        if is_updated:
            # TODO: force to update token with new name value
            return jsonify(user.to_json())
        return jsonify({"message": "Error during update"}), 400


@ns_user.route('/me/preference')
class UserMePreferenceResource(Resource):

    @token_required
    @ns_user.marshal_with(UserMePreferences.to_model(name_space=ns_user))
    def get(self):
        user_token: UserToken = g.user

        user_preferences = UserMePreferences.get_preferences(user_id=user_token.user_id)
        return user_preferences.to_json()

    @token_required
    @ns_user.expect(UserMePreferences.to_model(name_space=ns_user))
    def post(self):
        user_token: UserToken = g.user

        data = request.get_json()
        post_data = UserMePreferences(**data)
        user = User.get(user_id=user_token.user_id)
        if user is None:
            return jsonify({"message": "Invalid user"}), 400
        user.update(post_data)
        is_updated = user.update_user()
        if is_updated:
            return jsonify(user.to_json())
        return jsonify({"message": "Error during update"}), 400

