from flask_restx import Namespace, fields

from src.lib.configuration import configuration
from src.lib.database.nosql.document.mongodb.mongodb_manager import mongodb_client
from src.models import DataBaseModel
# from src.models.user.user_model import User


class RegisterModel(DataBaseModel):
    firstname: str
    lastname: str
    email: str
    # phone: Optional[str] = None
    password: str
    confirm_password: str

    @staticmethod
    def to_model(name_space: Namespace):
        return name_space.model('RegisterModel', {
            'firstname': fields.String(required=True),
            'lastname': fields.String(required=True),
            'email': fields.String(required=True),
            # 'phone': fields.String(required=False),
            'password': fields.String(required=True),
            'confirm_password': fields.String(required=True),
        })


class LoginModel(DataBaseModel):
    email: str
    password: str

    @staticmethod
    def to_model(name_space: Namespace):
        return name_space.model('LoginModel', {
            'email': fields.String(required=True),
            'password': fields.String(required=True),
        })


class ChangePasswordModel(DataBaseModel):
    password: str
    old_password: str

    @staticmethod
    def to_model(name_space: Namespace):
        return name_space.model('ChangePasswordModel', {
            'password': fields.String(required=True),
            'old_password': fields.String(required=True),
        })



class UserToken(DataBaseModel):
    user_id: str
    firstname: str
    lastname: str
    email: str
    status: str
    role: str

    @classmethod
    def from_user(cls, user):
        return cls(
            user_id=str(user.user_id),
            firstname=user.firstname,
            lastname=user.lastname,
            email=user.email,
            status=user.account.status,
            role=user.account.role
        )

    @staticmethod
    def to_model(name_space: Namespace):
        return name_space.model('UserTokenModel', {
            'user_id': fields.String(required=True),
            'firstname': fields.String(required=True),
            'lastname': fields.String(required=True),
            'email': fields.String(required=True),
            'status': fields.String(required=True),
            'role': fields.String(required=True),
        })





