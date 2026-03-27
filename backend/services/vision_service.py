import base64
import json
import logging
import mimetypes
import os
import re
import tempfile
import time
from pathlib import Path

from PIL import Image, ImageOps
import pillow_avif
from dotenv import load_dotenv
from openai import AsyncOpenAI, BadRequestError

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(BACKEND_DIR / ".env", override=True)

logger = logging.getLogger(__name__)

# Prefer DashScope settings for Qwen models, while still keeping Ark settings
# available for any future Doubao fallback.
DEFAULT_DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_ARK_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
DEFAULT_MODEL_NAME = "qwen3.5-flash"
DEFAULT_IMAGE_TIMEOUT_SEC = 90.0
DEFAULT_TEXT_TIMEOUT_SEC = 60.0
DEFAULT_MODEL_IMAGE_MAX_EDGE = 1024
INFERENCE_IMAGE_QUALITY = 86
MAX_ANALYSIS_ITEMS = 4
MAX_RECENT_ENTRIES_FOR_PROMPT = 10
MAX_WEEKLY_DAYS_FOR_PROMPT = 7
LANCZOS_RESAMPLE = getattr(getattr(Image, "Resampling", Image), "LANCZOS")

VISION_MODEL_NAME = os.getenv("VISION_MODEL", DEFAULT_MODEL_NAME)
TEXT_MODEL_NAME = os.getenv("TEXT_MODEL", DEFAULT_MODEL_NAME)


class VisionServiceError(Exception):
    """Safe error surfaced to API clients."""


_RESPONSE_FORMAT_SUPPORT = {}
_ASYNC_CLIENTS = {}

ALLOWED_RISK_CODES = (
    "high_calorie",
    "high_sugar",
    "high_sodium",
    "high_fat",
    "high_saturated_fat",
    "low_protein",
    "low_fiber",
    "allergen_risk",
    "gluten_risk",
    "lactose_risk",
)

ANALYSIS_JSON_TEMPLATE = {
    "main_name": "整餐名称",
    "nutrition_totals": {
        "calories_kcal": 0,
        "protein_g": 0,
        "fat_g": 0,
        "carb_g": 0,
        "fiber_g": 0,
        "sugar_g": 0,
        "sodium_mg": 0,
    },
    "nutrition_tags": ["标签1", "标签2"],
    "risk_flags": [
        {"code": "high_sugar", "severity": "medium", "reason": "原因"}
    ],
    "thought_process": "先说明考虑的健康条件，再简述判断依据",
    "items": [
        {
            "name": "食物名称",
            "ingredient_evidence": "视觉证据",
            "nutrition": {
                "calories_kcal": 0,
                "protein_g": 0,
                "fat_g": 0,
                "carb_g": 0,
                "fiber_g": 0,
                "sugar_g": 0,
                "sodium_mg": 0,
            },
            "nutrition_tags": ["标签1"],
            "risk_flags": [
                {"code": "low_protein", "severity": "low", "reason": "原因"}
            ],
        }
    ],
    "total_analysis": {
        "summary": "整餐总结",
        "suggestion": "简短建议",
        "confidence": 0.9,
    },
}

ALTERNATIVES_JSON_SCHEMA = {
    "name": "meal_alternatives",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "ordering_hint": {"type": "string"},
            "cooking_hint": {"type": "string"},
        },
        "required": ["ordering_hint", "cooking_hint"],
    },
}

HISTORY_ADVICE_JSON_SCHEMA = {
    "name": "history_advice",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "answer": {"type": "string"},
            "observations": {
                "type": "array",
                "items": {"type": "string"},
                "maxItems": 3,
            },
            "suggestions": {
                "type": "array",
                "items": {"type": "string"},
                "maxItems": 3,
            },
            "focus_tags": {
                "type": "array",
                "items": {"type": "string"},
                "maxItems": 4,
            },
        },
        "required": ["answer", "observations", "suggestions", "focus_tags"],
    },
}


def _get_env_float(name, default):
    raw = str(os.getenv(name, "")).strip()
    if not raw:
        return float(default)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return float(default)
    return value if value > 0 else float(default)


