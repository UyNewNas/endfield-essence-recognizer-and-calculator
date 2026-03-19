from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
import uuid


@dataclass
class WeaponEssenceMatch:
    weapon_name: str
    essence_requirements: List[str]
    matched_at: datetime = field(default_factory=datetime.now)
    

@dataclass
class UserProfile:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    acquired_weapons: List[WeaponEssenceMatch] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "acquired_weapons": [
                {
                    "weapon_name": w.weapon_name,
                    "essence_requirements": w.essence_requirements,
                    "matched_at": w.matched_at.isoformat(),
                }
                for w in self.acquired_weapons
            ],
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "UserProfile":
        acquired_weapons = []
        for w in data.get("acquired_weapons", []):
            acquired_weapons.append(WeaponEssenceMatch(
                weapon_name=w["weapon_name"],
                essence_requirements=w["essence_requirements"],
                matched_at=datetime.fromisoformat(w["matched_at"]),
            ))
        
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
            acquired_weapons=acquired_weapons,
        )


@dataclass
class FarmingPlan:
    location: str
    base_attrs: List[str]
    skill_attr: str
    satisfied_weapons: List[str]
    matched_weapons: List[str]
    satisfied_count: int
    matched_count: int
    
    def to_dict(self) -> dict:
        return {
            "location": self.location,
            "base_attrs": self.base_attrs,
            "skill_attr": self.skill_attr,
            "satisfied_weapons": self.satisfied_weapons,
            "matched_weapons": self.matched_weapons,
            "satisfied_count": self.satisfied_count,
            "matched_count": self.matched_count,
        }
