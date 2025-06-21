from flask import g, jsonify, request
from flask_restx import Namespace, Resource

from src.apps import token_required
from src.lib.authentication.auth_token import UserToken
from src.models.model import Model
from src.models.user.user_model import User, UserMe, UserMePreferences, Address

ns_user = Namespace('user', description='User related operations')


@ns_user.route('/me')
class UserMeResource(Resource):

    @token_required
    @ns_user.marshal_with(UserMe.to_model(name_space=ns_user))
    def get(self):
        user_token: UserToken = g.user

        user_me = User.get(user_id=user_token.user_id).to_me()

        return user_me.to_json()

    @token_required
    @ns_user.expect(UserMe.to_model(name_space=ns_user))
    @ns_user.marshal_with(UserMe.to_model(name_space=ns_user))
    def post(self):
        user_token: UserToken = g.user

        data = request.get_json()

        firstname = data.get('firstname', None)
        lastname = data.get('lastname', None)
        address = data.get('address', None)

        user = User.get_directly(user_id=user_token.user_id)

        if user is None:
            return jsonify({"message": "Invalid user"}), 400

        user.firstname = firstname
        user.lastname = lastname
        user.address = Address(**address) if address else None

        is_updated = user.update_user()
        if is_updated:
            # TODO: force to update token with new name value
            return jsonify(user.to_me().to_json())
        return jsonify({"message": "Error during update"}), 400


@ns_user.route('/article/preference')
class UserMePreferenceResource(Resource):

    @token_required
    @ns_user.marshal_with(UserMePreferences.to_model(name_space=ns_user))
    def get(self):
        user_token: UserToken = g.user

        user = User.get(user_id=user_token.user_id)

        if user is None:
            return jsonify({"message": "Invalid user"}), 400

        return user.to_preferences_json()

    @token_required
    @ns_user.expect(UserMePreferences.to_model(name_space=ns_user))
    @ns_user.marshal_with(UserMePreferences.to_model(name_space=ns_user))
    def post(self):
        user_token: UserToken = g.user

        data = request.get_json()

        preferences = data.get('preferences', [])
        preferences_enable = data.get('preferences_enable', True)

        user = User.get_directly(user_id=user_token.user_id)
        if user is None:
            return jsonify({"message": "Invalid user"}), 400
        user.preferences = preferences
        user.preferences_enable = preferences_enable

        is_updated = user.update_user()
        if is_updated:
            return user.to_preferences_json()
        return jsonify({"message": "Error during update"}), 400