def _get_env_int(name, default):
    raw = str(os.getenv(name, "")).strip()
    if not raw:
        return int(default)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return int(default)
    return value if value > 0 else int(default)


MODEL_TIMEOUT_IMAGE_SEC = _get_env_float(
    "MODEL_TIMEOUT_IMAGE_SEC", DEFAULT_IMAGE_TIMEOUT_SEC
)
MODEL_TIMEOUT_TEXT_SEC = _get_env_float(
    "MODEL_TIMEOUT_TEXT_SEC", DEFAULT_TEXT_TIMEOUT_SEC
)
MODEL_IMAGE_MAX_EDGE = _get_env_int(
    "MODEL_IMAGE_MAX_EDGE", DEFAULT_MODEL_IMAGE_MAX_EDGE
)


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def _infer_provider(model_name):
    normalized = str(model_name or "").strip().lower()
    if normalized.startswith("doubao"):
        return "ark"
    return "dashscope"


def _resolve_runtime_settings(model_name):
    provider = _infer_provider(model_name)
    if provider == "ark":
        api_key = os.getenv("ARK_API_KEY", "").strip()
        base_url = os.getenv("ARK_BASE_URL", "").strip() or DEFAULT_ARK_BASE_URL
        return provider, api_key, base_url

    api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    base_url = (
        os.getenv("DASHSCOPE_BASE_URL", "").strip() or DEFAULT_DASHSCOPE_BASE_URL
    )
    return provider, api_key, base_url


def _get_async_client(model_name):
    provider, api_key, base_url = _resolve_runtime_settings(model_name)
    cache_key = (provider, base_url, api_key)
    client = _ASYNC_CLIENTS.get(cache_key)
    if client is not None:
        return client

    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
        max_retries=0,
    )
    _ASYNC_CLIENTS[cache_key] = client
    return client


def _ensure_api_key_configured(model_name):
    provider, api_key, _ = _resolve_runtime_settings(model_name)
    if api_key:
        return
    expected_key = "ARK_API_KEY" if provider == "ark" else "DASHSCOPE_API_KEY"
    logger.error("Missing %s for model %s", expected_key, model_name)
    raise VisionServiceError("图像分析服务暂时不可用，请稍后重试")


def _get_model_request_kwargs(model_name):
    normalized = str(model_name or "").strip().lower()
    if normalized.startswith("qwen"):
        return {"extra_body": {"enable_thinking": False}}
    return {}


def _extract_content_text(content):
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        chunks = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if text:
                    chunks.append(str(text))
                continue

            text = getattr(item, "text", None)
            if text:
                chunks.append(str(text))
                continue

            chunks.append(str(item))

        return "".join(chunks).strip()

    return str(content or "").strip()


def _parse_json_content(content):
    text = _extract_content_text(content)
    if not text:
        raise ValueError("Empty model response")

    try:
        return json.loads(text), text
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        for index, char in enumerate(text):
            if char not in "{[":
                continue
            try:
                parsed, _ = decoder.raw_decode(text[index:])
                return parsed, text
            except json.JSONDecodeError:
                continue

    preview = re.sub(r"\s+", " ", text)[:200]
    raise ValueError(f"Could not parse model JSON response: {preview}")


def _response_format_mode(response_format):
    if not isinstance(response_format, dict):
        return "plain"
    return str(response_format.get("type") or "plain").strip().lower() or "plain"


def _build_json_schema_response_format(schema_config):
    return {
        "type": "json_schema",
        "json_schema": {
            "name": schema_config["name"],
            "schema": schema_config["schema"],
            "strict": True,
        },
    }


def _is_unsupported_response_format(exc, response_format):
    mode = _response_format_mode(response_format)
    message = str(exc or "").lower()
    if "response_format.type" in message and mode in message:
        return "not supported" in message or "not valid" in message
    if mode == "json_schema" and "response_format" in message and "schema" in message:
        return "not supported" in message or "not valid" in message
    return False


def _truncate_text(value, max_length):
    text = str(value or "").strip()
    if not text or len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip() + "…"


def _clean_number(value, digits=1):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0
    rounded = round(number, digits)
    if abs(rounded - round(rounded)) < 1e-9:
        return int(round(rounded))
    return rounded


