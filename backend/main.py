import asyncio
import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, Header, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps, UnidentifiedImageError
import pillow_avif
from pydantic import BaseModel, Field
import uvicorn

from services.vision_service import (
    VisionServiceError,
    analyze_food_image,
    generate_alternative_suggestions,
    generate_history_advice,
)
from utils.db import (
    add_friend,
    cleanup_expired_diet_records,
    get_or_create_user,
    get_today_friend_feed,
    init_db,
    save_diet_record,
)
from utils.cleanup import enforce_storage_limit, periodic_cleanup
from utils.nutrition import (
    build_backend_risk_flags,
    has_nutrition_data,
    infer_nutrition_tags,
    merge_risk_flags,
    normalize_nutrition_tags,
    normalize_nutrition_totals,
    normalize_risk_flags,
    sort_risk_flags,
)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

ALLOWED_IMAGE_FORMATS = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "WEBP": ".webp",
    "BMP": ".bmp",
    "AVIF": ".avif",
}
DISALLOWED_CONTENT_TYPES = {"image/svg+xml", "text/html"}
CHUNK_SIZE = 1024 * 1024
RESAMPLING_LANCZOS = getattr(getattr(Image, "Resampling", Image), "LANCZOS")

BASE_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)


class UploadValidationError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _load_int(name, default, min_value=1, max_value=None, aliases=None):
    raw_value = str(default).strip()
    source_name = name
    for candidate in [name, *(aliases or [])]:
        env_value = os.getenv(candidate)
        if env_value is None or not str(env_value).strip():
            continue
        raw_value = str(env_value).strip()
        source_name = candidate
        break

    try:
        parsed = int(raw_value)
    except (TypeError, ValueError):
        logger.warning("Invalid %s=%s, fallback to %s", source_name, raw_value, default)
        return default

    if parsed < min_value or (max_value is not None and parsed > max_value):
        logger.warning("Invalid %s=%s, fallback to %s", source_name, raw_value, default)
        return default

    return parsed


MAX_UPLOAD_SIZE_MB = _load_int("MAX_UPLOAD_SIZE_MB", 10)
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
THUMBNAIL_RETENTION_DAYS = _load_int(
    "THUMBNAIL_RETENTION_DAYS",
    30,
    aliases=["UPLOAD_RETENTION_DAYS"],
)
THUMBNAIL_MAX_EDGE = _load_int("THUMBNAIL_MAX_EDGE", 512)
THUMBNAIL_QUALITY = _load_int("THUMBNAIL_QUALITY", 70, min_value=1, max_value=100)
UPLOAD_STORAGE_LIMIT_MB = _load_int("UPLOAD_STORAGE_LIMIT_MB", 3072)
UPLOAD_STORAGE_LIMIT_BYTES = UPLOAD_STORAGE_LIMIT_MB * 1024 * 1024


async def _periodic_database_cleanup(
    retention_days: int,
    stop_event: asyncio.Event,
    interval_hours: int = 24,
):
    while True:
        try:
            cleanup_expired_diet_records(retention_days)
        except Exception:
            logger.exception("Failed to cleanup expired diet records")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_hours * 3600)
            break
        except asyncio.TimeoutError:
            continue


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    _migrate_legacy_webp_thumbnails()
    stop_event = asyncio.Event()
    cleanup_task = asyncio.create_task(
        periodic_cleanup(
            str(UPLOADS_DIR),
            days=THUMBNAIL_RETENTION_DAYS,
            interval_hours=24,
            stop_event=stop_event,
            max_total_size_bytes=UPLOAD_STORAGE_LIMIT_BYTES,
        )
    )
    database_cleanup_task = asyncio.create_task(
        _periodic_database_cleanup(
            retention_days=THUMBNAIL_RETENTION_DAYS,
            stop_event=stop_event,
        )
    )
    app.state.cleanup_stop_event = stop_event
    app.state.cleanup_task = cleanup_task
    app.state.database_cleanup_task = database_cleanup_task
    try:
        yield
    finally:
        stop_event.set()
        await cleanup_task
        await database_cleanup_task


app = FastAPI(title="LifeLens API", version="1.0.0", lifespan=lifespan)


