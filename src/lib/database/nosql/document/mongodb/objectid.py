from bson import ObjectId
from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema

class PydanticObjectId(ObjectId):
    """
    Custom ObjectId field compatible with Pydantic v2
    """

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: type, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_plain_validator_function(cls.validate)

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return cls(str(v))
        if isinstance(v, str):
            try:
                return cls(v)
            except Exception:
                raise ValueError(f"Invalid ObjectId string: {v}")
        raise TypeError(f"ObjectId must be str or ObjectId, got {type(v)}")

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        return {
            "type": "string",
            "examples": ["5eb7cf5a86d9755df3a6c593", "5eb7cfb05e32e07750a1756a"],
        }
