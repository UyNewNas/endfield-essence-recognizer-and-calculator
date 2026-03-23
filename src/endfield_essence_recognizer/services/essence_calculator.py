import json
import codecs
from itertools import combinations
from pathlib import Path
from typing import Dict, List, Tuple, Set, Literal
from dataclasses import dataclass

DATA_DIR = Path(__file__).parent.parent / "data"
V2_DIR = DATA_DIR / "v2"

StatType = Literal["ATTRIBUTE", "SECONDARY", "SKILL"]

WEAPON_TYPE_NAMES = {
    "SWORD": "单手剑",
    "CLAYM": "双手剑",
    "LANCE": "长柄武器",
    "PISTOL": "手铳",
    "WAND": "施术单元",
}

WEAPON_TYPE_ORDER = {
    "SWORD": 0,
    "CLAYM": 1,
    "LANCE": 2,
    "PISTOL": 3,
    "WAND": 4,
}


@dataclass
class WeaponInfo:
    name: str
    rarity: int
    requirements: List[str]
    non_base_count: int
    weapon_type: str
    
    @property
    def weapon_type_name(self) -> str:
        return WEAPON_TYPE_NAMES.get(self.weapon_type, self.weapon_type)
    
    @property
    def display_name(self) -> str:
        return f"{self.name}（{self.rarity}★ {self.weapon_type_name}）"


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
    satisfied_weapons: List[str]
    satisfied_rarity_sum: int
    location_weapons: List[str]
    location_rarity_sum: int
    total_score: float
    high_star_satisfied_count: int


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
        weapon_type = info.get("weapon_type", "")
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
                non_base_count=non_base_count,
                weapon_type=weapon_type
            )
    
    return result


def load_location_data() -> Dict[str, Dict[str, List[str]]]:
    location_file = DATA_DIR / "location_essence_data.json"
    with codecs.open(location_file, 'r', 'utf-8-sig') as f:
        return json.load(f)


def sort_weapons(weapon_names: List[str], weapon_info: Dict[str, WeaponInfo]) -> List[str]:
    """按星级主排序，武器类型次排序"""
    def sort_key(name: str):
        info = weapon_info.get(name)
        if info:
            return (-info.rarity, WEAPON_TYPE_ORDER.get(info.weapon_type, 999), name)
        return (0, 999, name)
    
    return sorted(weapon_names, key=sort_key)


def sort_weapons_by_type(weapon_names: List[str], weapon_info: Dict[str, WeaponInfo]) -> List[str]:
    """按武器类型主排序，星级次排序"""
    def sort_key(name: str):
        info = weapon_info.get(name)
        if info:
            return (WEAPON_TYPE_ORDER.get(info.weapon_type, 999), -info.rarity, name)
        return (999, 0, name)
    
    return sorted(weapon_names, key=sort_key)


def format_weapon_list(weapon_names: List[str], weapon_info: Dict[str, WeaponInfo]) -> str:
    """格式化武器列表（不超过5个时使用）"""
    sorted_names = sort_weapons(weapon_names, weapon_info)
    formatted = []
    for name in sorted_names:
        info = weapon_info.get(name)
        if info:
            formatted.append(info.display_name)
        else:
            formatted.append(name)
    return "、".join(formatted)


def format_weapon_list_detailed(weapon_names: List[str], weapon_info: Dict[str, WeaponInfo]) -> List[str]:
    """格式化武器列表（超过5个时使用），按武器类型分组输出，带颜色标签"""
    sorted_names = sort_weapons_by_type(weapon_names, weapon_info)
    
    def get_rarity_format(rarity: int) -> Tuple[str, str]:
        if rarity == 6:
            return "<bold><yellow>", "</></>"
        elif rarity == 5:
            return "<yellow>", "</>"
        elif rarity == 4:
            return "<magenta>", "</>"
        elif rarity == 3:
            return "<blue>", "</>"
        return "", ""
    
    type_groups: Dict[str, List[str]] = {}
    for name in sorted_names:
        info = weapon_info.get(name)
        if info:
            type_name = info.weapon_type_name
            if type_name not in type_groups:
                type_groups[type_name] = []
            open_tag, close_tag = get_rarity_format(info.rarity)
            type_groups[type_name].append(f"{name}（{open_tag}{info.rarity}★{close_tag}）")
        else:
            if "未知" not in type_groups:
                type_groups["未知"] = []
            type_groups["未知"].append(name)
    
    lines = []
    for type_name in ["单手剑", "双手剑", "长柄武器", "手铳", "施术单元", "未知"]:
        if type_name in type_groups:
            lines.append(f"(<bold>{type_name}</>): {'、'.join(type_groups[type_name])}")
    
    return lines


def format_weapon_list_auto(weapon_names: List[str], weapon_info: Dict[str, WeaponInfo]) -> Tuple[str, List[str]]:
    """
    自动选择格式化方式
    返回: (单行格式, 多行格式列表)
    如果不超过5个，多行格式列表为空
    """
    single_line = format_weapon_list(weapon_names, weapon_info)
    
    if len(weapon_names) <= 5:
        return single_line, []
    
    multi_line = format_weapon_list_detailed(weapon_names, weapon_info)
    return single_line, multi_line


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
    
    plans: List[FarmingPlan] = []
    
    for location, categories in location_data.items():
        base_attrs = categories.get('基础属性', [])
        skill_attrs = categories.get('技能属性', [])
        additional_attrs = categories.get('附加属性', [])
        
        location_pool = set(base_attrs) | set(skill_attrs) | set(additional_attrs)
        other_attrs = skill_attrs + additional_attrs
        
        location_weapons = []
        location_rarity_sum = 0
        for weapon_name in matched_weapons:
            weapon = weapon_info[weapon_name]
            weapon_reqs = set(weapon.requirements)
            if weapon_reqs <= location_pool:
                location_weapons.append(weapon_name)
                location_rarity_sum += weapon.rarity
        
        for base_combo in combinations(base_attrs, 3):
            base_set = set(base_combo)
            
            for other_attr in other_attrs:
                attr_type = "技能属性" if other_attr in skill_attrs else "附加属性"
                
                satisfied_weapons = []
                satisfied_rarity_sum = 0
                high_star_satisfied_count = 0
                total_score = 0.0
                
                for weapon_name in matched_weapons:
                    weapon = weapon_info[weapon_name]
                    weapon_reqs = set(weapon.requirements)
                    
                    has_match = False
                    for base_attr in base_combo:
                        combo = {base_attr, other_attr}
                        if combo <= weapon_reqs:
                            has_match = True
                            break
                    
                    if has_match:
                        satisfied_weapons.append(weapon_name)
                        satisfied_rarity_sum += weapon.rarity
                        total_score += weapon.rarity
                        if weapon.rarity >= 5:
                            high_star_satisfied_count += 1
                
                if len(satisfied_weapons) > 0:
                    plans.append(FarmingPlan(
                        location=location,
                        base_attrs=list(base_combo),
                        fourth_attr=other_attr,
                        attr_type=attr_type,
                        satisfied_weapons=satisfied_weapons,
                        satisfied_rarity_sum=satisfied_rarity_sum,
                        location_weapons=location_weapons,
                        location_rarity_sum=location_rarity_sum,
                        total_score=total_score,
                        high_star_satisfied_count=high_star_satisfied_count
                    ))
    
    plans.sort(key=lambda p: (
        p.high_star_satisfied_count,
        p.total_score,
        len(p.satisfied_weapons),
        p.satisfied_rarity_sum
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
