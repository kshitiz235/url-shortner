"""
CRUD layer — the functions that Create/Read/Update/Delete rows.

Keeping database operations here (instead of inside the route handlers) means
the routes stay thin and this logic is easy to test and reuse. Each function
takes a `Session` so the caller controls the transaction lifecycle.
"""
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import base62
from .tables import Click, Link


def create_link(db: Session, long_url: str) -> Link:
    """Insert a new link and give it a base-62 code derived from its id.

    Because the code is derived from the row's unique id, it is guaranteed
    unique — no collision checking or retry loop needed (unlike the random
    codes we used in Milestones 1-2).

    The two-step dance:
      1. add + flush  -> sends the INSERT and lets the DB assign `id`,
                         without committing yet.
      2. set code from base62(id), then commit -> makes it permanent.
    """
    link = Link(long_url=long_url)  # no code yet — we need the id first
    db.add(link)
    db.flush()                      # INSERT now; link.id is populated
    link.code = base62.encode(link.id)
    db.commit()
    db.refresh(link)                # reload final row (id, code, created_at)
    return link


def get_link_by_code(db: Session, code: str) -> Link | None:
    """Return the Link for a code, or None if it doesn't exist.

    This uses the index on `code`, so it's fast even with a huge table.
    """
    return db.scalar(select(Link).where(Link.code == code))


def add_click(
    db: Session, link_id: int, referrer: str | None, user_agent: str | None
) -> None:
    """Insert one click event for a link."""
    db.add(Click(link_id=link_id, referrer=referrer, user_agent=user_agent))
    db.commit()


def get_click_stats(db: Session, link: Link) -> dict:
    """Aggregate click analytics for a link using SQL COUNT / MAX / GROUP BY.

    Returns total clicks, the most recent click time, and the top referrers.
    Doing the aggregation in the database (not in Python) is far more efficient
    than loading every click row.
    """
    total: int = db.scalar(
        select(func.count(Click.id)).where(Click.link_id == link.id)
    ) or 0

    last_clicked: datetime | None = db.scalar(
        select(func.max(Click.clicked_at)).where(Click.link_id == link.id)
    )

    # Top 5 referrers by click count.
    top_referrers = db.execute(
        select(Click.referrer, func.count(Click.id).label("count"))
        .where(Click.link_id == link.id)
        .group_by(Click.referrer)
        .order_by(func.count(Click.id).desc())
        .limit(5)
    ).all()

    return {
        "total_clicks": total,
        "last_clicked": last_clicked,
        "top_referrers": [
            {"referrer": referrer, "count": count} for referrer, count in top_referrers
        ],
    }
