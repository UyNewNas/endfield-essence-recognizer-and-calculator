import pytest

from endfield_essence_recognizer.services.essence_calculator import (
    load_location_data,
    load_weapon_data,
    load_weapon_info,
    load_weapon_rarity,
    find_best_plans,
    FarmingPlan,
    WeaponInfo,
)


@pytest.fixture
def location_data():
    return load_location_data()


@pytest.fixture
def weapon_data():
    return load_weapon_data()


class TestLoadFunctions:
    def test_load_location_data(self):
        result = load_location_data()
        assert isinstance(result, dict)
        assert len(result) > 0
    
    def test_load_weapon_data(self):
        result = load_weapon_data()
        assert isinstance(result, dict)
        assert len(result) > 0
    
    def test_load_weapon_info(self):
        result = load_weapon_info()
        assert isinstance(result, dict)
        for name, info in result.items():
            assert isinstance(info, WeaponInfo)
            assert isinstance(info.name, str)
            assert isinstance(info.rarity, int)
            assert isinstance(info.requirements, list)
    
    def test_load_weapon_rarity(self):
        result = load_weapon_rarity()
        assert isinstance(result, dict)
        for name, rarity in result.items():
            assert isinstance(rarity, int)
            assert 1 <= rarity <= 6


class TestFindBestPlans:
    def test_find_best_plans_returns_list(self):
        weapon_list = ["达尔霍夫7", "吉米尼12", "奥佩罗77"]
        
        plans = find_best_plans(weapon_list, top_n=5)
        
        assert isinstance(plans, list)
        assert len(plans) <= 5
    
    def test_find_best_plans_structure(self):
        weapon_list = ["达尔霍夫7", "吉米尼12"]
        
        plans = find_best_plans(weapon_list, top_n=5)
        
        for plan in plans:
            assert isinstance(plan, FarmingPlan)
            assert isinstance(plan.location, str)
            assert isinstance(plan.base_attrs, list)
            assert len(plan.base_attrs) == 3
            assert isinstance(plan.fourth_attr, str)
            assert isinstance(plan.attr_type, str)
            assert isinstance(plan.cover_count, int)
            assert isinstance(plan.cover_weapons, list)
            assert isinstance(plan.cover_rarity_sum, int)
            assert isinstance(plan.plan_hot_sum, int)
            assert isinstance(plan.plan_weight_sum, int)
            assert isinstance(plan.total_score, float)
            assert isinstance(plan.high_star_cover_count, int)
    
    def test_find_best_plans_satisfiable_weapons(self):
        weapon_list = ["达尔霍夫7", "吉米尼12", "奥佩罗77", "佩科5", "塔尔11"]
        
        plans = find_best_plans(weapon_list, top_n=5)
        
        assert len(plans) > 0
        best_plan = plans[0]
        assert best_plan.partial_match_count == 5
    
    def test_find_best_plans_empty_list(self):
        weapon_list = []
        
        plans = find_best_plans(weapon_list, top_n=5)
        
        assert isinstance(plans, list)
    
    def test_find_best_plans_nonexistent_weapon(self):
        weapon_list = ["不存在的武器"]
        
        plans = find_best_plans(weapon_list, top_n=5)
        
        assert isinstance(plans, list)
    
    def test_find_best_plans_high_rarity_weapons(self):
        weapon_list = ["典范", "昔日精品", "大雷斑", "破碎君王", "赫拉芬格"]
        
        plans = find_best_plans(weapon_list, top_n=5)
        
        assert len(plans) > 0
        best_plan = plans[0]
        assert best_plan.partial_match_count > 0 or best_plan.cover_count > 0
        assert len(best_plan.partial_match_weapons) > 0 or len(best_plan.cover_weapons) > 0
    
    def test_find_best_plans_deduplication(self):
        weapon_list = ["典范", "昔日精品", "大雷斑", "破碎君王", "赫拉芬格"]
        
        plans = find_best_plans(weapon_list, top_n=5)
        
        seen_combos = set()
        for plan in plans:
            combo_key = (tuple(sorted(plan.base_attrs)), plan.fourth_attr)
            assert combo_key not in seen_combos, f"发现重复的词条组合: {combo_key}"
            seen_combos.add(combo_key)


class TestWeaponInfo:
    def test_weapon_info_non_base_count(self):
        weapon_info = load_weapon_info()
        
        for name, info in weapon_info.items():
            non_base = sum(
                1 for req in info.requirements
                if req not in ["敏捷提升", "力量提升", "意志提升", "智识提升", "主能力提升"]
            )
            assert info.non_base_count == non_base