def _compact_nutrition_for_prompt(nutrition_totals):
    if not isinstance(nutrition_totals, dict):
        return {}

    compact = {}
    key_map = {
        "calories_kcal": "kcal",
        "protein_g": "p",
        "fat_g": "f",
        "carb_g": "c",
        "fiber_g": "fiber",
        "sugar_g": "sugar",
        "sodium_mg": "sodium",
    }
    for source_key, target_key in key_map.items():
        value = _clean_number(nutrition_totals.get(source_key))
        if value:
            compact[target_key] = value
    return compact


def _compact_history_advice_context(weekly_stats, recent_entries, user_context, client_context=None):
    compact_user_context = {
        "goal": str((user_context or {}).get("goal") or "").strip(),
        "health_conditions": [
            str(item).strip()
            for item in (user_context or {}).get("health_conditions", [])
            if str(item).strip()
        ],
    }
    for key in ("age", "gender", "height", "weight", "activity_level"):
        value = (user_context or {}).get(key)
        if value not in (None, "", []):
            compact_user_context[key] = value

    compact_weekly_stats = []
    for day in list(weekly_stats or [])[-MAX_WEEKLY_DAYS_FOR_PROMPT:]:
        if not isinstance(day, dict):
            continue
        compact_weekly_stats.append(
            {
                "date": str(day.get("fullDate") or day.get("label") or "").strip(),
                "kcal": _clean_number(day.get("calories")),
                "p": _clean_number(day.get("protein")),
                "f": _clean_number(day.get("fat")),
                "c": _clean_number(day.get("carb")),
            }
        )

    averages = {}
    if compact_weekly_stats:
        metric_keys = ("kcal", "p", "f", "c")
        for key in metric_keys:
            values = [item[key] for item in compact_weekly_stats if item[key]]
            if values:
                averages[key] = _clean_number(sum(values) / len(values))

    def _sort_key(entry):
        return str((entry or {}).get("timestamp") or "")

    compact_recent_entries = []
    for entry in sorted(recent_entries or [], key=_sort_key, reverse=True)[
        :MAX_RECENT_ENTRIES_FOR_PROMPT
    ]:
        if not isinstance(entry, dict):
            continue
        compact_entry = {
            "time": str(entry.get("timestamp") or "").strip(),
            "meal": str(entry.get("main_name") or "").strip(),
            "light": str(entry.get("total_traffic_light") or "").strip(),
        }
        local_date = str(entry.get("local_date") or "").strip()
        if local_date:
            compact_entry["local_date"] = local_date

        warning_message = _truncate_text(entry.get("warning_message"), 48)
        if warning_message:
            compact_entry["warning"] = warning_message

        summary = _truncate_text(entry.get("summary"), 48)
        if summary:
            compact_entry["summary"] = summary

        tags = [
            str(tag).strip()
            for tag in entry.get("nutrition_tags", [])[:3]
            if str(tag).strip()
        ]
        if tags:
            compact_entry["tags"] = tags

        macros = _compact_nutrition_for_prompt(entry.get("nutrition_totals"))
        if macros:
            compact_entry["nutrition"] = macros

        compact_recent_entries.append(compact_entry)

    compact_context = {
        "profile": compact_user_context,
        "weekly": compact_weekly_stats,
        "weekly_avg": averages,
        "recent_meals": compact_recent_entries,
    }
    reference_today = str((client_context or {}).get("today") or "").strip()
    if reference_today:
        compact_context["reference_today"] = reference_today
    return compact_context


def _guess_mime_type(image_path):
    ext = os.path.splitext(image_path)[1].lower()
    mime_type, _ = mimetypes.guess_type(image_path)
    if mime_type:
        return mime_type
    mime_map = {
        ".webp": "image/webp",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
        ".avif": "image/avif",
    }
    return mime_map.get(ext, "image/jpeg")