def _load_cors_origins():
    raw = os.getenv("CORS_ALLOW_ORIGINS", "*").strip()
    if raw == "*":
        return ["*"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def _safe_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


HEALTH_CONDITION_ALIASES = {
    "diabetes": ("diabetes", "糖尿病"),
    "hypertension": ("hypertension", "高血压"),
    "high_cholesterol": ("high cholesterol", "高胆固醇", "胆固醇"),
    "gluten_free": ("gluten free", "gluten-free", "无麸质"),
    "lactose_intolerant": ("lactose intolerant", "乳糖不耐受", "乳糖"),
}

GOAL_ALIASES = {
    "diabetes": ("diabetes", "糖尿病"),
    "muscle_gain": ("muscle_gain", "增肌"),
    "weight_loss": ("weight_loss", "减脂", "瘦身"),
}

RISK_REASON_COPY = {
    "high_calorie": "总热量偏高",
    "high_sugar": "糖含量偏高",
    "high_sodium": "钠含量偏高",
    "high_fat": "脂肪含量偏高",
    "high_saturated_fat": "饱和脂肪偏高",
    "low_protein": "蛋白质偏低",
    "low_fiber": "膳食纤维偏低",
    "allergen_risk": "存在过敏原风险",
    "gluten_risk": "存在麸质风险",
    "lactose_risk": "存在乳糖风险",
}
DEFAULT_HISTORY_ADVICE_WINDOW_DAYS = 0
DEFAULT_HISTORY_ADVICE_QUESTION = "请结合我的饮食记录，给我一些有帮助的观察和建议"


def _normalize_traffic_light(value, default="yellow"):
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"green", "yellow", "red"}:
            return normalized
    return default


def _normalize_text_list(value):
    if not isinstance(value, list):
        return []
    return [str(item or "").strip().lower() for item in value if str(item or "").strip()]


def _normalize_display_list(value, limit):
    if not isinstance(value, list):
        return []

    normalized = []
    for item in value:
        text = str(item or "").strip()
        if not text or text in normalized:
            continue
        normalized.append(text)
        if len(normalized) >= limit:
            break
    return normalized


def _matches_condition(conditions, condition_key):
    keywords = HEALTH_CONDITION_ALIASES.get(condition_key, ())
    return any(keyword in condition for condition in conditions for keyword in keywords)


def _matches_goal(goal, goal_key):
    normalized_goal = str(goal or "").strip().lower()
    keywords = GOAL_ALIASES.get(goal_key, ())
    return any(keyword in normalized_goal for keyword in keywords)


def _default_risk_reason(code):
    return RISK_REASON_COPY.get(code, "存在需要关注的营养风险")


def _build_warning_message(traffic_light, reasons):
    if traffic_light == "green":
        return ""

    unique_reasons = []
    for reason in reasons:
        normalized = str(reason or "").strip()
        if not normalized or normalized in unique_reasons:
            continue
        unique_reasons.append(normalized)

    if not unique_reasons:
        return ""

    prefix = "这餐需要注意：" if traffic_light == "yellow" else "这餐风险较高："
    suffix = (
        "。建议控制分量并优化搭配。"
        if traffic_light == "yellow"
        else "。建议优先更换食材或减少摄入。"
    )
    return prefix + "；".join(unique_reasons[:2]) + suffix


