"""
Listing service layer with business logic
"""
import logging
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.listing import Listing, PropertyType, ListingStatus
from app.schemas.listing import (
    ListingCreateRequest,
    ListingUpdateRequest,
    ListingFilterRequest,
)

logger = logging.getLogger(__name__)


class ListingService:
    """Service class for listing management operations"""
    
    @staticmethod
    def create_listing(
        db: Session,
        owner_id: str,
        owner_name: str,
        listing_data: ListingCreateRequest
    ) -> Listing:
        """
        Create a new listing
        
        Args:
            db: Database session
            owner_id: ID of listing owner (landlord)
            owner_name: Name of listing owner
            listing_data: Listing creation data
        
        Returns:
            Created Listing object
        """
        new_listing = Listing(
            owner_id=owner_id,
            owner_name=owner_name,
            title=listing_data.title,
            description=listing_data.description,
            price=listing_data.price,
            currency=listing_data.currency,
            price_per_unit=listing_data.price_per_unit,
            property_type=listing_data.property_type,
            bedrooms=listing_data.bedrooms,
            bathrooms=listing_data.bathrooms,
            area=listing_data.area,
            address=listing_data.location.address,
            city=listing_data.location.city,
            state=listing_data.location.state,
            postal_code=listing_data.location.postal_code,
            latitude=listing_data.location.latitude,
            longitude=listing_data.location.longitude,
            neighborhood=listing_data.location.neighborhood,
            amenities=listing_data.amenities or [],
            status=ListingStatus.PENDING_REVIEW,
            is_active=True,
        )
        
        db.add(new_listing)
        db.commit()
        db.refresh(new_listing)
        
        logger.info(f"Listing created: {new_listing.id} by owner {owner_id}")
        return new_listing
    
    
    @staticmethod
    def get_listing_by_id(db: Session, listing_id: str) -> Optional[Listing]:
        """Get listing by ID"""
        return db.query(Listing).filter(Listing.id == listing_id).first()
    
    
    @staticmethod
    def get_listing_details(db: Session, listing_id: str) -> Optional[Listing]:
        """
        Get listing details and increment view count
        
        Args:
            db: Database session
            listing_id: Listing ID
        
        Returns:
            Listing object with incremented views
        """
        listing = db.query(Listing).filter(Listing.id == listing_id).first()
        if listing:
            listing.views += 1
            db.commit()
            db.refresh(listing)
        return listing
    
    
    @staticmethod
    def update_listing(
        db: Session,
        listing_id: str,
        owner_id: str,
        update_data: ListingUpdateRequest
    ) -> Optional[Listing]:
        """
        Update listing
        
        Args:
            db: Database session
            listing_id: Listing ID
            owner_id: User ID (must match owner)
            update_data: Update data
        
        Returns:
            Updated Listing object
        
        Raises:
            ValueError: If listing not found or user is not owner
        """
        listing = db.query(Listing).filter(Listing.id == listing_id).first()
        
        if not listing:
            raise ValueError("Listing not found")
        
        if listing.owner_id != owner_id:
            raise ValueError("Only owner can update this listing")
        
        # Update fields if provided
        if update_data.title is not None:
            listing.title = update_data.title
        
        if update_data.description is not None:
            listing.description = update_data.description
        
        if update_data.price is not None:
            listing.price = update_data.price
        
        if update_data.price_per_unit is not None:
            listing.price_per_unit = update_data.price_per_unit
        
        if update_data.property_type is not None:
            listing.property_type = update_data.property_type
        
        if update_data.bedrooms is not None:
            listing.bedrooms = update_data.bedrooms
        
        if update_data.bathrooms is not None:
            listing.bathrooms = update_data.bathrooms
        
        if update_data.area is not None:
            listing.area = update_data.area
        
        if update_data.location is not None:
            listing.address = update_data.location.address
            listing.city = update_data.location.city
            listing.state = update_data.location.state
            listing.postal_code = update_data.location.postal_code
            listing.latitude = update_data.location.latitude
            listing.longitude = update_data.location.longitude
            listing.neighborhood = update_data.location.neighborhood
        
        if update_data.amenities is not None:
            listing.amenities = update_data.amenities
        
        if update_data.is_active is not None:
            listing.is_active = update_data.is_active
        
        db.commit()
        db.refresh(listing)
        
        logger.info(f"Listing updated: {listing_id}")
        return listing
    
    
    @staticmethod
    def delete_listing(
        db: Session,
        listing_id: str,
        owner_id: str
    ) -> None:
        """
        Archive a listing (soft delete)
        
        Args:
            db: Database session
            listing_id: Listing ID
            owner_id: User ID (must match owner)
        
        Raises:
            ValueError: If listing not found or user is not owner
        """
        listing = db.query(Listing).filter(Listing.id == listing_id).first()
        
        if not listing:
            raise ValueError("Listing not found")
        
        if listing.owner_id != owner_id:
            raise ValueError("Only owner can delete this listing")
        
        listing.status = ListingStatus.ARCHIVED
        listing.is_active = False
        
        db.commit()
        
        logger.info(f"Listing archived: {listing_id}")
    
    
    @staticmethod
    def filter_listings(
        db: Session,
        filters: ListingFilterRequest
    ) -> Tuple[list, int]:
        """
        Filter listings based on criteria
        
        Args:
            db: Database session
            filters: Filter criteria
        
        Returns:
            Tuple of (listings, total_count)
        """
        query = db.query(Listing).filter(
            Listing.status == ListingStatus.APPROVED,
            Listing.is_active == True
        )
        
        # Property type filter
        if filters.property_type:
            query = query.filter(Listing.property_type.in_(filters.property_type))
        
        # Price range filter
        if filters.price_min is not None:
            query = query.filter(Listing.price >= filters.price_min)
        
        if filters.price_max is not None:
            query = query.filter(Listing.price <= filters.price_max)
        
        # Bedrooms filter
        if filters.bedrooms:
            query = query.filter(Listing.bedrooms.in_(filters.bedrooms))
        
        # City filter
        if filters.city:
            query = query.filter(Listing.city.ilike(f"%{filters.city}%"))
        
        # Neighborhood filter
        if filters.neighborhood:
            query = query.filter(Listing.neighborhood.ilike(f"%{filters.neighborhood}%"))
        
        # Get total before pagination
        total = query.count()
        
        # Sorting
        if filters.sort_by == "price_asc":
            query = query.order_by(Listing.price.asc())
        elif filters.sort_by == "price_desc":
            query = query.order_by(Listing.price.desc())
        elif filters.sort_by == "most_viewed":
            query = query.order_by(Listing.views.desc())
        else:  # newest
            query = query.order_by(Listing.created_at.desc())
        
        # Pagination
        listings = query.offset(filters.offset).limit(filters.limit).all()
        
        return listings, total
    
    
    @staticmethod
    def get_user_listings(
        db: Session,
        owner_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[list, int]:
        """
        Get all listings for a specific user
        
        Args:
            db: Database session
            owner_id: Owner ID
            limit: Number of results
            offset: Offset for pagination
        
        Returns:
            Tuple of (listings, total_count)
        """
        query = db.query(Listing).filter(Listing.owner_id == owner_id)
        total = query.count()
        
        listings = query.order_by(Listing.created_at.desc()).offset(offset).limit(limit).all()
        
        return listings, total
    
    
    @staticmethod
    def add_favorite(db: Session, listing_id: str) -> Optional[Listing]:
        """Increment favorite count"""
        listing = db.query(Listing).filter(Listing.id == listing_id).first()
        if listing:
            listing.favorites += 1
            db.commit()
            db.refresh(listing)
        return listing
    
    
    @staticmethod
    def remove_favorite(db: Session, listing_id: str) -> Optional[Listing]:
        """Decrement favorite count"""
        listing = db.query(Listing).filter(Listing.id == listing_id).first()
        if listing and listing.favorites > 0:
            listing.favorites -= 1
            db.commit()
            db.refresh(listing)
        return listing
