"""Generic CRUD repository over a SQLAlchemy model.

The repository layer isolates persistence concerns from the service/business
layer (Clean Architecture). Concrete repositories subclass
:class:`BaseRepository` and may add entity-specific queries.
"""

from __future__ import annotations

from typing import Generic, List, Optional, Sequence, Type, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Reusable CRUD operations bound to a single ORM ``model``.

    Parameters
    ----------
    model:
        The SQLAlchemy mapped class this repository manages.
    db:
        An active :class:`~sqlalchemy.orm.Session`.
    """

    def __init__(self, model: Type[ModelT], db: Session) -> None:
        self.model = model
        self.db = db

    def get(self, obj_id: int) -> Optional[ModelT]:
        """Return the row with primary key ``obj_id`` or ``None``."""
        return self.db.get(self.model, obj_id)

    def get_by(self, **filters: object) -> Optional[ModelT]:
        """Return the first row matching equality ``filters`` or ``None``."""
        stmt = select(self.model).filter_by(**filters).limit(1)
        return self.db.execute(stmt).scalar_one_or_none()

    def list(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        order_desc: bool = True,
    ) -> Sequence[ModelT]:
        """Return a page of rows ordered by primary key."""
        pk = list(self.model.__table__.primary_key.columns)[0]
        order = pk.desc() if order_desc else pk.asc()
        stmt = select(self.model).order_by(order).offset(skip).limit(limit)
        return self.db.execute(stmt).scalars().all()

    def count(self) -> int:
        """Return the total number of rows for the model."""
        stmt = select(func.count()).select_from(self.model)
        return int(self.db.execute(stmt).scalar_one())

    def add(self, obj: ModelT, *, flush: bool = True) -> ModelT:
        """Persist a new instance; flush to populate its primary key."""
        self.db.add(obj)
        if flush:
            self.db.flush()
        return obj

    def add_all(self, objs: List[ModelT]) -> List[ModelT]:
        """Bulk-persist a list of instances."""
        self.db.add_all(objs)
        self.db.flush()
        return objs

    def delete(self, obj: ModelT) -> None:
        """Mark an instance for deletion."""
        self.db.delete(obj)

    def commit(self) -> None:
        """Commit the current transaction."""
        self.db.commit()
