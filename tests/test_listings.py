"""
Test suite for listing endpoints
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.models.listing import Listing, PropertyType, ListingStatus

# SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_listings.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

# Mock auth token
MOCK_TOKEN = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1NTBlODQwMC1lMjliLTQxZDQtYTcxNi00NDY2NTU0NDAwMDAiLCJlbWFpbCI6ImxhbmRsb3JkQGV4YW1wbGUuY29tIiwicm9sZSI6ImxhbmRsb3JkIiwia3ljX3N0YXR1cyI6InZlcmlmaWVkIn0.test"


class TestListingCreation:
    """Test listing creation endpoint"""
    
    def setup_method(self):
        """Clear database before each test"""
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
    
    def test_create_listing_success(self):
        """Test successful listing creation"""
        response = client.post(
            "/api/v1/listings",
            headers={"Authorization": MOCK_TOKEN},
            json={
                "title": "3-Bedroom Apartment in Gwarinpa",
                "description": "Modern apartment with pool and gym",
                "price": 3500000,
                "currency": "NGN",
                "price_per_unit": "year",
                "property_type": "apartment",
                "bedrooms": 3,
                "bathrooms": 2,
                "area": 250,
                "location": {
                    "address": "123 Gwarinpa Street",
                    "city": "Abuja",
                    "state": "FCT",
                    "latitude": 9.0765,
                    "longitude": 7.3986,
                    "neighborhood": "Gwarinpa"
                },
                "amenities": ["gym", "pool", "security"]
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "listing_id" in data
        assert data["status"] == "pending_review"
    
    def test_create_listing_no_kyc(self):
        """Test listing creation without KYC verification"""
        # Token with kyc_status: pending
        unverified_token = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1NTBlODQwMC1lMjliLTQxZDQtYTcxNi00NDY2NTU0NDAwMDAxIiwicm9sZSI6ImxhbmRsb3JkIiwia3ljX3N0YXR1cyI6InBlbmRpbmcifQ.test"
        
        response = client.post(
            "/api/v1/listings",
            headers={"Authorization": unverified_token},
            json={
                "title": "Test Property",
                "price": 1000000,
                "property_type": "apartment",
                "location": {
                    "address": "Test Address",
                    "city": "Abuja"
                }
            }
        )
        
        assert response.status_code == 403
        assert "KYC" in response.json()["detail"]
    
    def test_create_listing_missing_required_fields(self):
        """Test listing creation with missing required fields"""
        response = client.post(
            "/api/v1/listings",
            headers={"Authorization": MOCK_TOKEN},
            json={
                "title": "Test",  # Too short
                "price": 1000000,
                "property_type": "apartment",
            }
        )
        
        assert response.status_code == 422  # Validation error


class TestListingRetrieval:
    """Test listing retrieval endpoints"""
    
    def setup_method(self):
        """Create test listing before each test"""
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        
        db = TestingSessionLocal()
        listing = Listing(
            owner_id="test-owner",
            owner_name="Test Landlord",
            title="Test Listing",
            price=2000000,
            currency="NGN",
            price_per_unit="year",
            property_type=PropertyType.APARTMENT,
            bedrooms=2,
            bathrooms=1,
            address="Test Address",
            city="Abuja",
            neighborhood="Gwarinpa",
            status=ListingStatus.APPROVED,
            is_active=True,
        )
        db.add(listing)
        db.commit()
        self.listing_id = listing.id
        db.close()
    
    def test_get_listing_success(self):
        """Test getting listing details"""
        response = client.get(f"/api/v1/listings/{self.listing_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Listing"
        assert data["price"] == 2000000
    
    def test_get_listing_not_found(self):
        """Test getting non-existent listing"""
        response = client.get("/api/v1/listings/non-existent-id")
        
        assert response.status_code == 404
    
    def test_get_listing_increments_views(self):
        """Test that getting listing increments view count"""
        # Get listing first time
        response1 = client.get(f"/api/v1/listings/{self.listing_id}")
        assert response1.json()["views"] == 1
        
        # Get listing second time
        response2 = client.get(f"/api/v1/listings/{self.listing_id}")
        assert response2.json()["views"] == 2


class TestListingUpdate:
    """Test listing update endpoint"""
    
    def setup_method(self):
        """Create test listing and authenticate"""
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        
        db = TestingSessionLocal()
        listing = Listing(
            id="test-listing-123",
            owner_id="550e8400-e29b-41d4-a716-446655440000",
            owner_name="Test Landlord",
            title="Test Listing",
            price=2000000,
            currency="NGN",
            price_per_unit="year",
            property_type=PropertyType.APARTMENT,
            bedrooms=2,
            bathrooms=1,
            address="Test Address",
            city="Abuja",
            status=ListingStatus.APPROVED,
            is_active=True,
        )
        db.add(listing)
        db.commit()
        db.close()
    
    def test_update_listing_success(self):
        """Test successful listing update"""
        response = client.patch(
            "/api/v1/listings/test-listing-123",
            headers={"Authorization": MOCK_TOKEN},
            json={
                "price": 2500000,
                "bedrooms": 3,
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["price"] == 2500000
        assert data["bedrooms"] == 3
    
    def test_update_listing_not_owner(self):
        """Test update by non-owner"""
        other_token = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkaWZmZXJlbnQtdXNlciIsInJvbGUiOiJsYW5kbG9yZCIsImt5Y19zdGF0dXMiOiJ2ZXJpZmllZCJ9.test"
        
        response = client.patch(
            "/api/v1/listings/test-listing-123",
            headers={"Authorization": other_token},
            json={"price": 3000000}
        )
        
        assert response.status_code == 403


class TestListingSearch:
    """Test listing search and filter"""
    
    def setup_method(self):
        """Create test listings"""
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        
        db = TestingSessionLocal()
        
        listings = [
            Listing(
                owner_id="owner1",
                title="Apartment 1",
                price=2000000,
                currency="NGN",
                price_per_unit="year",
                property_type=PropertyType.APARTMENT,
                bedrooms=2,
                address="Address 1",
                city="Abuja",
                status=ListingStatus.APPROVED,
                is_active=True,
            ),
            Listing(
                owner_id="owner2",
                title="House 1",
                price=5000000,
                currency="NGN",
                price_per_unit="year",
                property_type=PropertyType.RESIDENTIAL,
                bedrooms=4,
                address="Address 2",
                city="Abuja",
                status=ListingStatus.APPROVED,
                is_active=True,
            ),
            Listing(
                owner_id="owner3",
                title="Land 1",
                price=1000000,
                currency="NGN",
                price_per_unit="year",
                property_type=PropertyType.LAND,
                address="Address 3",
                city="Lagos",
                status=ListingStatus.APPROVED,
                is_active=True,
            ),
        ]
        
        db.add_all(listings)
        db.commit()
        db.close()
    
    def test_search_all_listings(self):
        """Test searching all approved listings"""
        response = client.post(
            "/api/v1/listings/search",
            json={}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["listings"]) == 3
    
    def test_search_by_property_type(self):
        """Test filtering by property type"""
        response = client.post(
            "/api/v1/listings/search",
            json={
                "property_type": ["apartment"]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["listings"][0]["property_type"] == "apartment"
    
    def test_search_by_price_range(self):
        """Test filtering by price range"""
        response = client.post(
            "/api/v1/listings/search",
            json={
                "price_min": 2000000,
                "price_max": 4000000
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["listings"][0]["price"] == 2000000
    
    def test_search_by_city(self):
        """Test filtering by city"""
        response = client.post(
            "/api/v1/listings/search",
            json={
                "city": "Lagos"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["listings"][0]["city"] == "Lagos"


class TestListingEngagement:
    """Test favorite/engagement features"""
    
    def setup_method(self):
        """Create test listing"""
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        
        db = TestingSessionLocal()
        listing = Listing(
            id="test-listing-123",
            owner_id="owner1",
            title="Test Listing",
            price=2000000,
            currency="NGN",
            price_per_unit="year",
            property_type=PropertyType.APARTMENT,
            address="Test Address",
            city="Abuja",
            status=ListingStatus.APPROVED,
            is_active=True,
            favorites=0,
        )
        db.add(listing)
        db.commit()
        db.close()
    
    def test_add_favorite(self):
        """Test adding listing to favorites"""
        response = client.post(
            "/api/v1/listings/test-listing-123/favorite",
            headers={"Authorization": MOCK_TOKEN}
        )
        
        assert response.status_code == 201
        
        # Verify favorite count increased
        listing_response = client.get("/api/v1/listings/test-listing-123")
        assert listing_response.json()["favorites"] == 1
    
    def test_remove_favorite(self):
        """Test removing listing from favorites"""
        # Add favorite first
        client.post(
            "/api/v1/listings/test-listing-123/favorite",
            headers={"Authorization": MOCK_TOKEN}
        )
        
        # Remove favorite
        response = client.delete(
            "/api/v1/listings/test-listing-123/favorite",
            headers={"Authorization": MOCK_TOKEN}
        )
        
        assert response.status_code == 204


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
