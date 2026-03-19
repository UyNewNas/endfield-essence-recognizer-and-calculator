import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException

from endfield_essence_recognizer.server import app
from endfield_essence_recognizer.api.routes.user_profile import router, profile_manager
from endfield_essence_recognizer.schemas.user_profile import UserProfile, WeaponEssenceMatch
from datetime import datetime


@pytest.fixture
def client():
    """Fixture for a FastAPI TestClient."""
    from fastapi import FastAPI
    test_app = FastAPI()
    test_app.include_router(router)
    with TestClient(test_app) as client:
        yield client


@pytest.fixture
def mock_profile_manager():
    """Fixture for a mocked UserProfileManager."""
    with patch('endfield_essence_recognizer.api.routes.user_profile.profile_manager') as mock:
        yield mock


class TestCreateProfile:
    def test_create_profile_success(self, client, mock_profile_manager):
        mock_profile = UserProfile(
            id="test-id-123",
            name="测试用户",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            updated_at=datetime(2024, 1, 1, 12, 0, 0),
            acquired_weapons=[],
        )
        mock_profile_manager.create_profile.return_value = mock_profile
        
        response = client.post("/user-profile/create", json={"name": "测试用户"})
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-id-123"
        assert data["name"] == "测试用户"
        assert data["weapon_count"] == 0
        mock_profile_manager.create_profile.assert_called_once_with("测试用户")
    
    def test_create_profile_empty_name(self, client, mock_profile_manager):
        mock_profile = UserProfile(name="")
        mock_profile_manager.create_profile.return_value = mock_profile
        
        response = client.post("/user-profile/create", json={"name": ""})
        
        assert response.status_code == 200
        assert response.json()["name"] == ""


class TestListProfiles:
    def test_list_profiles_empty(self, client, mock_profile_manager):
        mock_profile_manager.list_profiles.return_value = []
        
        response = client.get("/user-profile/list")
        
        assert response.status_code == 200
        assert response.json() == []
    
    def test_list_profiles_multiple(self, client, mock_profile_manager):
        mock_profile_manager.list_profiles.return_value = [
            {
                "id": "id-1",
                "name": "用户1",
                "weapon_count": 3,
                "updated_at": "2024-01-01T12:00:00",
            },
            {
                "id": "id-2",
                "name": "用户2",
                "weapon_count": 5,
                "updated_at": "2024-01-02T12:00:00",
            },
        ]
        
        response = client.get("/user-profile/list")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "用户1"
        assert data[1]["weapon_count"] == 5


