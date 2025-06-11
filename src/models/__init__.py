from pydantic import BaseModel


class DataBaseModel(BaseModel):

    def to_json(self) -> dict:
        return self.model_dump(by_alias=False, exclude_none=False)


class DataManagerBase:
    @staticmethod
    def collection():
        raise NotImplementedError()

