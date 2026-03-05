"""
Listing management API endpoints
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    get_current_user,
    get_current_user_id,
    verify_kyc_status,
    require_role,
)
from app.schemas.listing import (
    ListingCreateRequest,
    ListingCreateResponse,
    ListingResponse,
    ListingListResponse,
    ListingUpdateRequest,
    ListingFilterRequest,
    ErrorResponse,
)
from app.services.listing_service import ListingService
from app.models.listing import ListingStatus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/listings", tags=["Listings"])


# ============ CREATE LISTING ============

@router.post(
    "",
    response_model=ListingCreateResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "KYC not verified"},
    }
)
async def create_listing(
    listing_data: ListingCreateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Create a new property listing
    
    Requirements:
    - User must be authenticated
    - User must be landlord or agent
    - User must have verified KYC
    """
    try:
        user_id = current_user.get("sub")
        user_role = current_user.get("role")
        kyc_status = current_user.get("kyc_status")
        user_name = current_user.get("email", "")
        
        # Check role
        if user_role not in ["landlord", "agent"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only landlords and agents can create listings"
            )
        
        # Check KYC
        if kyc_status != "verified":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="KYC verification required. Please complete your verification first."
            )
        
        # Create listing
        listing = ListingService.create_listing(
            db=db,
            owner_id=user_id,
            owner_name=user_name,
            listing_data=listing_data
        )
        
        return ListingCreateResponse(
            message="Listing created successfully. Pending admin review.",
            listing_id=listing.id,
            status=listing.status
        )
    
    except ValueError as e:
        logger.error(f"Listing creation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating listing: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create listing"
        )


# ============ GET LISTING ============

@router.get(
    "/{listing_id}",
    response_model=ListingResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Listing not found"},
    }
)
async def get_listing(
    listing_id: str,
    db: Session = Depends(get_db),
):
    """
    Get listing details
    
    Public endpoint - no authentication required.
    Increments view count when called.
    """
    try:
        listing = ListingService.get_listing_details(db, listing_id)
        
        if not listing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Listing not found"
            )
        
        return ListingResponse.from_orm(listing)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching listing: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch listing"
        )


# ============ UPDATE LISTING ============

@router.patch(
    "/{listing_id}",
    response_model=ListingResponse,
    responses={
        403: {"model": ErrorResponse, "description": "Forbidden - not owner"},
        404: {"model": ErrorResponse, "description": "Listing not found"},
    }
)
async def update_listing(
    listing_id: str,
    update_data: ListingUpdateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Update listing
    
    Only the listing owner can update it.
    """
    try:
        user_id = current_user.get("sub")
        
        listing = ListingService.update_listing(
            db=db,
            listing_id=listing_id,
            owner_id=user_id,
            update_data=update_data
        )
        
        return ListingResponse.from_orm(listing)
    
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        elif "not owner" in str(e):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating listing: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update listing"
        )


# ============ DELETE LISTING ============

@router.delete(
    "/{listing_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        403: {"model": ErrorResponse, "description": "Forbidden - not owner"},
        404: {"model": ErrorResponse, "description": "Listing not found"},
    }
)
async def delete_listing(
    listing_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Delete (archive) listing
    
    Only the listing owner can delete it.
    Soft delete - marks as archived.
    """
    try:
        user_id = current_user.get("sub")
        
        ListingService.delete_listing(
            db=db,
            listing_id=listing_id,
            owner_id=user_id
        )
    
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        elif "not owner" in str(e):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error deleting listing: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete listing"
        )


# ============ SEARCH & FILTER ============

@router.post(
    "/search",
    response_model=ListingListResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid filters"},
    }
)
async def search_listings(
    filters: ListingFilterRequest,
    db: Session = Depends(get_db),
):
    """
    Search and filter listings
    
    Public endpoint - no authentication required.
    Filters approved and active listings only.
    """
    try:
        listings, total = ListingService.filter_listings(db, filters)
        
        return ListingListResponse(
            listings=[ListingResponse.from_orm(listing) for listing in listings],
            total=total,
            limit=filters.limit,
            offset=filters.offset
        )
    
    except Exception as e:
        logger.error(f"Error searching listings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search listings"
        )


# ============ USER'S LISTINGS ============

@router.get(
    "/user/my-listings",
    response_model=ListingListResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
    }
)
async def get_my_listings(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Get current user's listings
    
    Requires authentication.
    Shows all listings regardless of status.
    """
    try:
        user_id = current_user.get("sub")
        
        listings, total = ListingService.get_user_listings(
            db=db,
            owner_id=user_id,
            limit=limit,
            offset=offset
        )
        
        return ListingListResponse(
            listings=[ListingResponse.from_orm(listing) for listing in listings],
            total=total,
            limit=limit,
            offset=offset
        )
    
    except Exception as e:
        logger.error(f"Error fetching user listings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch listings"
        )


# ============ ENGAGEMENT ============

@router.post(
    "/{listing_id}/favorite",
    status_code=status.HTTP_201_CREATED,
)
async def add_favorite(
    listing_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Add listing to favorites
    
    Increments favorite count.
    """
    try:
        listing = ListingService.add_favorite(db, listing_id)
        
        if not listing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Listing not found"
            )
        
        return {"message": "Added to favorites"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding favorite: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add to favorites"
        )


@router.delete(
    "/{listing_id}/favorite",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_favorite(
    listing_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Remove listing from favorites
    
    Decrements favorite count.
    """
    try:
        listing = ListingService.remove_favorite(db, listing_id)
        
        if not listing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Listing not found"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing favorite: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove from favorites"
        )