def _evaluate_meal_risk(risk_flags, user_context):
    normalized_flags = sort_risk_flags(normalize_risk_flags(risk_flags))
    codes = {flag["code"] for flag in normalized_flags}
    conditions = _normalize_text_list((user_context or {}).get("health_conditions"))
    goal = (user_context or {}).get("goal")
    traffic_rank = 0
    reasons = []

    def raise_to(color, reason):
        nonlocal traffic_rank
        rank = {"green": 0, "yellow": 1, "red": 2}[color]
        traffic_rank = max(traffic_rank, rank)
        normalized_reason = str(reason or "").strip()
        if normalized_reason and normalized_reason not in reasons:
            reasons.append(normalized_reason)

    for flag in normalized_flags:
        raise_to("yellow", flag.get("reason") or _default_risk_reason(flag["code"]))

    has_any_allergy = any("allergy" in condition or "过敏" in condition for condition in conditions)
    if "allergen_risk" in codes and has_any_allergy:
        raise_to("red", "检测到潜在过敏原，与当前饮食禁忌直接冲突")
    if "gluten_risk" in codes and _matches_condition(conditions, "gluten_free"):
        raise_to("red", "这餐可能含麸质，不符合当前无麸质需求")
    if "lactose_risk" in codes and _matches_condition(conditions, "lactose_intolerant"):
        raise_to("red", "这餐可能含较多乳糖，不适合乳糖不耐受人群")

    if "high_sugar" in codes:
        if _matches_condition(conditions, "diabetes") or _matches_goal(goal, "diabetes"):
            raise_to("red", "糖分偏高，对血糖管理不太友好")
        else:
            raise_to("yellow", "糖分偏高，建议减少额外糖来源")

    if "high_sodium" in codes:
        if _matches_condition(conditions, "hypertension"):
            raise_to("red", "钠含量偏高，不利于高血压管理")
        else:
            raise_to("yellow", "钠含量偏高，建议减少高盐配料")

    if "high_saturated_fat" in codes:
        if _matches_condition(conditions, "high_cholesterol"):
            raise_to("red", "饱和脂肪偏高，不利于胆固醇控制")
        else:
            raise_to("yellow", "饱和脂肪偏高，建议减少油炸和肥肉来源")

    if "low_protein" in codes and _matches_goal(goal, "muscle_gain"):
        raise_to("yellow", "蛋白质偏低，不利于增肌目标")

    if "high_calorie" in codes and _matches_goal(goal, "weight_loss"):
        if "high_fat" in codes or "low_protein" in codes:
            raise_to("red", "总热量偏高且营养结构不理想，不利于减脂目标")
        else:
            raise_to("yellow", "总热量偏高，建议控制份量以贴合减脂目标")

    traffic_light = {0: "green", 1: "yellow", 2: "red"}[traffic_rank]
    return traffic_light, _build_warning_message(traffic_light, reasons)


def _derive_item_traffic_light(item, risk_flags):
    explicit = _normalize_traffic_light(item.get("traffic_light"), "")
    if explicit:
        return explicit
    if any(flag.get("severity") == "high" for flag in risk_flags):
        return "red"
    if risk_flags:
        return "yellow"
    return "green"


def _normalize_items(items):
    normalized_items = []
    if not isinstance(items, list):
        return normalized_items

    for item in items:
        if not isinstance(item, dict):
            continue
        nutrition = normalize_nutrition_totals(
            item.get("nutrition"), fallback_calories=item.get("calories")
        )
        risk_flags = normalize_risk_flags(item.get("risk_flags"))
        tags = normalize_nutrition_tags(item.get("nutrition_tags")) or infer_nutrition_tags(
            nutrition, risk_flags
        )
        normalized_items.append(
            {
                "name": str(item.get("name") or "未知菜品"),
                "calories": nutrition["calories_kcal"],
                "unit": str(item.get("unit") or "kcal"),
                "nutrition": nutrition,
                "nutrition_tags": tags,
                "risk_flags": risk_flags,
                "ingredient_evidence": str(
                    item.get("ingredient_evidence") or item.get("evidence") or ""
                ),
                "traffic_light": _derive_item_traffic_light(item, risk_flags),
            }
        )
    return normalized_items


def _normalize_analysis_result(result, user_context=None):
    if not isinstance(result, dict):
        raise ValueError("Invalid analysis response format")

    items = _normalize_items(result.get("items"))
    fallback_name = items[0]["name"] if items else "未知菜品"
    total_analysis = result.get("total_analysis")
    if not isinstance(total_analysis, dict):
        total_analysis = {}

    confidence = _safe_float(total_analysis.get("confidence"), 0.0)
    confidence = max(0.0, min(1.0, confidence))
    model_totals = normalize_nutrition_totals(
        result.get("nutrition_totals"), fallback_calories=result.get("total_calories")
    )
    item_totals = normalize_nutrition_totals()
    if items:
        summed = {}
        for key, value in items[0]["nutrition"].items():
            summed[key] = 0
        for item in items:
            for key, value in item["nutrition"].items():
                summed[key] += _safe_float(value, 0.0)
        item_totals = normalize_nutrition_totals(summed)

    if items and has_nutrition_data(item_totals):
        nutrition_totals = item_totals
    elif has_nutrition_data(model_totals):
        nutrition_totals = model_totals
    else:
        nutrition_totals = normalize_nutrition_totals(
            None, fallback_calories=result.get("total_calories")
        )

    model_risk_flags = normalize_risk_flags(result.get("risk_flags"))
    item_risk_flags = []
    for item in items:
        item_risk_flags.extend(item.get("risk_flags", []))
    risk_flags = merge_risk_flags(
        model_risk_flags,
        item_risk_flags,
        build_backend_risk_flags(nutrition_totals),
    )
    nutrition_tags = normalize_nutrition_tags(
        result.get("nutrition_tags")
    ) or infer_nutrition_tags(nutrition_totals, risk_flags)
    total_traffic_light, warning_message = _evaluate_meal_risk(risk_flags, user_context)

    return {
        "main_name": str(result.get("main_name") or fallback_name),
        "total_calories": nutrition_totals["calories_kcal"],
        "nutrition_totals": nutrition_totals,
        "nutrition_tags": nutrition_tags,
        "risk_flags": risk_flags,
        "total_traffic_light": total_traffic_light,
        "warning_message": warning_message,
        "thought_process": str(result.get("thought_process") or ""),
        "items": items,
        "total_analysis": {
            "summary": str(total_analysis.get("summary") or "暂无分析摘要"),
            "suggestion": str(total_analysis.get("suggestion") or "暂无建议"),
            "confidence": confidence,
        },
    }


