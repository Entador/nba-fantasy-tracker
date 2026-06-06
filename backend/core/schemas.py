"""Shared Pydantic base models."""

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    """Base for response models read from ORM objects.

    Sets `from_attributes=True` once so subclasses can be built from SQLAlchemy
    rows (`Model.model_validate(orm_obj)`) without repeating the config.
    """

    model_config = ConfigDict(from_attributes=True)
