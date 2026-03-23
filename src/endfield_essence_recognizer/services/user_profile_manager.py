import json
import codecs
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from endfield_essence_recognizer.schemas.user_profile import UserProfile, WeaponEssenceMatch
from endfield_essence_recognizer.services.essence_calculator import (
    load_weapon_data,
    load_location_data,
    find_best_plans,
)

DATA_DIR = Path(__file__).parent.parent / "data"


class UserProfileManager:
    def __init__(self, profiles_dir: str = "user_profiles"):
        self.profiles_dir = Path(profiles_dir)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self.current_profile: Optional[UserProfile] = None
        self._weapon_data: Optional[Dict[str, List[str]]] = None
    
    def _get_profile_path(self, profile_id: str) -> Path:
        return self.profiles_dir / f"{profile_id}.json"
    
    def _load_weapon_data(self) -> Dict[str, List[str]]:
        if self._weapon_data is None:
            self._weapon_data = load_weapon_data()
        return self._weapon_data
    
    def create_profile(self, name: str) -> UserProfile:
        profile = UserProfile(name=name)
        self._save_profile(profile)
        return profile
    
    def load_profile(self, profile_id: str) -> Optional[UserProfile]:
        profile_path = self._get_profile_path(profile_id)
        if not profile_path.exists():
            return None
        
        with codecs.open(profile_path, 'r', 'utf-8-sig') as f:
            data = json.load(f)
        
        profile = UserProfile.from_dict(data)
        return profile
    
    def save_profile(self, profile: Optional[UserProfile] = None) -> None:
        if profile is None:
            profile = self.current_profile
        if profile is None:
            return
        
        profile.updated_at = datetime.now()
        self._save_profile(profile)
    
    def _save_profile(self, profile: UserProfile) -> None:
        profile_path = self._get_profile_path(profile.id)
        with codecs.open(profile_path, 'w', 'utf-8-sig') as f:
            json.dump(profile.to_dict(), f, ensure_ascii=False, indent=2)
    
    def select_profile(self, profile_id: str) -> bool:
        profile = self.load_profile(profile_id)
        if profile is None:
            return False
        self.current_profile = profile
        return True
    
    def list_profiles(self) -> List[Dict]:
        profiles = []
        for profile_file in self.profiles_dir.glob("*.json"):
            try:
                profile = self.load_profile(profile_file.stem)
                if profile:
                    profiles.append({
                        "id": profile.id,
                        "name": profile.name,
                        "weapon_count": len(profile.acquired_weapons),
                        "updated_at": profile.updated_at.isoformat(),
                    })
            except Exception:
                continue
        profiles.sort(key=lambda x: x["updated_at"], reverse=True)
        return profiles
    
    def delete_profile(self, profile_id: str) -> bool:
        profile_path = self._get_profile_path(profile_id)
        if not profile_path.exists():
            return False
        
        profile_path.unlink()
        if self.current_profile and self.current_profile.id == profile_id:
            self.current_profile = None
        return True
    
    def register_acquired_weapon(
        self,
        weapon_name: str,
        essence_requirements: List[str],
    ) -> bool:
        if self.current_profile is None:
            return False
        
        weapon_data = self._load_weapon_data()
        if weapon_name not in weapon_data:
            return False
        
        expected_requirements = weapon_data[weapon_name]
        if set(essence_requirements) != set(expected_requirements):
            return False
        
        existing_names = {w.weapon_name for w in self.current_profile.acquired_weapons}
        if weapon_name in existing_names:
            return False
        
        match = WeaponEssenceMatch(
            weapon_name=weapon_name,
            essence_requirements=essence_requirements,
        )
        self.current_profile.acquired_weapons.append(match)
        self.save_profile()
        return True
    
    def unregister_acquired_weapon(self, weapon_name: str) -> bool:
        if self.current_profile is None:
            return False
        
        original_count = len(self.current_profile.acquired_weapons)
        self.current_profile.acquired_weapons = [
            w for w in self.current_profile.acquired_weapons
            if w.weapon_name != weapon_name
        ]
        
        if len(self.current_profile.acquired_weapons) == original_count:
            return False
        
        self.save_profile()
        return True
    
    def get_acquired_weapons(self) -> List[Dict]:
        if self.current_profile is None:
            return []
        
        return [
            {
                "weapon_name": w.weapon_name,
                "essence_requirements": w.essence_requirements,
                "matched_at": w.matched_at.isoformat(),
            }
            for w in self.current_profile.acquired_weapons
        ]
    
    def get_remaining_weapons(self) -> List[str]:
        weapon_data = self._load_weapon_data()
        
        if self.current_profile is None:
            return list(weapon_data.keys())
        
        acquired_names = {w.weapon_name for w in self.current_profile.acquired_weapons}
        return [name for name in weapon_data.keys() if name not in acquired_names]
    
    def calculate_farming_plans(self, top_n: int = 10):
        remaining_weapons = self.get_remaining_weapons()
        
        if not remaining_weapons:
            return []
        
        weapon_data = self._load_weapon_data()
        location_data = load_location_data()
        
        plans = find_best_plans(remaining_weapons, weapon_data, location_data, top_n)
        
        return plans
