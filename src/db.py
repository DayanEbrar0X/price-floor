import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# sqlite by default so the thing runs anywhere without a server,
# set DATABASE_URL to point at postgres when we deploy the collector
DB_URL = os.environ.get("DATABASE_URL", "sqlite:///pricefloor.db")

engine = create_engine(DB_URL)
Session = sessionmaker(bind=engine)
