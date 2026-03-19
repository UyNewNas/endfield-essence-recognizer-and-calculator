from __future__ import annotations

import threading
from typing import Optional


class CurrentProfileState:
    """
    Global state for the currently selected profile ID.
    This is used by hotkey handlers to know which profile to update.
    """
    
    _instance: Optional[CurrentProfileState] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> CurrentProfileState:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._profile_id: Optional[str] = None
        return cls._instance
    
    @property
    def profile_id(self) -> Optional[str]:
        return self._profile_id
    
    def set_profile_id(self, profile_id: Optional[str]) -> None:
        self._profile_id = profile_id


def get_current_profile_state() -> CurrentProfileState:
    return CurrentProfileState()
