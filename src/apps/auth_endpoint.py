from datetime import datetime, timezone

from flask import request, make_response, jsonify, g
from email_validator import validate_email, EmailNotValidError
from flask_restx import Namespace, Resource

from src.apps import token_required
from src.lib.authentication.password import hash_password, check_password
from src.lib.authentication.auth_token import TokenManager
from src.models.model import Model
from src.models.user.auth_event_model import AuthEventLogModel
from src.models.user.auth_model import LoginModel, RegisterModel, ChangePasswordModel, UserToken
from src.models.user.user_model import User, Account, PasswordHistory


ns_auth = Namespace('auth', description='Authentication operations')


@ns_auth.route('/register')
class RegisterResource(Resource):

    @ns_auth.expect(RegisterModel.to_model(name_space=ns_auth))
    @ns_auth.marshal_with(Model.get_message_response_model(name_space=ns_auth))
    @ns_auth.response(201, "User registered")
    def post(self):
        # Retrieve form data
        data = request.get_json()
        register_data = RegisterModel(**data)

        error = None

        if not register_data.firstname:
            error = "First name is required."
        elif not register_data.lastname:
            error = "Last name is required."
        elif not register_data.email:
            error = "Email is required."
        elif not register_data.password:
            error = "Password is required."
        elif not register_data.confirm_password:
            error = "Confirm password is required."

        try:
            validate_email(register_data.email)
        except EmailNotValidError:
            error = "Invalid email address."

        if error is None:
            if register_data.password != register_data.confirm_password:
                return {"success": False, "message": "Passwords do not match!"}, 400

            user = User.get_by_email(register_data.email)
            if user:
                return {"success": False, "message": "User already exists"}, 400

            current_datetime = datetime.now(timezone.utc)

            hashed_password = hash_password(register_data.password)

            user = User(
                _id=None,
                firstname=register_data.firstname,
                lastname=register_data.lastname,
                email=register_data.email,
                password=hashed_password,
                account=Account(status="active", role="user"),
                password_history=[PasswordHistory(password=hashed_password, created_at=current_datetime)],

                created_at=current_datetime,
                updated_at=current_datetime
            )
            user_token = UserToken(user_id='', firstname=user.firstname, lastname=user.lastname, email=user.email, role="user", status="active")
            user.save(user_token)

            user = User.get_by_email(user.email)

            if user is not None:
                auth_event_log = AuthEventLogModel.from_request(request=request, event='register', is_success=True, message='Registration successful!')
                auth_event_log.save()

                return {"success": True, "message": "Registration successful!"}, 201
            error = 'Error during insert user'

        auth_event_log = AuthEventLogModel.from_request(request=request, event='register', is_success=False, message=error)
        auth_event_log.save()

        return {"success": False, "message": error}, 400


@ns_auth.route('/login')
class LoginResource(Resource):

    @ns_auth.expect(LoginModel.to_model(name_space=ns_auth))
    @ns_auth.response(200, "Login successful")
    def post(self):
        data = request.get_json()

        login_data = LoginModel(**data)
        error = None

        if not login_data.email:
            error = "Email is required."
        elif not login_data.password:
            error = "Password is required."

        try:
            validate_email(login_data.email)
        except EmailNotValidError:
            error = "Invalid email address."

        if error is None:
            user = User.get_by_email(login_data.email)

            if user is None:
                error = "User does not exist."

            if error is None:
                if check_password(login_data.password, user.password):
                    token = TokenManager.generate_token(
                        user_id=str(user.user_id),
                        user_data=UserToken.from_user(user=user)
                    )

                    # Create response and set Authorization header
                    response = make_response(jsonify({"success": True, "message": "Login successful!"}))
                    response.headers["Authorization"] = f"Bearer {token}"

                    auth_event_log = AuthEventLogModel.from_request(request=request, event='login', is_success=True, message='Login successful!')
                    auth_event_log.save()

                    return response
                else:
                    error = "Incorrect password."

        auth_event_log = AuthEventLogModel.from_request(request=request, event='login', is_success=False, message=error)
        auth_event_log.save()

        return {"success": False, "message": error}, 400


@ns_auth.route('/login-alt')
class LoginAlternativeResource(Resource):

    @ns_auth.expect(LoginModel.to_model(name_space=ns_auth))
    @ns_auth.response(200, "Login successful")
    def post(self):
        data = request.get_json()

        login_data = LoginModel(**data)
        error = None

        if not login_data.email:
            error = "Email is required."
        elif not login_data.password:
            error = "Password is required."

        try:
            # validated = validate_email(login_data.email)
            pass
        except EmailNotValidError:
            error = "Invalid email address."

        if error is None:
            user = User.get_by_email(login_data.email)

            if user is None:
                error = "User does not exist."

            if error is None:

                # is_valid_password = check_password(login_data.password, user.password)
                is_valid_password = True

                if is_valid_password:
                    # Generate JWT token
                    token = TokenManager.generate_token(
                        user_id=str(user.user_id),
                        user_data=UserToken.from_user(user=user)
                    )

                    # Create response and set Authorization header
                    response = make_response(jsonify({"success": True, "message": "Login successful!"}))
                    response.headers["Authorization"] = f"Bearer {token}"

                    auth_event_log = AuthEventLogModel.from_request(request=request, event='login', is_success=True, message='Login successful!')
                    auth_event_log.save()

                    return response
                else:
                    error = "Incorrect password."

        auth_event_log = AuthEventLogModel.from_request(request=request, event='login', is_success=False, message=error)
        auth_event_log.save()

        return {"success": False, "message": error}, 400


@ns_auth.route('/change_password')
class ChangePasswordResource(Resource):
    @ns_auth.expect(ChangePasswordModel.to_model(name_space=ns_auth))
    @ns_auth.response(200, "Change password successful")
    def post(self):
        data = request.get_json()

        change_password_data = ChangePasswordModel(**data)

        user_token: UserToken = g.user

        user = User.get(user_token, user_token.user_id)
        is_valid_password = check_password(change_password_data.old_password, user.password)

        if is_valid_password:
            is_update = User.update_password(user_token, user_token.user_id, change_password_data.password)
            if is_update:
                auth_event_log = AuthEventLogModel.from_request(request=request, event='change_password', is_success=True, message='Password updated!')
                auth_event_log.save()

                return {"success": True, "message": "Password updated!"}, 200
            else:
                error = "Update failed!"
        else:
            error = "Incorrect old password!"

        auth_event_log = AuthEventLogModel.from_request(request=request, event='change_password', is_success=False, message=error)
        auth_event_log.save()

        return {"success": False, "message": error}, 400


@ns_auth.route('/me')
class MeResource(Resource):
    @token_required
    @ns_auth.marshal_with(UserToken.to_model(name_space=ns_auth), code=200)
    def get(self):
        user_token: UserToken = g.user
        return user_token.to_json(), 200

