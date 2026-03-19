import pytest
from datetime import datetime
import uuid

from endfield_essence_recognizer.schemas.user_profile import (
    WeaponEssenceMatch,
    UserProfile,
    FarmingPlan,
)


class TestWeaponEssenceMatch:
    def test_create_weapon_essence_match(self):
        match = WeaponEssenceMatch(
            weapon_name="熔铸火焰",
            essence_requirements=["智识提升", "攻击提升", "夜幕"],
        )
        
        assert match.weapon_name == "熔铸火焰"
        assert match.essence_requirements == ["智识提升", "攻击提升", "夜幕"]
        assert isinstance(match.matched_at, datetime)
    
    def test_create_weapon_essence_match_with_custom_time(self):
        custom_time = datetime(2024, 1, 1, 12, 0, 0)
        match = WeaponEssenceMatch(
            weapon_name="黯色火炬",
            essence_requirements=["智识提升", "灼热伤害提升", "附术"],
            matched_at=custom_time,
        )
        
        assert match.matched_at == custom_time
    
    def test_essence_requirements_order_matters(self):
        match = WeaponEssenceMatch(
            weapon_name="扶摇",
            essence_requirements=["主能力提升", "暴击率提升", "夜幕"],
        )
        
        assert match.essence_requirements[0] == "主能力提升"
        assert match.essence_requirements[1] == "暴击率提升"
        assert match.essence_requirements[2] == "夜幕"


class TestUserProfile:
    def test_create_user_profile_default_values(self):
        profile = UserProfile()
        
        assert profile.id is not None
        assert uuid.UUID(profile.id)
        assert profile.name == ""
        assert isinstance(profile.created_at, datetime)
        assert isinstance(profile.updated_at, datetime)
        assert profile.acquired_weapons == []
    
    def test_create_user_profile_with_name(self):
        profile = UserProfile(name="测试用户")
        
        assert profile.name == "测试用户"
    
    def test_create_user_profile_with_custom_id(self):
        custom_id = str(uuid.uuid4())
        profile = UserProfile(id=custom_id, name="自定义ID用户")
        
        assert profile.id == custom_id
    
    def test_to_dict(self):
        custom_time = datetime(2024, 1, 1, 12, 0, 0)
        profile = UserProfile(
            id="test-id-123",
            name="测试用户",
            created_at=custom_time,
            updated_at=custom_time,
            acquired_weapons=[
                WeaponEssenceMatch(
                    weapon_name="熔铸火焰",
                    essence_requirements=["智识提升", "攻击提升", "夜幕"],
                    matched_at=custom_time,
                )
            ],
        )
        
        result = profile.to_dict()
        
        assert result["id"] == "test-id-123"
        assert result["name"] == "测试用户"
        assert result["created_at"] == "2024-01-01T12:00:00"
        assert result["updated_at"] == "2024-01-01T12:00:00"
        assert len(result["acquired_weapons"]) == 1
        assert result["acquired_weapons"][0]["weapon_name"] == "熔铸火焰"
        assert result["acquired_weapons"][0]["essence_requirements"] == ["智识提升", "攻击提升", "夜幕"]
    
    def test_from_dict(self):
        data = {
            "id": "test-id-456",
            "name": "从字典加载",
            "created_at": "2024-06-15T10:30:00",
            "updated_at": "2024-06-15T10:30:00",
            "acquired_weapons": [
                {
                    "weapon_name": "黯色火炬",
                    "essence_requirements": ["智识提升", "灼热伤害提升", "附术"],
                    "matched_at": "2024-06-15T10:30:00",
                }
            ],
        }
        
        profile = UserProfile.from_dict(data)
        
        assert profile.id == "test-id-456"
        assert profile.name == "从字典加载"
        assert profile.created_at == datetime(2024, 6, 15, 10, 30, 0)
        assert profile.updated_at == datetime(2024, 6, 15, 10, 30, 0)
        assert len(profile.acquired_weapons) == 1
        assert profile.acquired_weapons[0].weapon_name == "黯色火炬"
    
    def test_from_dict_missing_optional_fields(self):
        data = {
            "id": "test-id-789",
        }
        
        profile = UserProfile.from_dict(data)
        
        assert profile.id == "test-id-789"
        assert profile.name == ""
        assert profile.acquired_weapons == []
    
    def test_from_dict_empty_acquired_weapons(self):
        data = {
            "id": "test-id-empty",
            "name": "空武器列表",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
            "acquired_weapons": [],
        }
        
        profile = UserProfile.from_dict(data)
        
        assert profile.acquired_weapons == []
    
    def test_to_dict_and_from_dict_roundtrip(self):
        original = UserProfile(
            name="往返测试",
            acquired_weapons=[
                WeaponEssenceMatch(
                    weapon_name="扶摇",
                    essence_requirements=["主能力提升", "暴击率提升", "夜幕"],
                )
            ],
        )
        
        data = original.to_dict()
        restored = UserProfile.from_dict(data)
        
        assert restored.id == original.id
        assert restored.name == original.name
        assert len(restored.acquired_weapons) == len(original.acquired_weapons)
        assert restored.acquired_weapons[0].weapon_name == "扶摇"


