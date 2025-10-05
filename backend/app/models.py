from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, Float, String

Base = declarative_base()


class Observation(Base):
    __tablename__ = "observations"

    id = Column(Integer, primary_key=True, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    date = Column(String, index=True, nullable=False)
    ndvi = Column(Float, nullable=True)
    evi = Column(Float, nullable=True)
    t2m = Column(Float, nullable=True)
    rh2m = Column(Float, nullable=True)
    label = Column(String, nullable=True)