def _normalize_alternatives_result(result):
    if not isinstance(result, dict):
        raise ValueError("Invalid alternatives response format")
    return {
        "ordering_hint": str(result.get("ordering_hint") or "暂无点餐建议"),
        "cooking_hint": str(result.get("cooking_hint") or "暂无烹饪建议"),
    }


def _normalize_history_advice_question(question):
    normalized = str(question or "").strip()
    return normalized or DEFAULT_HISTORY_ADVICE_QUESTION


def _normalize_history_advice_result(result):
    if not isinstance(result, dict):
        raise ValueError("Invalid history advice response format")

    return {
        "answer": str(
            result.get("answer") or "已收到你的饮食记录，可以继续针对今天、最近或整体习惯提问。"
        ).strip(),
        "observations": _normalize_display_list(result.get("observations"), 3),
        "suggestions": _normalize_display_list(result.get("suggestions"), 3),
        "focus_tags": _normalize_display_list(result.get("focus_tags"), 4),
    }


def _error_response(message, status_code=500, trace_id=None):
    payload = {
        "code": status_code,
        "message": str(message),
    }
    if trace_id:
        payload["trace_id"] = trace_id
    return JSONResponse(status_code=status_code, content=payload)


def _delete_file(file_path):
    if not file_path:
        return
    path = Path(file_path)
    if path.exists():
        path.unlink(missing_ok=True)


def _to_utc_iso(dt):
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _build_image_expiration():
    return _to_utc_iso(datetime.now(timezone.utc) + timedelta(days=THUMBNAIL_RETENTION_DAYS))


def _require_user_id(raw_user_id):
    normalized = str(raw_user_id or "").strip()
    if not normalized:
        raise UploadValidationError("缺少用户身份标识", status_code=401)
    return normalized


def _migrate_legacy_webp_thumbnails():
    migrated_count = 0
    for webp_path in UPLOADS_DIR.glob("*.webp"):
        jpg_path = webp_path.with_suffix(".jpg")

        if jpg_path.exists():
            webp_path.unlink(missing_ok=True)
            migrated_count += 1
            continue

        try:
            with Image.open(webp_path) as source_image:
                image = _prepare_thumbnail_image(source_image)
                image.save(
                    jpg_path,
                    "JPEG",
                    quality=THUMBNAIL_QUALITY,
                    optimize=True,
                )
            webp_path.unlink(missing_ok=True)
            migrated_count += 1
        except Exception:
            logger.exception("Failed to migrate legacy thumbnail %s", webp_path.name)

    if migrated_count:
        logger.info("Migrated %s legacy WebP thumbnails to JPEG", migrated_count)


def _parse_user_context(raw_user_context):
    try:
        parsed = json.loads(raw_user_context)
    except json.JSONDecodeError as exc:
        raise UploadValidationError("用户档案格式无效", status_code=400) from exc

    return _normalize_user_context_dict(parsed)


def _normalize_user_context_dict(parsed):
    if not isinstance(parsed, dict):
        raise UploadValidationError("用户档案格式无效", status_code=400)

    normalized = dict(parsed)

    health_conditions = normalized.get("health_conditions")
    if not isinstance(health_conditions, list):
        normalized["health_conditions"] = []
    else:
        normalized["health_conditions"] = [str(item) for item in health_conditions]

    normalized["goal"] = str(normalized.get("goal") or "").strip()

    return normalized


