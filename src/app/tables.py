"""
Database table definitions (ORM models).

Each class here maps to a table; each attribute maps to a column. SQLAlchemy
turns these into `CREATE TABLE` statements and lets us work with rows as
ordinary Python objects.
"""
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _utcnow() -> datetime:
    """Timezone-aware 'now' in UTC — always store times in UTC."""
    return datetime.now(timezone.utc)


class Link(Base):
    __tablename__ = "links"

    # A big auto-incrementing primary key. On PostgreSQL this is BIGINT (room
    # for ~9 quintillion rows); on SQLite (tests) we fall back to INTEGER so
    # auto-increment behaves. Milestone 3 will base-62 encode this id into the
    # short code.
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )

    # The short code. `unique=True` enforces no duplicates at the DB level;
    # `index=True` builds a lookup index so redirects (which search by code)
    # are fast even with millions of rows.
    #
    # It's nullable ONLY so we can insert a row to obtain its id, then set the
    # code = base62(id) and update — all inside one transaction. A committed
    # row always has a code (never NULL).
    code: Mapped[str | None] = mapped_column(
        String(16), unique=True, index=True, nullable=True
    )

    # The original URL. Text has no length limit — URLs can be long.
    long_url: Mapped[str] = mapped_column(Text, nullable=False)

    # When the link was created. Filled in automatically.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    # ORM relationship: link.clicks gives all Click rows for this link.
    # cascade="all, delete-orphan" means deleting a link deletes its clicks.
    clicks: Mapped[list["Click"]] = relationship(
        back_populates="link", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # helps when debugging / in the shell
        return f"<Link code={self.code!r} url={self.long_url!r}>"


class Click(Base):
    """One row per redirect — the raw analytics event."""

    __tablename__ = "clicks"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )

    # Foreign key: every click belongs to exactly one link. `index=True` makes
    # "count the clicks for this link" queries fast. ON DELETE CASCADE means a
    # link's clicks are removed with it.
    link_id: Mapped[int] = mapped_column(
        ForeignKey("links.id", ondelete="CASCADE"), index=True, nullable=False
    )

    clicked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    # Where the click came from (HTTP "Referer" header) — may be absent.
    referrer: Mapped[str | None] = mapped_column(Text, nullable=True)

    # The visitor's browser/device (HTTP "User-Agent" header) — may be absent.
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    # The other side of the relationship: click.link gives the parent Link.
    link: Mapped["Link"] = relationship(back_populates="clicks")

    def __repr__(self) -> str:
        return f"<Click link_id={self.link_id} at={self.clicked_at!r}>"