def _prepare_inference_image(image_path):
    original_mime = _guess_mime_type(image_path)
    original_bytes = os.path.getsize(image_path)
    with Image.open(image_path) as source_image:
        image = ImageOps.exif_transpose(source_image)
        original_size = image.size
        rgb_image = image.convert("RGB")
        if max(rgb_image.size) > MODEL_IMAGE_MAX_EDGE:
            rgb_image.thumbnail(
                (MODEL_IMAGE_MAX_EDGE, MODEL_IMAGE_MAX_EDGE),
                LANCZOS_RESAMPLE,
            )
        prepared_size = rgb_image.size
        temp_file = tempfile.NamedTemporaryFile(
            prefix="lifelens_infer_",
            suffix=".jpg",
            delete=False,
        )
        prepared_path = temp_file.name
        temp_file.close()
        rgb_image.save(
            prepared_path,
            format="JPEG",
            quality=INFERENCE_IMAGE_QUALITY,
            optimize=True,
        )

    prepared_bytes = os.path.getsize(prepared_path)
    return prepared_path, {
        "original_mime": original_mime,
        "original_size": list(original_size),
        "prepared_size": list(prepared_size),
        "original_bytes": original_bytes,
        "prepared_bytes": prepared_bytes,
    }


def _log_model_call(event, model_name, elapsed_seconds, **details):
    provider, _, _ = _resolve_runtime_settings(model_name)
    payload = {
        "event": event,
        "model": model_name,
        "provider": provider,
        "qwen_optimized": bool(_get_model_request_kwargs(model_name)),
        "elapsed_ms": round(float(elapsed_seconds) * 1000, 1),
    }
    for key, value in details.items():
        if value in (None, "", [], {}):
            continue
        payload[key] = value
    logger.info("model_call %s", json.dumps(payload, ensure_ascii=False, sort_keys=True))


async def _create_json_completion(
    model,
    messages,
    timeout,
    response_formats=None,
):
    client = _get_async_client(model)
    request_kwargs = {
        "model": model,
        "messages": messages,
        "timeout": timeout,
        **_get_model_request_kwargs(model),
    }

    attempted_modes = []
    fallback_used = False
    for response_format in response_formats or []:
        mode = _response_format_mode(response_format)
        attempted_modes.append(mode)
        cache_key = (model, mode)
        if _RESPONSE_FORMAT_SUPPORT.get(cache_key) is False:
            fallback_used = True
            continue

        try:
            response = await client.chat.completions.create(
                response_format=response_format,
                **request_kwargs,
            )
            _RESPONSE_FORMAT_SUPPORT[cache_key] = True
            parsed, text = _parse_json_content(response.choices[0].message.content)
            return parsed, {
                "response_format_mode": mode,
                "response_format_fallback": fallback_used,
                "attempted_modes": attempted_modes,
                "output_length": len(text),
            }
        except BadRequestError as exc:
            if not _is_unsupported_response_format(exc, response_format):
                raise
            _RESPONSE_FORMAT_SUPPORT[cache_key] = False
            fallback_used = True
            logger.info(
                "Model %s does not support response_format=%s; retrying with fallback",
                model,
                mode,
            )

    response = await client.chat.completions.create(**request_kwargs)
    parsed, text = _parse_json_content(response.choices[0].message.content)
    return parsed, {
        "response_format_mode": "plain",
        "response_format_fallback": fallback_used,
        "attempted_modes": attempted_modes,
        "output_length": len(text),
    }


def _build_analysis_messages(user_context):
    compact_profile = {
        "age": user_context.get("age"),
        "gender": user_context.get("gender"),
        "height_cm": user_context.get("height"),
        "weight_kg": user_context.get("weight"),
        "activity_level": user_context.get("activity_level"),
        "goal": user_context.get("goal"),
        "health_conditions": user_context.get("health_conditions", []),
    }
    risk_code_text = "、".join(ALLOWED_RISK_CODES)
    return [
        {
            "role": "system",
            "content": (
                "你是严谨的营养师和食物识别助手。"
                "只能输出严格 JSON，所有说明文字用简体中文，JSON key 保持英文。"
            ),
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "请分析整餐并给出多维营养估算。\n"
                        f"用户画像: {json.dumps(compact_profile, ensure_ascii=False)}\n"
                        f"要求: items 最多 {MAX_ANALYSIS_ITEMS} 项；数值字段只写数字；"
                        "nutrition_totals 表示整餐总量；ingredient_evidence 不超过18字；"
                        "thought_process 用1到2句，先写已考虑的健康条件再简述依据；"
                        "summary 和 suggestion 各不超过36字；confidence 取 0 到 1。\n"
                        f"risk_flags.code 只能使用: {risk_code_text}；"
                        "severity 只能是 low、medium、high。\n"
                        "若用户有糖尿病/高血压/高胆固醇/过敏/无麸质/乳糖不耐，请特别检查相关风险。\n"
                        "返回结构:\n"
                        f"{json.dumps(ANALYSIS_JSON_TEMPLATE, ensure_ascii=False)}"
                    ),
                }
            ],
        },
    ]