def _detect_image_format(file_path):
    try:
        with Image.open(file_path) as image:
            image.verify()
        with Image.open(file_path) as image:
            detected_format = (image.format or "").upper()
    except (UnidentifiedImageError, OSError) as exc:
        logger.warning("Rejected invalid image file %s: %s", file_path, exc)
        raise UploadValidationError("仅支持 JPG、PNG、WEBP、BMP、AVIF 图片", 415) from exc

    if detected_format not in ALLOWED_IMAGE_FORMATS:
        raise UploadValidationError("仅支持 JPG、PNG、WEBP、BMP、AVIF 图片", 415)
    return detected_format


def _prepare_thumbnail_image(source_image):
    image = ImageOps.exif_transpose(source_image)
    has_alpha = "A" in image.getbands() or (
        image.mode == "P" and "transparency" in image.info
    )
    if has_alpha:
        alpha_image = image.convert("RGBA")
        background = Image.new("RGB", alpha_image.size, (255, 255, 255))
        background.paste(alpha_image, mask=alpha_image.getchannel("A"))
        return background
    if image.mode not in {"RGB", "L"}:
        return image.convert("RGB")
    if image.mode == "L":
        return image.convert("RGB")
    return image


def _build_thumbnail_path(trace_id):
    return UPLOADS_DIR / f"{trace_id}.jpg"


def _build_source_upload_path(trace_id, detected_format):
    return UPLOADS_DIR / f"{trace_id}_source{ALLOWED_IMAGE_FORMATS[detected_format]}"


def _create_thumbnail(source_path, trace_id):
    try:
        with Image.open(source_path) as source_image:
            image = _prepare_thumbnail_image(source_image)
            image.thumbnail((THUMBNAIL_MAX_EDGE, THUMBNAIL_MAX_EDGE), RESAMPLING_LANCZOS)
            jpeg_path = _build_thumbnail_path(trace_id)
            image.save(
                jpeg_path,
                "JPEG",
                quality=THUMBNAIL_QUALITY,
                optimize=True,
            )
            return jpeg_path
    except UploadValidationError:
        raise
    except Exception as exc:
        logger.exception("Failed to create thumbnail trace_id=%s", trace_id)
        raise UploadValidationError("生成缩略图失败，请重试", 500) from exc


async def _store_upload_file(upload_file: UploadFile, trace_id: str):
    content_type = (upload_file.content_type or "").lower().strip()
    if content_type in DISALLOWED_CONTENT_TYPES:
        raise UploadValidationError("仅支持 JPG、PNG、WEBP、BMP、AVIF 图片", 415)

    temp_path = UPLOADS_DIR / f"{trace_id}.upload"
    total_size = 0
    try:
        with temp_path.open("wb") as buffer:
            while True:
                chunk = await upload_file.read(CHUNK_SIZE)
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > MAX_UPLOAD_SIZE_BYTES:
                    raise UploadValidationError(
                        f"上传图片不能超过 {MAX_UPLOAD_SIZE_MB}MB",
                        413,
                    )
                buffer.write(chunk)

        if total_size == 0:
            raise UploadValidationError("上传文件不能为空", 400)

        detected_format = _detect_image_format(temp_path)
        final_path = _build_source_upload_path(trace_id, detected_format)
        temp_path.replace(final_path)
        return final_path
    except UploadValidationError:
        _delete_file(temp_path)
        raise
    except Exception as exc:
        _delete_file(temp_path)
        logger.exception("Failed to store uploaded file trace_id=%s", trace_id)
        raise UploadValidationError("上传图片失败，请重试", 500) from exc
    finally:
        await upload_file.close()


CORS_ORIGINS = _load_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=CORS_ORIGINS != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")


class AlternativeRequest(BaseModel):
    analysis_result: dict
    user_context: dict


class HistoryAdviceRequest(BaseModel):
    question: str = ""
    window_days: int = DEFAULT_HISTORY_ADVICE_WINDOW_DAYS
    client_context: dict = Field(default_factory=dict)
    user_context: dict = Field(default_factory=dict)
    weekly_stats: list[dict] = Field(default_factory=list)
    recent_entries: list[dict] = Field(default_factory=list)


class UserInitRequest(BaseModel):
    user_id: str = ""


