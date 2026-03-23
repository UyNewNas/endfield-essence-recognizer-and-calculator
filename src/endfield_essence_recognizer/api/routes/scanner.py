from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from endfield_essence_recognizer.core.interfaces import AutomationEngine
from endfield_essence_recognizer.core.scanner.engine import (
    OneTimeRecognitionEngine,
    ScannerEngine,
)
from endfield_essence_recognizer.core.scanner.context import ScannerContext
from endfield_essence_recognizer.core.window.adapter import WindowActionsAdapter
from endfield_essence_recognizer.core.window.scaling import create_scaling_wrappers
from endfield_essence_recognizer.dependencies import (
    default_user_setting_manager,
    get_delivery_claimer_engine_dep,
    get_one_time_recognition_engine_dep,
    get_scanner_engine_dep,
    get_scanner_service,
    require_game_or_webview_is_active,
    require_game_window_exists,
)
from endfield_essence_recognizer.dependencies.core import (
    get_game_window_manager,
    get_resolution_profile,
)
from endfield_essence_recognizer.dependencies.recognition import (
    get_abandon_status_recognizer_dep,
    get_attribute_level_recognizer_dep,
    get_attribute_recognizer_dep,
    get_lock_status_recognizer_dep,
    get_rarity_recognizer_dep,
    get_ui_scene_recognizer_dep,
)
from endfield_essence_recognizer.dependencies.services import get_static_game_data
from endfield_essence_recognizer.schemas.scanner import TaskType
from endfield_essence_recognizer.services.scanner_service import ScannerService
from endfield_essence_recognizer.services.profile_state import get_current_profile_state
from endfield_essence_recognizer.services.user_profile_manager import UserProfileManager
from endfield_essence_recognizer.services.essence_calculator import (
    load_location_data,
    load_weapon_data,
    find_best_plans,
)
from endfield_essence_recognizer.utils.log import logger

router = APIRouter(prefix="", tags=["scanner"])


class ToggleScanningRequest(BaseModel):
    task_type: TaskType


class StartScanningRequest(BaseModel):
    profile_id: Optional[str] = None


def _create_scanner_context() -> ScannerContext:
    return ScannerContext(
        attr_recognizer=get_attribute_recognizer_dep(),
        attr_level_recognizer=get_attribute_level_recognizer_dep(),
        abandon_status_recognizer=get_abandon_status_recognizer_dep(),
        lock_status_recognizer=get_lock_status_recognizer_dep(),
        rarity_recognizer=get_rarity_recognizer_dep(),
        ui_scene_recognizer=get_ui_scene_recognizer_dep(),
        static_game_data=get_static_game_data(),
    )


def _log_farming_plans(profile_id: str) -> None:
    """
    Log farming plans for remaining weapons after scan completes.
    """
    try:
        from endfield_essence_recognizer.services.essence_calculator import (
            load_weapon_info,
            find_best_plans,
            format_weapon_list,
            sort_weapons,
        )
        
        weapon_info = load_weapon_info()
        
        if profile_id == "temp":
            logger.opt(colors=True).info("<yellow>临时账号模式，不保存武器数据，跳过刷取方案计算</>")
            return
        elif profile_id == "default":
            remaining_weapons = list(weapon_info.keys())
            profile_display = "默认账号"
        else:
            manager = UserProfileManager()
            if not manager.select_profile(profile_id):
                logger.warning(f"无法选择账号 {profile_id}，跳过刷取方案计算")
                return
            remaining_weapons = manager.get_remaining_weapons()
            profile_display = f"账号 {profile_id}"
        
        if not remaining_weapons:
            logger.opt(colors=True).success(
                f"{profile_display} 已获取所有武器的完美基质！"
            )
            return
        
        sorted_weapons = sort_weapons(remaining_weapons, weapon_info)
        formatted_weapons = format_weapon_list(remaining_weapons, weapon_info)
        
        logger.opt(colors=True).info(
            f"{profile_display} 还有 <yellow>{len(remaining_weapons)}</> 把武器未获取完美基质"
        )
        logger.info(f"待刷取武器列表: {formatted_weapons}")
        
        plans = find_best_plans(remaining_weapons, top_n=5)
        
        if not plans:
            logger.warning("无法计算出有效的刷取方案")
            return
        
        logger.info("=" * 60)
        logger.opt(colors=True).info("<green>推荐刷取方案</>")
        logger.info("=" * 60)
        
        for i, plan in enumerate(plans, 1):
            formatted_satisfied = format_weapon_list(plan.satisfied_weapons, weapon_info)
            formatted_location = format_weapon_list(plan.location_weapons, weapon_info)
            
            logger.info(f"")
            logger.opt(colors=True).info(f"<cyan>方案 {i}</>")
            logger.info(f"  刷取地点: 重度能量淤积点·{plan.location}")
            logger.info(f"  基础属性: {'、'.join(plan.base_attrs)}")
            logger.info(f"  {plan.attr_type}: {plan.fourth_attr}")
            
            logger.opt(colors=True).info(
                f"  满足需求 <green>{len(plan.satisfied_weapons)}</> 把武器，"
                f"匹配地点 <yellow>{len(plan.location_weapons)}</> 把武器，"
                f"总分 <magenta>{plan.total_score:.1f}</>"
            )
            if plan.high_star_satisfied_count > 0:
                logger.opt(colors=True).info(
                    f"  <green>高星武器满足需求: {plan.high_star_satisfied_count} 把</>"
                )
            if plan.satisfied_weapons:
                logger.info(f"  满足需求武器: {formatted_satisfied}")
            if plan.location_weapons:
                logger.opt(colors=True).info(f"  <yellow>匹配地点武器</>: {formatted_location}")
        
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"计算刷取方案失败: {e}")