class TestSelectProfile:
    def test_select_profile_success(self, client, mock_profile_manager):
        mock_profile_manager.select_profile.return_value = True
        
        response = client.post("/user-profile/select/test-id-123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Profile selected"
        assert data["profile_id"] == "test-id-123"
        mock_profile_manager.select_profile.assert_called_once_with("test-id-123")
    
    def test_select_profile_not_found(self, client, mock_profile_manager):
        mock_profile_manager.select_profile.return_value = False
        
        response = client.post("/user-profile/select/nonexistent-id")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestGetCurrentProfile:
    def test_get_current_profile_none(self, client, mock_profile_manager):
        mock_profile_manager.current_profile = None
        
        response = client.get("/user-profile/current")
        
        assert response.status_code == 200
        assert response.json() is None
    
    def test_get_current_profile_exists(self, client, mock_profile_manager):
        mock_profile = UserProfile(
            id="current-id",
            name="当前用户",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            updated_at=datetime(2024, 1, 1, 12, 0, 0),
            acquired_weapons=[
                WeaponEssenceMatch(
                    weapon_name="熔铸火焰",
                    essence_requirements=["智识提升", "攻击提升", "夜幕"],
                    matched_at=datetime(2024, 1, 1, 12, 0, 0),
                )
            ],
        )
        mock_profile_manager.current_profile = mock_profile
        mock_profile_manager.get_acquired_weapons.return_value = [
            {
                "weapon_name": "熔铸火焰",
                "essence_requirements": ["智识提升", "攻击提升", "夜幕"],
                "matched_at": "2024-01-01T12:00:00",
            }
        ]
        
        response = client.get("/user-profile/current")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "current-id"
        assert data["name"] == "当前用户"
        assert len(data["acquired_weapons"]) == 1


class TestDeleteProfile:
    def test_delete_profile_success(self, client, mock_profile_manager):
        mock_profile_manager.delete_profile.return_value = True
        
        response = client.delete("/user-profile/test-id-123")
        
        assert response.status_code == 200
        assert response.json()["message"] == "Profile deleted"
        mock_profile_manager.delete_profile.assert_called_once_with("test-id-123")
    
    def test_delete_profile_not_found(self, client, mock_profile_manager):
        mock_profile_manager.delete_profile.return_value = False
        
        response = client.delete("/user-profile/nonexistent-id")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestRegisterWeapon:
    def test_register_weapon_success(self, client, mock_profile_manager):
        mock_profile_manager.current_profile = UserProfile(name="测试")
        mock_profile_manager.register_acquired_weapon.return_value = True
        
        response = client.post(
            "/user-profile/weapons/register",
            json={
                "weapon_name": "熔铸火焰",
                "essence_requirements": ["智识提升", "攻击提升", "夜幕"],
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Weapon registered"
        assert data["weapon_name"] == "熔铸火焰"
    
    def test_register_weapon_no_profile_selected(self, client, mock_profile_manager):
        mock_profile_manager.current_profile = None
        
        response = client.post(
            "/user-profile/weapons/register",
            json={
                "weapon_name": "熔铸火焰",
                "essence_requirements": ["智识提升", "攻击提升", "夜幕"],
            },
        )
        
        assert response.status_code == 400
        assert "no profile selected" in response.json()["detail"].lower()
    
    def test_register_weapon_failed(self, client, mock_profile_manager):
        mock_profile_manager.current_profile = UserProfile(name="测试")
        mock_profile_manager.register_acquired_weapon.return_value = False
        
        response = client.post(
            "/user-profile/weapons/register",
            json={
                "weapon_name": "不存在的武器",
                "essence_requirements": ["错误词条"],
            },
        )
        
        assert response.status_code == 400
        assert "failed to register" in response.json()["detail"].lower()


class TestUnregisterWeapon:
    def test_unregister_weapon_success(self, client, mock_profile_manager):
        mock_profile_manager.current_profile = UserProfile(name="测试")
        mock_profile_manager.unregister_acquired_weapon.return_value = True
        
        response = client.delete("/user-profile/weapons/熔铸火焰")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Weapon unregistered"
        assert data["weapon_name"] == "熔铸火焰"
    
    def test_unregister_weapon_no_profile_selected(self, client, mock_profile_manager):
        mock_profile_manager.current_profile = None
        
        response = client.delete("/user-profile/weapons/熔铸火焰")
        
        assert response.status_code == 400
        assert "no profile selected" in response.json()["detail"].lower()
    
    def test_unregister_weapon_not_found(self, client, mock_profile_manager):
        mock_profile_manager.current_profile = UserProfile(name="测试")
        mock_profile_manager.unregister_acquired_weapon.return_value = False
        
        response = client.delete("/user-profile/weapons/不存在的武器")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestGetAcquiredWeapons:
    def test_get_acquired_weapons_success(self, client, mock_profile_manager):
        mock_profile_manager.current_profile = UserProfile(name="测试")
        mock_profile_manager.get_acquired_weapons.return_value = [
            {
                "weapon_name": "熔铸火焰",
                "essence_requirements": ["智识提升", "攻击提升", "夜幕"],
                "matched_at": "2024-01-01T12:00:00",
            },
            {
                "weapon_name": "黯色火炬",
                "essence_requirements": ["智识提升", "灼热伤害提升", "附术"],
                "matched_at": "2024-01-02T12:00:00",
            },
        ]
        
        response = client.get("/user-profile/weapons/acquired")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["weapon_name"] == "熔铸火焰"
        assert data[1]["weapon_name"] == "黯色火炬"
    
    def test_get_acquired_weapons_no_profile(self, client, mock_profile_manager):
        mock_profile_manager.current_profile = None
        
        response = client.get("/user-profile/weapons/acquired")
        
        assert response.status_code == 400
        assert "no profile selected" in response.json()["detail"].lower()


class TestGetRemainingWeapons:
    def test_get_remaining_weapons_success(self, client, mock_profile_manager):
        mock_profile_manager.current_profile = UserProfile(name="测试")
        mock_profile_manager.get_remaining_weapons.return_value = [
            "扶摇",
            "同类相食",
        ]
        
        response = client.get("/user-profile/weapons/remaining")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert "扶摇" in data
        assert "同类相食" in data
    
    def test_get_remaining_weapons_no_profile(self, client, mock_profile_manager):
        mock_profile_manager.current_profile = None
        
        response = client.get("/user-profile/weapons/remaining")
        
        assert response.status_code == 400
        assert "no profile selected" in response.json()["detail"].lower()


class TestGetFarmingPlans:
    def test_get_farming_plans_success(self, client, mock_profile_manager):
        mock_profile_manager.current_profile = UserProfile(name="测试")
        mock_profile_manager.calculate_farming_plans.return_value = [
            ("枢纽区：", ["敏捷提升", "智识提升", "主能力提升"], "攻击提升", 2, ["熔铸火焰", "扶摇"], 1, ["黯色火炬"]),
            ("源石研究园", ["力量提升", "意志提升", "智识提升"], "附术", 1, ["同类相食"], 1, ["黯色火炬"]),
        ]
        
        response = client.get("/user-profile/farming-plans?top_n=5")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["location"] == "枢纽区："
        assert data[0]["satisfied_count"] == 2
        assert data[0]["matched_count"] == 1
        assert "熔铸火焰" in data[0]["satisfied_weapons"]
    
    def test_get_farming_plans_no_profile(self, client, mock_profile_manager):
        mock_profile_manager.current_profile = None
        
        response = client.get("/user-profile/farming-plans")
        
        assert response.status_code == 400
        assert "no profile selected" in response.json()["detail"].lower()
    
    def test_get_farming_plans_empty(self, client, mock_profile_manager):
        mock_profile_manager.current_profile = UserProfile(name="测试")
        mock_profile_manager.calculate_farming_plans.return_value = []
        
        response = client.get("/user-profile/farming-plans")
        
        assert response.status_code == 200
        assert response.json() == []
    
    def test_get_farming_plans_custom_top_n(self, client, mock_profile_manager):
        mock_profile_manager.current_profile = UserProfile(name="测试")
        mock_profile_manager.calculate_farming_plans.return_value = []
        
        response = client.get("/user-profile/farming-plans?top_n=20")
        
        mock_profile_manager.calculate_farming_plans.assert_called_once_with(top_n=20)


class TestAPIIntegration:
    def test_full_workflow(self, client, mock_profile_manager):
        mock_profile = UserProfile(
            id="workflow-id",
            name="工作流测试用户",
            acquired_weapons=[],
        )
        mock_profile_manager.create_profile.return_value = mock_profile
        mock_profile_manager.select_profile.return_value = True
        mock_profile_manager.current_profile = mock_profile
        mock_profile_manager.register_acquired_weapon.return_value = True
        mock_profile_manager.get_acquired_weapons.return_value = [
            {
                "weapon_name": "熔铸火焰",
                "essence_requirements": ["智识提升", "攻击提升", "夜幕"],
                "matched_at": "2024-01-01T12:00:00",
            }
        ]
        mock_profile_manager.get_remaining_weapons.return_value = ["黯色火炬", "扶摇"]
        mock_profile_manager.calculate_farming_plans.return_value = []
        
        create_response = client.post("/user-profile/create", json={"name": "工作流测试用户"})
        assert create_response.status_code == 200
        
        select_response = client.post("/user-profile/select/workflow-id")
        assert select_response.status_code == 200
        
        register_response = client.post(
            "/user-profile/weapons/register",
            json={
                "weapon_name": "熔铸火焰",
                "essence_requirements": ["智识提升", "攻击提升", "夜幕"],
            },
        )
        assert register_response.status_code == 200
        
        acquired_response = client.get("/user-profile/weapons/acquired")
        assert acquired_response.status_code == 200
        assert len(acquired_response.json()) == 1
        
        remaining_response = client.get("/user-profile/weapons/remaining")
        assert remaining_response.status_code == 200
        assert len(remaining_response.json()) == 2
