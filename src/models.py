from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def now():
    return datetime.now(timezone.utc)


class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True)
    cheapshark_id = Column(String(32), unique=True, nullable=False)
    title = Column(String(300), nullable=False)
    steam_app_id = Column(String(32))
    thumb = Column(String(500))
    first_seen = Column(DateTime, default=now)

    snapshots = relationship("PriceSnapshot", back_populates="game")

    def __repr__(self):
        return "<Game %s>" % self.title


class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"

    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    store_id = Column(String(8), nullable=False)
    price = Column(Float, nullable=False)
    normal_price = Column(Float, nullable=False)
    collected_at = Column(DateTime, default=now, nullable=False)

    game = relationship("Game", back_populates="snapshots")

    def __repr__(self):
        return "<PriceSnapshot %s %.2f>" % (self.game_id, self.price)


# the analyzer reads history per game+store constantly, without this it table scans
Index("ix_snap_game_store", PriceSnapshot.game_id, PriceSnapshot.store_id)
