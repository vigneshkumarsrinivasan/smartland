"""
SQLAlchemy models. Phase 1 populates all tables with seed data.
Deferred (Phase 5+): User, Watchlist, Report, Alert, ModelWeight
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class City(Base):
    __tablename__ = "cities"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    state = Column(String, nullable=False)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    areas = relationship("Area", back_populates="city")


class Area(Base):
    __tablename__ = "areas"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    city_id = Column(Integer, ForeignKey("cities.id"), nullable=False)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    current_price_sqft = Column(Float, nullable=False)
    land_type = Column(String, default="Residential")

    city = relationship("City", back_populates="areas")
    price_history = relationship("AreaPriceHistory", back_populates="area", order_by="AreaPriceHistory.date")
    infrastructure_projects = relationship("InfrastructureProject", back_populates="area")
    growth_signals = relationship("GrowthSignal", back_populates="area")
    risk_signals = relationship("RiskSignal", back_populates="area")
    predictions = relationship("Prediction", back_populates="area")


class AreaPriceHistory(Base):
    __tablename__ = "area_price_history"
    id = Column(Integer, primary_key=True, index=True)
    area_id = Column(Integer, ForeignKey("areas.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    price_sqft = Column(Float, nullable=False)
    area = relationship("Area", back_populates="price_history")


class InfrastructureProject(Base):
    __tablename__ = "infrastructure_projects"
    id = Column(Integer, primary_key=True, index=True)
    area_id = Column(Integer, ForeignKey("areas.id"), nullable=False)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)       # Metro, Highway, IT Park, Airport, etc.
    status = Column(String, nullable=False)     # Announced, Under Construction, Completed
    target_year = Column(Integer)
    impact_score = Column(Float)               # 0-10 estimated impact on area
    area = relationship("Area", back_populates="infrastructure_projects")


class GrowthSignal(Base):
    __tablename__ = "growth_signals"
    id = Column(Integer, primary_key=True, index=True)
    area_id = Column(Integer, ForeignKey("areas.id"), nullable=False)
    infrastructure_score = Column(Float)
    job_growth_score = Column(Float)
    population_growth_score = Column(Float)
    commercial_activity_score = Column(Float)
    transaction_velocity_score = Column(Float)
    land_scarcity_score = Column(Float)
    government_spending_score = Column(Float)
    area = relationship("Area", back_populates="growth_signals")


class RiskSignal(Base):
    __tablename__ = "risk_signals"
    id = Column(Integer, primary_key=True, index=True)
    area_id = Column(Integer, ForeignKey("areas.id"), nullable=False)
    flood_risk = Column(Float)
    water_risk = Column(Float)
    legal_risk = Column(Float)
    overvaluation_risk = Column(Float)
    pollution_risk = Column(Float)
    crime_risk = Column(Float)
    delay_risk = Column(Float)
    area = relationship("Area", back_populates="risk_signals")


class Prediction(Base):
    __tablename__ = "predictions"
    id = Column(Integer, primary_key=True, index=True)
    area_id = Column(Integer, ForeignKey("areas.id"), nullable=False)
    growth_score = Column(Float, nullable=False)     # 0-100
    risk_score = Column(Float, nullable=False)       # 0-100
    confidence_score = Column(Float, nullable=False) # 0-100
    recommendation = Column(String, nullable=False)  # Strong Buy / Buy / Hold / Avoid / Sell
    generated_at = Column(DateTime, default=datetime.utcnow)
    area = relationship("Area", back_populates="predictions")


class DataSource(Base):
    __tablename__ = "data_sources"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)   # Infrastructure, Economic, Environmental, etc.
    description = Column(Text)
    status = Column(String, default="active")   # active, degraded, offline
    last_updated = Column(DateTime, default=datetime.utcnow)
    coverage = Column(String)                   # e.g. "Bangalore, Hyderabad"