class AddFriendRequest(BaseModel):
    friend_code: Optional[str] = None
    target_user_id: Optional[str] = None


class DietRecordRequest(BaseModel):
    main_name: str
    total_calories: int
    total_traffic_light: str
    summary: str
    warning_message: str = ""
    nutrition_totals: dict = Field(default_factory=dict)
    nutrition_tags: list[str] = Field(default_factory=list)
    image_url: str = ""
    image_expires_at: str = ""


@app.get("/")
async def root():
    return {"message": "LifeLens API is running"}


@app.get("/api/v1/health")
async def health():
    return {
        "status": "ok",
        "service": "lifelens-api",
        "max_upload_size_mb": MAX_UPLOAD_SIZE_MB,
        "thumbnail_retention_days": THUMBNAIL_RETENTION_DAYS,
        "thumbnail_max_edge": THUMBNAIL_MAX_EDGE,
        "thumbnail_quality": THUMBNAIL_QUALITY,
        "upload_storage_limit_mb": UPLOAD_STORAGE_LIMIT_MB,
    }


@app.post("/api/v1/user/init")
async def init_user(request: UserInitRequest):
    trace_id = str(uuid.uuid4())
    try:
        payload = get_or_create_user(request.user_id)
        return JSONResponse(status_code=200, content={"code": 200, "data": payload})
    except ValueError as exc:
        return _error_response(str(exc), status_code=400, trace_id=trace_id)
    except Exception:
        logger.exception("Unexpected error during user initialization trace_id=%s", trace_id)
        return _error_response("初始化用户失败，请稍后重试", 500, trace_id)


@app.post("/api/v1/friends/add")
async def add_friendship(
    request: AddFriendRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
):
    trace_id = str(uuid.uuid4())
    try:
        current_user_id = _require_user_id(x_user_id)
        payload = add_friend(
            current_user_id,
            friend_code=request.friend_code,
            target_user_id=request.target_user_id,
        )
        return JSONResponse(status_code=200, content={"code": 200, "data": payload})
    except UploadValidationError as exc:
        return _error_response(exc.message, status_code=exc.status_code, trace_id=trace_id)
    except LookupError as exc:
        return _error_response(str(exc), status_code=404, trace_id=trace_id)
    except ValueError as exc:
        return _error_response(str(exc), status_code=400, trace_id=trace_id)
    except Exception:
        logger.exception("Unexpected error during add_friend trace_id=%s", trace_id)
        return _error_response("添加好友失败，请稍后重试", 500, trace_id)


@app.get("/api/v1/friends/feed")
async def get_friend_feed(x_user_id: Optional[str] = Header(None, alias="X-User-Id")):
    trace_id = str(uuid.uuid4())
    try:
        current_user_id = _require_user_id(x_user_id)
        payload = get_today_friend_feed(current_user_id)
        return JSONResponse(status_code=200, content={"code": 200, "data": payload})
    except UploadValidationError as exc:
        return _error_response(exc.message, status_code=exc.status_code, trace_id=trace_id)
    except ValueError as exc:
        return _error_response(str(exc), status_code=400, trace_id=trace_id)
    except Exception:
        logger.exception("Unexpected error during get_friend_feed trace_id=%s", trace_id)
        return _error_response("获取好友动态失败，请稍后重试", 500, trace_id)


@app.post("/api/v1/diet-records")
async def create_diet_record(
    request: DietRecordRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
):
    trace_id = str(uuid.uuid4())
    try:
        current_user_id = _require_user_id(x_user_id)
        payload = save_diet_record(
            current_user_id,
            main_name=request.main_name,
            total_calories=request.total_calories,
            total_traffic_light=request.total_traffic_light,
            summary=request.summary,
            warning_message=request.warning_message,
            nutrition_totals=request.nutrition_totals,
            nutrition_tags=request.nutrition_tags,
            image_url=request.image_url,
            image_expires_at=request.image_expires_at,
        )
        return JSONResponse(status_code=200, content={"code": 200, "data": payload})
    except UploadValidationError as exc:
        return _error_response(exc.message, status_code=exc.status_code, trace_id=trace_id)
    except ValueError as exc:
        return _error_response(str(exc), status_code=400, trace_id=trace_id)
    except Exception:
        logger.exception("Unexpected error during create_diet_record trace_id=%s", trace_id)
        return _error_response("保存饮食记录失败，请稍后重试", 500, trace_id)


