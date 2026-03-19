"""
Stores schema definitions used in FastAPI endpoints.

Contains Enums, Pydantic models, etc. that define the
interface for API requests and responses. Enums may
also be used in other parts of the application.
"""

from endfield_essence_recognizer.schemas.user_profile import (
    UserProfile,
    WeaponEssenceMatch,
    FarmingPlan,
)

__all__ = [
    "UserProfile",
    "WeaponEssenceMatch",
    "FarmingPlan",
]
