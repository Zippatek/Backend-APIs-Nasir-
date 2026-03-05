"""
SQLAlchemy database models for listings
"""
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, JSON, Enum as SQLEnum, Index, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum
import uuid

Base = declarative_base()


class PropertyType(str, enum.Enum):
    """Property type enumeration"""
    RESIDENTIAL = "residential"
    APARTMENT = "apartment"
    COMMERCIAL = "commercial"
    LAND = "land"
    OFFICE = "office"
    WAREHOUSE = "warehouse"


class ListingStatus(str, enum.Enum):
    """Listing status enumeration"""
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class PriceUnit(str, enum.Enum):
    """Price per unit enumeration"""
    YEAR = "year"
    MONTH = "month"
    DAY = "day"


class Listing(Base):
    """Listing model for PostgreSQL"""
    __tablename__ = "listings"
    
    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Ownership & User Reference
    owner_id = Column(String(36), nullable=False, index=True)  # Foreign key to users table
    owner_name = Column(String(200), nullable=True)
    
    # Basic Information
    title = Column(String(255), nullable=False)
    description = Column(String(2000), nullable=True)
    
    # Pricing
    price = Column(Float, nullable=False)
    currency = Column(String(3), default="NGN", nullable=False)
    price_per_unit = Column(SQLEnum(PriceUnit), default=PriceUnit.YEAR, nullable=False)
    
    # Property Details
    property_type = Column(SQLEnum(PropertyType), nullable=False, index=True)
    bedrooms = Column(Integer, nullable=True)
    bathrooms = Column(Integer, nullable=True)
    area = Column(Float, nullable=True)  # in square meters
    
    # Location
    address = Column(String(255), nullable=False)
    city = Column(String(100), nullable=False, index=True)
    state = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    neighborhood = Column(String(100), nullable=True, index=True)
    
    # Amenities (stored as JSON)
    amenities = Column(JSON, nullable=True, default=[])
    
    # Images (stored as JSON array of URLs)
    images = Column(JSON, nullable=True, default=[])
    
    # Documents (stored as JSON)
    documents = Column(JSON, nullable=True, default=[])
    
    # Status & Verification
    status = Column(SQLEnum(ListingStatus), default=ListingStatus.PENDING_REVIEW, nullable=False, index=True)
    is_active = Column(Boolean, default=True, index=True)
    
    # Engagement Metrics
    views = Column(Integer, default=0)
    favorites = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_owner_status', 'owner_id', 'status'),
        Index('idx_city_status', 'city', 'status'),
        Index('idx_property_type_status', 'property_type', 'status'),
        Index('idx_price_range', 'price'),
        Index('idx_location', 'city', 'neighborhood'),
    )
    
    def __repr__(self):
        return f"<Listing {self.title}>"