@app.post("/api/v1/vision/analyze")
async def analyze_vision(file: UploadFile = File(...), user_context: str = Form(...)):
    trace_id = str(uuid.uuid4())
    source_file_path = None
    thumbnail_path = None

    try:
        parsed_user_context = _parse_user_context(user_context)
        source_file_path = await _store_upload_file(file, trace_id)
        analysis_result = await analyze_food_image(str(source_file_path), parsed_user_context)
        thumbnail_path = _create_thumbnail(source_file_path, trace_id)
        _delete_file(source_file_path)
        source_file_path = None

        # Keep the latest thumbnail available even if the directory is already over quota.
        enforce_storage_limit(
            str(UPLOADS_DIR),
            UPLOAD_STORAGE_LIMIT_BYTES,
            protected_paths=[str(thumbnail_path)],
        )

        normalized_result = _normalize_analysis_result(
            analysis_result, parsed_user_context
        )
        normalized_result["image_url"] = f"/uploads/{thumbnail_path.name}"
        normalized_result["image_expires_at"] = _build_image_expiration()
        return JSONResponse(
            status_code=200,
            content={
                "code": 200,
                "data": normalized_result,
                "trace_id": trace_id,
            },
        )
    except UploadValidationError as exc:
        _delete_file(source_file_path)
        _delete_file(thumbnail_path)
        return _error_response(exc.message, status_code=exc.status_code, trace_id=trace_id)
    except VisionServiceError as exc:
        _delete_file(source_file_path)
        _delete_file(thumbnail_path)
        return _error_response(str(exc), status_code=502, trace_id=trace_id)
    except ValueError:
        logger.exception("Invalid analysis response format trace_id=%s", trace_id)
        _delete_file(source_file_path)
        _delete_file(thumbnail_path)
        return _error_response("图像分析结果格式异常，请稍后重试", 502, trace_id)
    except Exception:
        logger.exception("Unexpected error during image analysis trace_id=%s", trace_id)
        _delete_file(source_file_path)
        _delete_file(thumbnail_path)
        return _error_response("服务器内部错误，请稍后重试", 500, trace_id)


@app.post("/api/v1/vision/generate-alternatives")
async def generate_alternatives(request: AlternativeRequest):
    trace_id = str(uuid.uuid4())
    try:
        result = await generate_alternative_suggestions(
            request.analysis_result,
            request.user_context,
        )
        normalized_result = _normalize_alternatives_result(result)
        return JSONResponse(status_code=200, content={"code": 200, "data": normalized_result})
    except VisionServiceError as exc:
        return _error_response(str(exc), status_code=502, trace_id=trace_id)
    except ValueError:
        logger.exception("Invalid alternatives response format trace_id=%s", trace_id)
        return _error_response("爆改建议结果格式异常，请稍后重试", 502, trace_id)
    except Exception:
        logger.exception("Unexpected error during alternatives generation trace_id=%s", trace_id)
        return _error_response("服务器内部错误，请稍后重试", 500, trace_id)


@app.post("/api/v1/vision/history-advice")
async def history_advice(request: HistoryAdviceRequest):
    trace_id = str(uuid.uuid4())
    try:
        if not request.recent_entries:
            return _error_response("暂无可用饮食记录，先记录几餐再来询问 AI 吧", 400, trace_id)

        normalized_user_context = _normalize_user_context_dict(request.user_context)
        normalized_question = _normalize_history_advice_question(request.question)
        result = await generate_history_advice(
            normalized_question,
            request.weekly_stats,
            request.recent_entries,
            normalized_user_context,
            request.client_context,
        )
        normalized_result = _normalize_history_advice_result(result)
        return JSONResponse(status_code=200, content={"code": 200, "data": normalized_result})
    except UploadValidationError as exc:
        return _error_response(exc.message, status_code=exc.status_code, trace_id=trace_id)
    except VisionServiceError as exc:
        return _error_response(str(exc), status_code=502, trace_id=trace_id)
    except ValueError:
        logger.exception("Invalid history advice response format trace_id=%s", trace_id)
        return _error_response("历史建议结果格式异常，请稍后重试", 502, trace_id)
    except Exception:
        logger.exception("Unexpected error during history advice trace_id=%s", trace_id)
        return _error_response("服务器内部错误，请稍后重试", 500, trace_id)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)