def _build_alternatives_messages(analysis_result, user_context):
    compact_context = {
        "food_name": analysis_result.get("main_name"),
        "traffic_light": analysis_result.get("total_traffic_light"),
        "warning_message": _truncate_text(analysis_result.get("warning_message"), 48),
        "nutrition_totals": _compact_nutrition_for_prompt(
            analysis_result.get("nutrition_totals")
        ),
        "nutrition_tags": [
            str(tag).strip()
            for tag in analysis_result.get("nutrition_tags", [])[:4]
            if str(tag).strip()
        ],
        "risk_flags": [
            {
                "code": str(flag.get("code") or "").strip(),
                "severity": str(flag.get("severity") or "").strip(),
                "reason": _truncate_text(flag.get("reason"), 28),
            }
            for flag in analysis_result.get("risk_flags", [])[:4]
            if isinstance(flag, dict)
        ],
        "goal": user_context.get("goal"),
        "health_conditions": user_context.get("health_conditions", []),
    }
    return [
        {
            "role": "system",
            "content": (
                "你是营养师。只基于提供的结构化上下文给出简洁可执行建议，"
                "必须返回严格 JSON，不要输出 markdown。"
            ),
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "请针对当前黄灯或红灯餐食，输出两条 AI 爆改建议。\n"
                        f"上下文: {json.dumps(compact_context, ensure_ascii=False)}\n"
                        "要求: ordering_hint 优先解决最关键风险；"
                        "cooking_hint 说明在家如何减少问题营养素；"
                        "两句都要简短、具体、适合执行，最好控制在32字内。"
                    ),
                }
            ],
        },
    ]


def _build_history_advice_messages(
    question, weekly_stats, recent_entries, user_context, client_context=None
):
    compact_context = _compact_history_advice_context(
        weekly_stats, recent_entries, user_context, client_context
    )
    return [
        {
            "role": "system",
            "content": (
                "你是营养师和饮食教练。只根据提供的饮食记录和用户资料回答。"
                "如果用户问今天、今天这顿或某一餐，优先参考 reference_today 与对应的 local_date/time；"
                "如果用户问最近趋势，再结合 weekly 和 recent_meals。"
                "如果记录不足以支持结论，要明确说明，不要硬猜。"
                "不要提图片，不要编造不存在的数据，必须返回严格 JSON。"
            ),
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"用户问题: {question}\n"
                        f"上下文: {json.dumps(compact_context, ensure_ascii=False)}\n"
                        "要求: answer 直接回答问题；observations 和 suggestions 各最多3条短句；"
                        "focus_tags 最多4个短标签，例如“蛋白偏低”“晚餐偏重”。"
                    ),
                }
            ],
        },
    ]


async def analyze_food_image(image_path, user_context):
    start_time = time.time()
    prepared_path = None
    image_meta = {}
    try:
        _ensure_api_key_configured(VISION_MODEL_NAME)
        prepared_path, image_meta = _prepare_inference_image(image_path)
        base64_image = encode_image(prepared_path)

        messages = _build_analysis_messages(user_context)
        messages[1]["content"].append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
            }
        )

        result, completion_meta = await _create_json_completion(
            model=VISION_MODEL_NAME,
            messages=messages,
            timeout=MODEL_TIMEOUT_IMAGE_SEC,
            response_formats=[{"type": "json_object"}],
        )

        _log_model_call(
            "analyze_food_image",
            VISION_MODEL_NAME,
            time.time() - start_time,
            timeout_sec=MODEL_TIMEOUT_IMAGE_SEC,
            image=image_meta,
            output_length=completion_meta.get("output_length"),
            response_format_mode=completion_meta.get("response_format_mode"),
            response_format_fallback=completion_meta.get("response_format_fallback"),
        )
        return result
    except VisionServiceError:
        raise
    except Exception:
        _log_model_call(
            "analyze_food_image_error",
            VISION_MODEL_NAME,
            time.time() - start_time,
            timeout_sec=MODEL_TIMEOUT_IMAGE_SEC,
            image=image_meta,
        )
        logger.exception("Error in analyze_food_image")
        raise VisionServiceError("图像分析服务暂时不可用，请稍后重试")
    finally:
        if prepared_path and os.path.exists(prepared_path):
            try:
                os.remove(prepared_path)
            except Exception:
                logger.exception("Error cleaning up inference image %s", prepared_path)


