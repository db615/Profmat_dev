"""Common helpers for route modules."""

from uuid import UUID

from fastapi import HTTPException


def commit(session, instance):
    session.add(instance)
    session.commit()
    session.refresh(instance)
    return instance


def get_owned(session, model, resource_id: UUID, user_id: UUID):
    instance = session.get(model, resource_id)
    if instance is None or instance.user_id != user_id:
        raise HTTPException(status_code=404, detail=f"{model.__name__} not found")
    return instance
