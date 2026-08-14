from pydantic import BaseModel


def to_json(model: BaseModel, exclude=None):
    return model.model_dump_json(ensure_ascii=False, indent=2, exclude=exclude) if model else None