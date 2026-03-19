import json
import codecs
from itertools import combinations
from pathlib import Path
from typing import Dict, List, Tuple, Set, Literal
from dataclasses import dataclass

DATA_DIR = Path(__file__).parent.parent / "data"
V2_DIR = DATA_DIR / "v2"

StatType = Literal["ATTRIBUTE", "SECONDARY", "SKILL"]


@dataclass
class WeaponInfo:
    name: str
    rarity: int
    requirements: List[str]
    non_base_count: int


@dataclass
class StatInfo:
    name: str
    stat_id: str
    type: StatType


@dataclass
class FarmingPlan:
    location: str
    base_attrs: List[str]
    fourth_attr: str
    attr_type: str
    cover_count: int
    cover_weapons: List[str]
    cover_rarity_sum: int
    plan_hot_sum: int
    plan_weight_sum: int
    partial_match_count: int
    partial_match_weapons: List[str]
    partial_match_rarity_sum: int
    total_score: float
    high_star_cover_count: int


BASE_STATS = {"敏捷提升", "力量提升", "意志提升", "智识提升", "主能力提升"}


def load_essence_stat() -> Dict[str, StatInfo]:
    stat_file = V2_DIR / "EssenceStat.json"
    with codecs.open(stat_file, 'r', 'utf-8-sig') as f:
        data = json.load(f)
    
    result = {}
    for stat_id, info in data.items():
        result[stat_id] = StatInfo(
            name=info["name"],
            stat_id=stat_id,
            type=info["type"]
        )
    return result


def load_weapon_info() -> Dict[str, WeaponInfo]:
    weapon_file = V2_DIR / "Weapon.json"
    stat_info = load_essence_stat()
    
    with codecs.open(weapon_file, 'r', 'utf-8-sig') as f:
        data = json.load(f)
    
    result = {}
    for weapon_id, info in data.items():
        name = info.get("name", "")
        if not name:
            continue
        
        rarity = info.get("rarity", 0)
        requirements = []
        non_base_count = 0
        
        for stat_key in ["stat1_id", "stat2_id", "stat3_id"]:
            stat_id = info.get(stat_key)
            if stat_id and stat_id in stat_info:
                stat = stat_info[stat_id]
                requirements.append(stat.name)
                if stat.name not in BASE_STATS:
                    non_base_count += 1
        
        if len(requirements) >= 2:
            result[name] = WeaponInfo(
                name=name,
                rarity=rarity,
                requirements=requirements,
                non_base_count=non_base_count
            )
    
    return result


def load_location_data() -> Dict[str, Dict[str, List[str]]]:
    location_file = DATA_DIR / "location_essence_data.json"
    with codecs.open(location_file, 'r', 'utf-8-sig') as f:
        return json.load(f)


def calculate_stat_metrics(
    weapon_list: List[str],
    weapon_info: Dict[str, WeaponInfo]
) -> Tuple[Dict[str, int], Dict[str, int]]:
    hot_count: Dict[str, int] = {}
    rarity_weight: Dict[str, int] = {}
    
    for weapon_name in weapon_list:
        if weapon_name not in weapon_info:
            continue
        
        weapon = weapon_info[weapon_name]
        for stat_name in weapon.requirements:
            hot_count[stat_name] = hot_count.get(stat_name, 0) + 1
            rarity_weight[stat_name] = rarity_weight.get(stat_name, 0) + weapon.rarity
    
    return hot_count, rarity_weight


def find_best_plans(
    weapon_list: List[str],
    weapon_data: Dict[str, List[str]] = None,
    location_data: Dict[str, Dict[str, List[str]]] = None,
    top_n: int = 5
) -> List[FarmingPlan]:
    weapon_info = load_weapon_info()
    if location_data is None:
        location_data = load_location_data()
    
    normalized_list = [w.replace(" ", "") for w in weapon_list]
    matched_weapons = []
    for w in normalized_list:
        for name in weapon_info.keys():
            if name.replace(" ", "") == w:
                matched_weapons.append(name)
                break
    
    hot_count, rarity_weight = calculate_stat_metrics(matched_weapons, weapon_info)
    
    plans: List[FarmingPlan] = []
    
    for location, categories in location_data.items():
        base_attrs = categories.get('基础属性', [])
        skill_attrs = categories.get('技能属性', [])
        additional_attrs = categories.get('附加属性', [])
        
        other_attrs = skill_attrs + additional_attrs
        
        for base_combo in combinations(base_attrs, 3):
            base_set = set(base_combo)
            
            for other_attr in other_attrs:
                plan_essences = base_set | {other_attr}
                
                attr_type = "技能属性" if other_attr in skill_attrs else "附加属性"
                
                cover_weapons = []
                cover_rarity_sum = 0
                partial_match_weapons = []
                partial_match_rarity_sum = 0
                high_star_cover_count = 0
                total_score = 0.0
                
                for weapon_name in matched_weapons:
                    weapon = weapon_info[weapon_name]
                    weapon_reqs = set(weapon.requirements)
                    matched_count = len(weapon_reqs & plan_essences)
                    
                    if matched_count >= 3:
                        cover_weapons.append(weapon_name)
                        cover_rarity_sum += weapon.rarity
                        total_score += weapon.rarity
                        if weapon.rarity >= 5:
                            high_star_cover_count += 1
                    elif matched_count >= 2:
                        partial_match_weapons.append(weapon_name)
                        partial_match_rarity_sum += weapon.rarity
                        total_score += weapon.rarity * 0.5
                
                plan_hot_sum = sum(hot_count.get(s, 0) for s in plan_essences)
                plan_weight_sum = sum(rarity_weight.get(s, 0) for s in plan_essences)
                
                total_match_count = len(cover_weapons) + len(partial_match_weapons)
                
                if total_match_count > 0 or plan_hot_sum > 0:
                    plans.append(FarmingPlan(
                        location=location,
                        base_attrs=list(base_combo),
                        fourth_attr=other_attr,
                        attr_type=attr_type,
                        cover_count=len(cover_weapons),
                        cover_weapons=cover_weapons,
                        cover_rarity_sum=cover_rarity_sum,
                        plan_hot_sum=plan_hot_sum,
                        plan_weight_sum=plan_weight_sum,
                        partial_match_count=len(partial_match_weapons),
                        partial_match_weapons=partial_match_weapons,
                        partial_match_rarity_sum=partial_match_rarity_sum,
                        total_score=total_score,
                        high_star_cover_count=high_star_cover_count
                    ))
    
    plans.sort(key=lambda p: (
        p.high_star_cover_count,
        p.total_score,
        p.cover_count,
        p.cover_rarity_sum
    ), reverse=True)
    
    seen_combos: Set[Tuple[Tuple[str, ...], str]] = set()
    unique_plans: List[FarmingPlan] = []
    
    for plan in plans:
        combo_key = (tuple(sorted(plan.base_attrs)), plan.fourth_attr)
        if combo_key not in seen_combos:
            seen_combos.add(combo_key)
            unique_plans.append(plan)
            if len(unique_plans) >= top_n:
                break
    
    return unique_plans


def load_weapon_data(file_path: str | Path | None = None) -> Dict[str, List[str]]:
    weapon_info = load_weapon_info()
    return {name: info.requirements for name, info in weapon_info.items()}


def load_weapon_rarity() -> Dict[str, int]:
    weapon_info = load_weapon_info()
    return {name: info.rarity for name, info in weapon_info.items()}