class TestFarmingPlan:
    def test_create_farming_plan(self):
        plan = FarmingPlan(
            location="枢纽区：",
            base_attrs=["敏捷提升", "智识提升", "主能力提升"],
            skill_attr="攻击提升",
            satisfied_weapons=["熔铸火焰", "扶摇"],
            matched_weapons=["黯色火炬"],
            satisfied_count=2,
            matched_count=1,
        )
        
        assert plan.location == "枢纽区："
        assert plan.base_attrs == ["敏捷提升", "智识提升", "主能力提升"]
        assert plan.skill_attr == "攻击提升"
        assert plan.satisfied_weapons == ["熔铸火焰", "扶摇"]
        assert plan.matched_weapons == ["黯色火炬"]
        assert plan.satisfied_count == 2
        assert plan.matched_count == 1
    
    def test_farming_plan_to_dict(self):
        plan = FarmingPlan(
            location="源石研究园",
            base_attrs=["力量提升", "意志提升", "智识提升"],
            skill_attr="附术",
            satisfied_weapons=["同类相食"],
            matched_weapons=["黯色火炬"],
            satisfied_count=1,
            matched_count=1,
        )
        
        result = plan.to_dict()
        
        assert result["location"] == "源石研究园"
        assert result["base_attrs"] == ["力量提升", "意志提升", "智识提升"]
        assert result["skill_attr"] == "附术"
        assert result["satisfied_weapons"] == ["同类相食"]
        assert result["matched_weapons"] == ["黯色火炬"]
        assert result["satisfied_count"] == 1
        assert result["matched_count"] == 1
    
    def test_farming_plan_empty_lists(self):
        plan = FarmingPlan(
            location="空方案",
            base_attrs=[],
            skill_attr="",
            satisfied_weapons=[],
            matched_weapons=[],
            satisfied_count=0,
            matched_count=0,
        )
        
        assert plan.satisfied_weapons == []
        assert plan.matched_weapons == []
        assert plan.satisfied_count == 0


class TestUserProfileEdgeCases:
    def test_multiple_acquired_weapons(self):
        profile = UserProfile(
            name="多武器用户",
            acquired_weapons=[
                WeaponEssenceMatch(
                    weapon_name=f"武器{i}",
                    essence_requirements=[f"词条{i}a", f"词条{i}b", f"词条{i}c"],
                )
                for i in range(5)
            ],
        )
        
        assert len(profile.acquired_weapons) == 5
        assert profile.acquired_weapons[0].weapon_name == "武器0"
        assert profile.acquired_weapons[4].weapon_name == "武器4"
    
    def test_unicode_name(self):
        profile = UserProfile(name="中文用户名🎉")
        
        assert profile.name == "中文用户名🎉"
        
        data = profile.to_dict()
        restored = UserProfile.from_dict(data)
        
        assert restored.name == "中文用户名🎉"
    
    def test_very_long_name(self):
        long_name = "很长的用户名" * 100
        profile = UserProfile(name=long_name)
        
        assert profile.name == long_name
