"""
Basic API endpoint tests
"""
import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Test health check endpoints"""
    
    def test_health_check(self, client: TestClient):
        """Test basic health check endpoint"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "app_name" in data
    
    def test_root_endpoint(self, client: TestClient):
        """Test root endpoint"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data


class TestAuthEndpoints:
    """Test authentication endpoints"""
    
    def test_signup_and_me_flow(self, client: TestClient, sample_user_data):
        """Test per-user signup then fetch current user"""
        # Signup
        resp = client.post("/api/v1/auth/signup", json={
            "email": sample_user_data["email"],
            "username": sample_user_data["username"],
            "password": sample_user_data["password"]
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        token = data["access_token"]

        # Get current user
        me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        me_data = me.json()
        assert me_data["email"] == sample_user_data["email"]
    
    def test_login_with_invalid_credentials(self, client: TestClient):
        """Test login with invalid credentials"""
        response = client.post("/api/v1/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401
    
    def test_access_protected_endpoint_without_auth(self, client: TestClient):
        """Test accessing protected endpoint without authentication"""
        response = client.get("/api/v1/auth/me")
        
        assert response.status_code == 401


class TestDocumentEndpoints:
    """Test document management endpoints"""
    
    def test_list_documents_without_auth(self, client: TestClient):
        """Test listing documents without authentication"""
        response = client.get("/api/v1/documents/")
        
        assert response.status_code == 401
    
    def test_upload_document_without_auth(self, client: TestClient):
        """Test uploading document without authentication"""
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.txt", "test content", "text/plain")}
        )
        
        assert response.status_code == 401


class TestQueryEndpoints:
    """Test RAG query endpoints"""
    
    def test_rag_query_without_auth(self, client: TestClient):
        """Test RAG query without authentication"""
        response = client.post("/api/v1/queries/rag", json={
            "query": "What is the meaning of life?",
            "max_chunks": 5
        })
        
        assert response.status_code == 401
    
    def test_query_history_without_auth(self, client: TestClient):
        """Test query history without authentication"""
        response = client.get("/api/v1/queries/history")
        
        assert response.status_code == 401