"""
Tests for the Mergington High School Activities API
"""
import pytest
from fastapi.testclient import TestClient
from src.app import app


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirect(self, client):
        """Test that root redirects to /static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert "/static/index.html" in response.headers["location"]


class TestActivitiesEndpoint:
    """Tests for the /activities endpoint"""
    
    def test_get_activities(self, client):
        """Test fetching all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        
        # Check that we have activities
        assert isinstance(data, dict)
        assert len(data) > 0
        
        # Check structure of an activity
        assert "Chess Club" in data
        chess_club = data["Chess Club"]
        assert "description" in chess_club
        assert "schedule" in chess_club
        assert "max_participants" in chess_club
        assert "participants" in chess_club
        assert isinstance(chess_club["participants"], list)
    
    def test_get_activities_has_all_required_fields(self, client):
        """Test that all activities have required fields"""
        response = client.get("/activities")
        data = response.json()
        
        required_fields = {"description", "schedule", "max_participants", "participants"}
        for activity_name, activity_details in data.items():
            assert required_fields.issubset(activity_details.keys()), \
                f"Activity {activity_name} missing required fields"


class TestSignupEndpoint:
    """Tests for the signup endpoint"""
    
    def test_signup_valid(self, client):
        """Test signing up a new student for an activity"""
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "newstudent@mergington.edu"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
        assert "Chess Club" in data["message"]
        
        # Verify the student was actually added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "newstudent@mergington.edu" in activities_data["Chess Club"]["participants"]
    
    def test_signup_duplicate_student(self, client):
        """Test signing up a student who is already registered"""
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "michael@mergington.edu"}
        )
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"]
    
    def test_signup_nonexistent_activity(self, client):
        """Test signing up for a non-existent activity"""
        response = client.post(
            "/activities/Nonexistent Activity/signup",
            params={"email": "newstudent@mergington.edu"}
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]
    
    def test_signup_activity_full(self, client):
        """Test signing up when activity is at max capacity"""
        # Get activities to check current state
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        
        # Find an activity we can fill up
        activity_name = "Math Olympiad"  # max 10 participants
        activity = activities_data[activity_name]
        current_participants = len(activity["participants"])
        remaining_spots = activity["max_participants"] - current_participants
        
        # Fill up the activity if not full
        if remaining_spots > 0:
            for i in range(remaining_spots):
                client.post(
                    f"/activities/{activity_name}/signup",
                    params={"email": f"student{i}@mergington.edu"}
                )
        
        # Try to sign up one more student (should fail if full)
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": "overfull@mergington.edu"}
        )
        assert response.status_code == 400
        data = response.json()
        assert "no spots left" in data["detail"]


class TestUnregisterEndpoint:
    """Tests for the unregister endpoint"""
    
    def test_unregister_valid(self, client):
        """Test unregistering a student from an activity"""
        response = client.post(
            "/activities/Chess Club/unregister",
            params={"email": "michael@mergington.edu"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "michael@mergington.edu" in data["message"]
        assert "Chess Club" in data["message"]
        
        # Verify the student was actually removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "michael@mergington.edu" not in activities_data["Chess Club"]["participants"]
    
    def test_unregister_not_registered(self, client):
        """Test unregistering a student who is not registered"""
        response = client.post(
            "/activities/Chess Club/unregister",
            params={"email": "notregistered@mergington.edu"}
        )
        assert response.status_code == 400
        data = response.json()
        assert "not registered" in data["detail"]
    
    def test_unregister_nonexistent_activity(self, client):
        """Test unregistering from a non-existent activity"""
        response = client.post(
            "/activities/Nonexistent Activity/unregister",
            params={"email": "michael@mergington.edu"}
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]
    
    def test_unregister_then_signup_again(self, client):
        """Test that a student can sign up again after unregistering"""
        email = "michael@mergington.edu"
        activity = "Chess Club"
        
        # Unregister
        response = client.post(
            f"/activities/{activity}/unregister",
            params={"email": email}
        )
        assert response.status_code == 200
        
        # Verify removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data[activity]["participants"]
        
        # Sign up again
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response.status_code == 200
        
        # Verify re-registered
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data[activity]["participants"]


class TestActivityDetails:
    """Tests for activity details and participants"""
    
    def test_participants_count(self, client):
        """Test that participant counts are accurate"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity in data.items():
            participants = activity["participants"]
            max_participants = activity["max_participants"]
            
            # Participants should not exceed max
            assert len(participants) <= max_participants, \
                f"{activity_name} has more participants than allowed"
    
    def test_activity_schedule_exists(self, client):
        """Test that all activities have schedule information"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity in data.items():
            assert activity["schedule"], f"{activity_name} has no schedule"
            assert isinstance(activity["schedule"], str)
            assert len(activity["schedule"]) > 0
    
    def test_activity_description_exists(self, client):
        """Test that all activities have descriptions"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity in data.items():
            assert activity["description"], f"{activity_name} has no description"
            assert isinstance(activity["description"], str)
            assert len(activity["description"]) > 0
