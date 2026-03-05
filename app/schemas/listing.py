"""
Pydantic schemas for listing endpoints
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class PropertyType(str, Enum):
    """Property type enumeration"""
    RESIDENTIAL = "residential"
    APARTMENT = "apartment"
    COMMERCIAL = "commercial"
    LAND = "land"
    OFFICE = "office"
    WAREHOUSE = "warehouse"


class ListingStatus(str, Enum):
    """Listing status enumeration"""
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class PriceUnit(str, Enum):
    """Price per unit enumeration"""
    YEAR = "year"
    MONTH = "month"
    DAY = "day"


# ============ REQUEST SCHEMAS ============

class LocationInput(BaseModel):
    """Location information for listing"""
    address: str = Field(..., min_length=5, max_length=255)
    city: str = Field(..., min_length=2, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    neighborhood: Optional[str] = Field(None, max_length=100)


class ListingCreateRequest(BaseModel):
    """Create listing request schema"""
    title: str = Field(..., min_length=10, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    price: float = Field(..., gt=0)
    currency: str = Field(default="NGN", max_length=3)
    price_per_unit: PriceUnit = Field(default=PriceUnit.YEAR)
    property_type: PropertyType
    bedrooms: Optional[int] = Field(None, ge=0)
    bathrooms: Optional[int] = Field(None, ge=0)
    area: Optional[float] = Field(None, gt=0, description="Area in square meters")
    location: LocationInput
    amenities: Optional[List[str]] = Field(default=[], max_length=20)


class ListingUpdateRequest(BaseModel):
    """Update listing request schema"""
    title: Optional[str] = Field(None, min_length=10, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    price: Optional[float] = Field(None, gt=0)
    price_per_unit: Optional[PriceUnit] = None
    property_type: Optional[PropertyType] = None
    bedrooms: Optional[int] = Field(None, ge=0)
    bathrooms: Optional[int] = Field(None, ge=0)
    area: Optional[float] = Field(None, gt=0)
    location: Optional[LocationInput] = None
    amenities: Optional[List[str]] = None
    is_active: Optional[bool] = None


class ListingFilterRequest(BaseModel):
    """Listing filter request schema"""
    property_type: Optional[List[PropertyType]] = None
    price_min: Optional[float] = Field(None, ge=0)
    price_max: Optional[float] = Field(None, ge=0)
    bedrooms: Optional[List[int]] = None
    city: Optional[str] = None
    neighborhood: Optional[str] = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    sort_by: str = Field(default="newest", description="newest, price_asc, price_desc, most_viewed")
    
    @validator('price_max')
    def validate_price_range(cls, v, values):
        if v and 'price_min' in values and values['price_min']:
            if v < values['price_min']:
                raise ValueError('price_max must be greater than price_min')
        return v


# ============ RESPONSE SCHEMAS ============

class LocationResponse(BaseModel):
    """Location information in response"""
    address: str
    city: str
    state: Optional[str] = None
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    neighborhood: Optional[str] = None
    
    class Config:
        from_attributes = True


class ImageInfo(BaseModel):
    """Image information"""
    url: str
    caption: Optional[str] = None
    is_main: bool = False


class DocumentInfo(BaseModel):
    """Document information"""
    type: str  # title_deed, survey_plan, etc.
    url: str
    uploaded_at: datetime


class ListingResponse(BaseModel):
    """Complete listing response"""
    id: str
    title: str
    description: Optional[str] = None
    price: float
    currency: str
    price_per_unit: PriceUnit
    property_type: PropertyType
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    area: Optional[float] = None
    location: LocationResponse
    amenities: Optional[List[str]] = None
    images: Optional[List[ImageInfo]] = None
    documents: Optional[List[DocumentInfo]] = None
    owner_id: str
    owner_name: Optional[str] = None
    status: ListingStatus
    is_active: bool
    views: int
    favorites: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ListingListResponse(BaseModel):
    """Multiple listings response"""
    listings: List[ListingResponse]
    total: int
    limit: int
    offset: int


class ListingCreateResponse(BaseModel):
    """Listing creation response"""
    message: str
    listing_id: str
    status: ListingStatus


# ============ ERROR SCHEMAS ============

class ErrorResponse(BaseModel):
    """Standard error response"""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
