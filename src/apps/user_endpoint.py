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

        user_me = User.get(user_id=user_token.user_id)

        return user_me.to_me_json()

    @token_required
    @ns_user.expect(UserMe.to_model(name_space=ns_user))
    @ns_user.marshal_with(UserMe.to_model(name_space=ns_user))
    def post(self):
        user_token: UserToken = g.user

        data = request.get_json()

        firstname = data.get('firstname', None)
        lastname = data.get('lastname', None)
        address = data.get('address', None)

        user = User.get(user_id=user_token.user_id)

        if user is None:
            return jsonify({"message": "Invalid user"}), 400

        user.firstname = firstname
        user.lastname = lastname
        user.address = Address(**address) if address else None

        is_updated = user.update_user()
        if is_updated:
            # TODO: force to update token with new name value
            return jsonify(user.to_me_json())
        return jsonify({"message": "Error during update"}), 40


@ns_user.route('/me/preference')
class UserMePreferenceResource(Resource):

    @token_required
    @ns_user.marshal_with(Model.get_list_of_string_model(name_space=ns_user))
    def get(self):
        user_token: UserToken = g.user

        user = User.get(user_id=user_token.user_id)

        if user is None:
            return jsonify({"message": "Invalid user"}), 400

        return user.to_preferences_json()

    @token_required
    @ns_user.expect(Model.get_list_of_string_model(name_space=ns_user))
    @ns_user.marshal_with(Model.get_list_of_string_model(name_space=ns_user))
    def post(self):
        user_token: UserToken = g.user

        data = request.get_json()

        preferences = data.get('preferences', [])

        user = User.get(user_id=user_token.user_id)
        if user is None:
            return jsonify({"message": "Invalid user"}), 400
        user.preferences = preferences

        is_updated = user.update_user()
        if is_updated:
            return jsonify(user.to_preferences_json())
        return jsonify({"message": "Error during update"}), 400

