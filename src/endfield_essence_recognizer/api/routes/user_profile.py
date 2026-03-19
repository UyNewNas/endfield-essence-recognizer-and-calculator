from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from endfield_essence_recognizer.services.user_profile_manager import UserProfileManager

router = APIRouter(prefix="/user-profile", tags=["user-profile"])

profile_manager = UserProfileManager()


class CreateProfileRequest(BaseModel):
    name: str


class RegisterWeaponRequest(BaseModel):
    weapon_name: str
    essence_requirements: List[str]


class ProfileResponse(BaseModel):
    id: str
    name: str
    weapon_count: int
    updated_at: str


class ProfileDetailResponse(BaseModel):
    id: str
    name: str
    created_at: str
    updated_at: str
    acquired_weapons: List[dict]


class FarmingPlanResponse(BaseModel):
    location: str
    base_attrs: List[str]
    skill_attr: str
    satisfied_weapons: List[str]
    matched_weapons: List[str]
    satisfied_count: int
    matched_count: int


@router.post("/create", response_model=ProfileResponse)
async def create_profile(request: CreateProfileRequest):
    profile = profile_manager.create_profile(request.name)
    return ProfileResponse(
        id=profile.id,
        name=profile.name,
        weapon_count=len(profile.acquired_weapons),
        updated_at=profile.updated_at.isoformat(),
    )


@router.get("/list", response_model=List[ProfileResponse])
async def list_profiles():
    profiles = profile_manager.list_profiles()
    return [
        ProfileResponse(
            id=p["id"],
            name=p["name"],
            weapon_count=p["weapon_count"],
            updated_at=p["updated_at"],
        )
        for p in profiles
    ]


@router.post("/select/{profile_id}")
async def select_profile(profile_id: str):
    if not profile_manager.select_profile(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"message": "Profile selected", "profile_id": profile_id}


@router.get("/current", response_model=Optional[ProfileDetailResponse])
async def get_current_profile():
    if profile_manager.current_profile is None:
        return None
    
    profile = profile_manager.current_profile
    return ProfileDetailResponse(
        id=profile.id,
        name=profile.name,
        created_at=profile.created_at.isoformat(),
        updated_at=profile.updated_at.isoformat(),
        acquired_weapons=profile_manager.get_acquired_weapons(),
    )


@router.delete("/{profile_id}")
async def delete_profile(profile_id: str):
    if not profile_manager.delete_profile(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"message": "Profile deleted"}


@router.post("/weapons/register")
async def register_acquired_weapon(request: RegisterWeaponRequest):
    if profile_manager.current_profile is None:
        raise HTTPException(status_code=400, detail="No profile selected")
    
    if not profile_manager.register_acquired_weapon(
        request.weapon_name,
        request.essence_requirements,
    ):
        raise HTTPException(
            status_code=400,
            detail="Failed to register weapon. Check if weapon exists and requirements match."
        )
    
    return {"message": "Weapon registered", "weapon_name": request.weapon_name}


@router.delete("/weapons/{weapon_name}")
async def unregister_acquired_weapon(weapon_name: str):
    if profile_manager.current_profile is None:
        raise HTTPException(status_code=400, detail="No profile selected")
    
    if not profile_manager.unregister_acquired_weapon(weapon_name):
        raise HTTPException(status_code=404, detail="Weapon not found in acquired list")
    
    return {"message": "Weapon unregistered", "weapon_name": weapon_name}


@router.get("/weapons/acquired")
async def get_acquired_weapons():
    if profile_manager.current_profile is None:
        raise HTTPException(status_code=400, detail="No profile selected")
    
    return profile_manager.get_acquired_weapons()


@router.get("/weapons/remaining")
async def get_remaining_weapons():
    if profile_manager.current_profile is None:
        raise HTTPException(status_code=400, detail="No profile selected")
    
    return profile_manager.get_remaining_weapons()


@router.get("/farming-plans", response_model=List[FarmingPlanResponse])
async def get_farming_plans(top_n: int = 10):
    if profile_manager.current_profile is None:
        raise HTTPException(status_code=400, detail="No profile selected")
    
    plans = profile_manager.calculate_farming_plans(top_n=top_n)
    
    return [
        FarmingPlanResponse(
            location=plan[0],
            base_attrs=plan[1],
            skill_attr=plan[2],
            satisfied_weapons=plan[4],
            matched_weapons=plan[6],
            satisfied_count=plan[3],
            matched_count=plan[5],
        )
        for plan in plans
    ]