def _create_scanner_engine_with_callback(profile_id: Optional[str] = None) -> ScannerEngine:
    """
    Create a ScannerEngine with optional treasure found callback.
    This function manually builds the engine to support the callback parameter.
    """
    window_manager = get_game_window_manager()
    ctx = _create_scanner_context()
    user_setting_manager = default_user_setting_manager()
    profile = get_resolution_profile()
    
    adapter = WindowActionsAdapter(window_manager)
    image_source, window_actions = create_scaling_wrappers(adapter, adapter)
    
    on_treasure_found = None
    on_scan_complete = None
    
    effective_profile_id = profile_id if profile_id else "temp"
    
    if effective_profile_id and effective_profile_id not in ("temp", "default"):
        static_data = get_static_game_data()
        
        def on_treasure_found_callback(stats_names: list[str], weapon_ids: list[str]) -> None:
            try:
                manager = UserProfileManager()
                if not manager.select_profile(effective_profile_id):
                    logger.warning(f"无法选择账号 {effective_profile_id}")
                    return
                    
                for weapon_id in weapon_ids:
                    weapon = static_data.get_weapon(weapon_id)
                    if weapon:
                        weapon_name = weapon.name
                        result = manager.register_acquired_weapon(weapon_name, stats_names)
                        if result:
                            logger.info(f"已将武器 {weapon_name} 记录到账号 {effective_profile_id}")
                        else:
                            logger.debug(f"武器 {weapon_name} 未记录（可能已存在或词条不匹配）")
            except Exception as e:
                logger.error(f"记录武器到账号失败: {e}")
        
        on_treasure_found = on_treasure_found_callback
    
    def on_scan_complete_callback(treasure_weapons_found: list[tuple[list[str], list[str]]]) -> None:
        _log_farming_plans(effective_profile_id)
    
    on_scan_complete = on_scan_complete_callback
    
    return ScannerEngine(
        ctx=ctx,
        image_source=image_source,
        window_actions=window_actions,
        user_setting_manager=user_setting_manager,
        profile=profile,
        on_treasure_found=on_treasure_found,
        on_scan_complete=on_scan_complete,
    )


@router.post(
    "/recognize_once",
    dependencies=[
        Depends(require_game_or_webview_is_active),
        Depends(require_game_window_exists),
    ],
)
async def recognize_once(
    engine: OneTimeRecognitionEngine = Depends(get_one_time_recognition_engine_dep),
    scanner_service: ScannerService = Depends(get_scanner_service),
) -> None:
    scanner_service.start_scan(scanner_factory=lambda: engine)


@router.post(
    "/start_scanning",
    dependencies=[
        Depends(require_game_or_webview_is_active),
        Depends(require_game_window_exists),
    ],
)
async def start_scanning(
    request: Optional[StartScanningRequest] = None,
    scanner_service: ScannerService = Depends(get_scanner_service),
) -> None:
    profile_id = request.profile_id if request else None
    
    if profile_id:
        get_current_profile_state().set_profile_id(profile_id)
    
    def create_engine() -> ScannerEngine:
        return _create_scanner_engine_with_callback(profile_id)
    
    scanner_service.toggle_scan(scanner_factory=create_engine)


@router.post(
    "/toggle_scanning",
    dependencies=[
        Depends(require_game_or_webview_is_active),
        Depends(require_game_window_exists),
    ],
)
async def toggle_scanning(
    request: ToggleScanningRequest,
    scanner_service: ScannerService = Depends(get_scanner_service),
    essence_engine: ScannerEngine = Depends(get_scanner_engine_dep),
    delivery_engine: AutomationEngine = Depends(get_delivery_claimer_engine_dep),
) -> None:
    if request.task_type == TaskType.ESSENCE:
        profile_id = get_current_profile_state().profile_id
        
        def get_engine() -> ScannerEngine:
            return _create_scanner_engine_with_callback(profile_id)
        
        scanner_service.toggle_scan(scanner_factory=get_engine)
    else:
        def get_engine() -> AutomationEngine:
            match request.task_type:
                case TaskType.DELIVERY_CLAIM:
                    return delivery_engine
                case _:
                    raise ValueError(f"Unsupported task type: {request.task_type}")
        
        scanner_service.toggle_scan(scanner_factory=get_engine)
