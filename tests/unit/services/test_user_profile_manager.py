import json
import pytest
from pathlib import Path
from datetime import datetime

from endfield_essence_recognizer.services.user_profile_manager import UserProfileManager
from endfield_essence_recognizer.schemas.user_profile import UserProfile, WeaponEssenceMatch


@pytest.fixture
def profiles_dir(tmp_path):
    return str(tmp_path / "user_profiles")


@pytest.fixture
def weapon_data_file(tmp_path):
    data = {
        "单手剑": [
            {"name": "熔铸火焰", "essence_requirements": ["智识提升", "攻击提升", "夜幕"]},
            {"name": "黯色火炬", "essence_requirements": ["智识提升", "灼热伤害提升", "附术"]},
            {"name": "扶摇", "essence_requirements": ["主能力提升", "暴击率提升", "夜幕"]},
        ]
    }
    file_path = tmp_path / "weapon_essence_data.json"
    file_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return str(file_path)


@pytest.fixture
def location_data_file(tmp_path):
    data = {
        "枢纽区：": {
            "基础属性": ["敏捷提升", "力量提升", "意志提升", "智识提升", "主能力提升"],
            "附加属性": ["攻击提升", "寒冷伤害提升"],
            "技能属性": ["强攻", "粉碎", "夜幕"],
        }
    }
    file_path = tmp_path / "location_essence_data.json"
    file_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return str(file_path)


@pytest.fixture
def manager(profiles_dir):
    return UserProfileManager(profiles_dir)


class TestUserProfileManager:
    def test_create_profile(self, manager):
        profile = manager.create_profile("Test User")
        
        assert profile.id is not None
        assert profile.name == "Test User"
        assert len(profile.acquired_weapons) == 0
    
    def test_save_and_load_profile(self, manager, profiles_dir):
        profile = manager.create_profile("Test User")
        
        loaded = manager.load_profile(profile.id)
        
        assert loaded is not None
        assert loaded.id == profile.id
        assert loaded.name == profile.name
    
    def test_list_profiles(self, manager):
        manager.create_profile("User 1")
        manager.create_profile("User 2")
        
        profiles = manager.list_profiles()
        
        assert len(profiles) == 2
    
    def test_select_profile(self, manager):
        profile = manager.create_profile("Test User")
        
        result = manager.select_profile(profile.id)
        
        assert result is True
        assert manager.current_profile is not None
        assert manager.current_profile.id == profile.id
    
    def test_select_nonexistent_profile(self, manager):
        result = manager.select_profile("nonexistent-id")
        
        assert result is False
        assert manager.current_profile is None
    
    def test_delete_profile(self, manager):
        profile = manager.create_profile("Test User")
        
        result = manager.delete_profile(profile.id)
        
        assert result is True
        assert manager.load_profile(profile.id) is None
    
    def test_delete_nonexistent_profile(self, manager):
        result = manager.delete_profile("nonexistent-id")
        
        assert result is False


class TestWeaponRegistration:
    def test_register_acquired_weapon(self, manager, weapon_data_file):
        profile = manager.create_profile("Test User")
        manager.select_profile(profile.id)
        
        manager._weapon_data = {
            "熔铸火焰": ["智识提升", "攻击提升", "夜幕"],
            "黯色火炬": ["智识提升", "灼热伤害提升", "附术"],
        }
        
        result = manager.register_acquired_weapon(
            "熔铸火焰",
            ["智识提升", "攻击提升", "夜幕"],
        )
        
        assert result is True
        assert len(manager.current_profile.acquired_weapons) == 1
        assert manager.current_profile.acquired_weapons[0].weapon_name == "熔铸火焰"
    
    def test_register_weapon_wrong_requirements(self, manager):
        profile = manager.create_profile("Test User")
        manager.select_profile(profile.id)
        
        manager._weapon_data = {
            "熔铸火焰": ["智识提升", "攻击提升", "夜幕"],
        }
        
        result = manager.register_acquired_weapon(
            "熔铸火焰",
            ["错误词条1", "错误词条2", "错误词条3"],
        )
        
        assert result is False
        assert len(manager.current_profile.acquired_weapons) == 0
    
    def test_register_nonexistent_weapon(self, manager):
        profile = manager.create_profile("Test User")
        manager.select_profile(profile.id)
        
        manager._weapon_data = {}
        
        result = manager.register_acquired_weapon(
            "不存在的武器",
            ["词条1", "词条2", "词条3"],
        )
        
        assert result is False
    
    def test_unregister_acquired_weapon(self, manager):
        profile = manager.create_profile("Test User")
        manager.select_profile(profile.id)
        
        manager._weapon_data = {
            "熔铸火焰": ["智识提升", "攻击提升", "夜幕"],
        }
        
        manager.register_acquired_weapon(
            "熔铸火焰",
            ["智识提升", "攻击提升", "夜幕"],
        )
        
        result = manager.unregister_acquired_weapon("熔铸火焰")
        
        assert result is True
        assert len(manager.current_profile.acquired_weapons) == 0
    
    def test_unregister_nonexistent_weapon(self, manager):
        profile = manager.create_profile("Test User")
        manager.select_profile(profile.id)
        
        result = manager.unregister_acquired_weapon("不存在的武器")
        
        assert result is False


class TestRemainingWeapons:
    def test_get_remaining_weapons(self, manager):
        profile = manager.create_profile("Test User")
        manager.select_profile(profile.id)
        
        manager._weapon_data = {
            "熔铸火焰": ["智识提升", "攻击提升", "夜幕"],
            "黯色火炬": ["智识提升", "灼热伤害提升", "附术"],
            "扶摇": ["主能力提升", "暴击率提升", "夜幕"],
        }
        
        manager.register_acquired_weapon(
            "熔铸火焰",
            ["智识提升", "攻击提升", "夜幕"],
        )
        
        remaining = manager.get_remaining_weapons()
        
        assert "熔铸火焰" not in remaining
        assert "黯色火炬" in remaining
        assert "扶摇" in remaining
    
    def test_get_remaining_weapons_no_profile(self, manager):
        manager._weapon_data = {
            "熔铸火焰": ["智识提升", "攻击提升", "夜幕"],
        }
        
        remaining = manager.get_remaining_weapons()
        
        assert "熔铸火焰" in remaining


class TestFarmingPlans:
    def test_calculate_farming_plans(self, manager, location_data_file, weapon_data_file):
        profile = manager.create_profile("Test User")
        manager.select_profile(profile.id)
        
        manager._weapon_data = {
            "熔铸火焰": ["智识提升", "攻击提升", "夜幕"],
            "黯色火炬": ["智识提升", "灼热伤害提升", "附术"],
        }
        
        plans = manager.calculate_farming_plans(top_n=5)
        
        assert isinstance(plans, list)
    
    def test_calculate_farming_plans_no_remaining(self, manager, location_data_file, weapon_data_file):
        profile = manager.create_profile("Test User")
        manager.select_profile(profile.id)
        
        manager._weapon_data = {
            "熔铸火焰": ["智识提升", "攻击提升", "夜幕"],
        }
        
        manager.register_acquired_weapon(
            "熔铸火焰",
            ["智识提升", "攻击提升", "夜幕"],
        )
        
        plans = manager.calculate_farming_plans(top_n=5)
        
        assert plans == []