async def generate_alternative_suggestions(analysis_result, user_context):
    start_time = time.time()
    try:
        _ensure_api_key_configured(TEXT_MODEL_NAME)
        food_name = analysis_result.get("main_name", "未知食物")
        messages = _build_alternatives_messages(analysis_result, user_context)

        result, completion_meta = await _create_json_completion(
            model=TEXT_MODEL_NAME,
            messages=messages,
            timeout=MODEL_TIMEOUT_TEXT_SEC,
            response_formats=[
                _build_json_schema_response_format(ALTERNATIVES_JSON_SCHEMA),
                {"type": "json_object"},
            ],
        )

        _log_model_call(
            "generate_alternative_suggestions",
            TEXT_MODEL_NAME,
            time.time() - start_time,
            timeout_sec=MODEL_TIMEOUT_TEXT_SEC,
            food_name=food_name,
            risk_flag_count=len(analysis_result.get("risk_flags") or []),
            output_length=completion_meta.get("output_length"),
            response_format_mode=completion_meta.get("response_format_mode"),
            response_format_fallback=completion_meta.get("response_format_fallback"),
        )
        return result
    except VisionServiceError:
        raise
    except Exception:
        _log_model_call(
            "generate_alternative_suggestions_error",
            TEXT_MODEL_NAME,
            time.time() - start_time,
            timeout_sec=MODEL_TIMEOUT_TEXT_SEC,
            food_name=analysis_result.get("main_name", "未知食物"),
        )
        logger.exception("Error in generate_alternative_suggestions")
        raise VisionServiceError("爆改建议服务暂时不可用，请稍后重试")


async def generate_history_advice(
    question, weekly_stats, recent_entries, user_context, client_context=None
):
    start_time = time.time()
    compact_context = _compact_history_advice_context(
        weekly_stats, recent_entries, user_context, client_context
    )
    try:
        _ensure_api_key_configured(TEXT_MODEL_NAME)
        messages = _build_history_advice_messages(
            question, weekly_stats, recent_entries, user_context, client_context
        )
        result, completion_meta = await _create_json_completion(
            model=TEXT_MODEL_NAME,
            messages=messages,
            timeout=MODEL_TIMEOUT_TEXT_SEC,
            response_formats=[
                _build_json_schema_response_format(HISTORY_ADVICE_JSON_SCHEMA),
                {"type": "json_object"},
            ],
        )

        _log_model_call(
            "generate_history_advice",
            TEXT_MODEL_NAME,
            time.time() - start_time,
            timeout_sec=MODEL_TIMEOUT_TEXT_SEC,
            weekly_days=len(compact_context.get("weekly", [])),
            recent_meal_count=len(compact_context.get("recent_meals", [])),
            output_length=completion_meta.get("output_length"),
            response_format_mode=completion_meta.get("response_format_mode"),
            response_format_fallback=completion_meta.get("response_format_fallback"),
        )
        return result
    except VisionServiceError:
        raise
    except Exception:
        _log_model_call(
            "generate_history_advice_error",
            TEXT_MODEL_NAME,
            time.time() - start_time,
            timeout_sec=MODEL_TIMEOUT_TEXT_SEC,
            weekly_days=len(compact_context.get("weekly", [])),
            recent_meal_count=len(compact_context.get("recent_meals", [])),
        )
        logger.exception("Error in generate_history_advice")
        raise VisionServiceError("历史建议服务暂时不可用，请稍后重试")
