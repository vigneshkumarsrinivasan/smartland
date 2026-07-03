"""
SQLAlchemy models. Phase 1 populates all tables with seed data.
Phase B adds: Plan, User, Subscription, UsageLog
"""
import uuid
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
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
    data_source = Column(String, nullable=True) # e.g. "NHAI", "BMRCL"
    source_url = Column(String, nullable=True)  # traceable source URL
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
    last_run_at = Column(DateTime, nullable=True)  # when the pipeline ingester last ran
    freshness_hours = Column(Integer, default=24)  # how often this source should be refreshed


# ── Phase B: Billing ──────────────────────────────────────────────────────────

class Plan(Base):
    __tablename__ = "plans"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)               # "Free", "Pro", "Enterprise"
    slug = Column(String, unique=True, nullable=False)  # "free", "pro", "enterprise"
    razorpay_plan_id = Column(String, nullable=True)    # set after creating plan in Razorpay
    price_inr = Column(Integer, nullable=False)         # monthly price in INR (0 for Free)
    billing_cycle = Column(String, default="monthly")
    max_reports_per_month = Column(Integer, nullable=True)  # null = unlimited
    features_json = Column(Text, nullable=True)             # JSON list of feature strings
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    subscriptions = relationship("Subscription", back_populates="plan")


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=True)
    auth_token = Column(String, unique=True, nullable=True, index=True)  # UUID bearer token
    razorpay_customer_id = Column(String, nullable=True)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    plan = relationship("Plan")
    subscriptions = relationship("Subscription", back_populates="user")
    usage_logs = relationship("UsageLog", back_populates="user")

    @staticmethod
    def generate_token() -> str:
        return str(uuid.uuid4())


class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    razorpay_subscription_id = Column(String, nullable=True)
    # Razorpay statuses: created, authenticated, active, paused, cancelled, completed, expired
    status = Column(String, default="created")
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="subscriptions")
    plan = relationship("Plan", back_populates="subscriptions")


class UsageLog(Base):
    __tablename__ = "usage_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    # event_type: "area_report", "compare", "export", "api_call"
    event_type = Column(String, nullable=False)
    resource_id = Column(Integer, nullable=True)   # e.g. area_id
    metadata_json = Column(Text, nullable=True)    # extra JSON data
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="usage_logs")


# ── Phase E: API Keys ─────────────────────────────────────────────────────────

class ApiKey(Base):
    __tablename__ = "api_keys"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)              # human label, e.g. "Production app"
    key_hash = Column(String, unique=True, nullable=False)  # SHA-256 of the raw key
    key_prefix = Column(String, nullable=False)        # first 12 chars for display
    scopes = Column(String, default="read")            # "read" | "read,write"
    requests_per_minute = Column(Integer, default=60)  # enforced by slowapi per key
    last_used_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=True)       # null = never expires
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User")


# ── Phase D: Alerts ───────────────────────────────────────────────────────────

class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    area_id = Column(Integer, ForeignKey("areas.id"), nullable=False)
    # alert_type: "price_movement", "score_change", "weekly_digest"
    alert_type = Column(String, nullable=False, default="price_movement")
    # channel: "email", "whatsapp", "both"
    channel = Column(String, nullable=False, default="email")
    # threshold: % change that triggers the alert (e.g. 5.0 = 5%)
    threshold = Column(Float, nullable=True, default=5.0)
    phone = Column(String, nullable=True)          # WhatsApp number (E.164 format)
    is_active = Column(Boolean, default=True)
    last_triggered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User")
    area = relationship("Area")
