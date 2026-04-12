from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

ModelT = TypeVar("ModelT")


class Repository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, object_id: str) -> ModelT | None:
        return await self.session.get(self.model, object_id)

    async def list(self, *, limit: int = 100, offset: int = 0) -> list[ModelT]:
        result = await self.session.scalars(select(self.model).offset(offset).limit(limit))
        return list(result)

    def add(self, model: ModelT) -> ModelT:
        self.session.add(model)
        return model
