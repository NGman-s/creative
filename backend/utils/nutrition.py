from __future__ import annotations

import json
from typing import Iterable

NUTRITION_FIELD_SPECS = {
    "calories_kcal": {"precision": 0, "default": 0},
    "protein_g": {"precision": 1, "default": 0.0},
    "fat_g": {"precision": 1, "default": 0.0},
    "carb_g": {"precision": 1, "default": 0.0},
    "fiber_g": {"precision": 1, "default": 0.0},
    "sugar_g": {"precision": 1, "default": 0.0},
    "sodium_mg": {"precision": 0, "default": 0},
}

NUTRITION_FIELDS = tuple(NUTRITION_FIELD_SPECS.keys())

NUTRITION_TAG_ALIASES = {
    "high_protein": "高蛋白",
    "protein_rich": "高蛋白",
    "rich_in_protein": "高蛋白",
    "high_fiber": "高纤维",
    "fiber_rich": "高纤维",
    "rich_in_fiber": "高纤维",
    "low_fat": "低脂",
    "low_calorie": "低热量",
    "high_calorie": "高热量",
    "high_sugar": "高糖",
    "low_sugar": "低糖",
    "high_sodium": "高钠",
    "low_sodium": "低钠",
    "low_protein": "低蛋白",
    "low_fiber": "低纤维",
    "high_carb": "高碳水",
    "low_carb": "低碳水",
    "balanced": "营养均衡",
    "balanced_meal": "营养均衡",
    "balanced_diet": "营养均衡",
    "balanced_nutrition": "营养均衡",
    "light_meal": "清淡",
}

NUTRITION_TAG_NUTRIENTS = {
    "protein": "蛋白",
    "fiber": "纤维",
    "fat": "脂",
    "saturated_fat": "饱和脂肪",
    "sugar": "糖",
    "sodium": "钠",
    "calorie": "热量",
    "calories": "热量",
    "carb": "碳水",
    "carbs": "碳水",
    "carbohydrate": "碳水",
    "carbohydrates": "碳水",
    "cholesterol": "胆固醇",
}

RISK_CODE_ORDER = (
    "allergen_risk",
    "gluten_risk",
    "lactose_risk",
    "high_sugar",
    "high_sodium",
    "high_saturated_fat",
    "high_calorie",
    "high_fat",
    "low_protein",
    "low_fiber",
)

RISK_CODE_SET = set(RISK_CODE_ORDER)
RISK_SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3}


def safe_float(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_numeric_value(field_name: str, value) -> int | float:
    spec = NUTRITION_FIELD_SPECS[field_name]
    parsed = max(0.0, safe_float(value, 0.0))
    precision = spec["precision"]
    if precision == 0:
        return int(round(parsed))
    return round(parsed, precision)


def empty_nutrition_totals() -> dict:
    return {
        field_name: spec["default"]
        for field_name, spec in NUTRITION_FIELD_SPECS.items()
    }


def normalize_nutrition_totals(value=None, fallback_calories=None) -> dict:
    totals = empty_nutrition_totals()
    source = value if isinstance(value, dict) else {}

    for field_name in NUTRITION_FIELDS:
        if field_name in source:
            totals[field_name] = _normalize_numeric_value(field_name, source.get(field_name))

    if fallback_calories is not None and not totals["calories_kcal"]:
        totals["calories_kcal"] = _normalize_numeric_value(
            "calories_kcal", fallback_calories
        )

    return totals


def has_nutrition_data(totals) -> bool:
    if not isinstance(totals, dict):
        return False
    return any(safe_float(totals.get(field_name), 0.0) > 0 for field_name in NUTRITION_FIELDS)


def sum_nutrition_totals(items: Iterable[dict]) -> dict:
    summed = {field_name: 0.0 for field_name in NUTRITION_FIELDS}
    for item in items or []:
        if not isinstance(item, dict):
            continue
        nutrition = normalize_nutrition_totals(item.get("nutrition"))
        for field_name in NUTRITION_FIELDS:
            summed[field_name] += safe_float(nutrition.get(field_name), 0.0)

    return {
        field_name: _normalize_numeric_value(field_name, total)
        for field_name, total in summed.items()
    }


def _normalize_tag_key(tag) -> str:
    text = str(tag or "").strip().lower()
    if not text:
        return ""
    text = text.replace("-", " ").replace("/", " ")
    return "_".join(part for part in text.split() if part)


def _translate_nutrition_tag(tag) -> str:
    normalized_key = _normalize_tag_key(tag)
    if not normalized_key:
        return ""

    if normalized_key in NUTRITION_TAG_ALIASES:
        return NUTRITION_TAG_ALIASES[normalized_key]

    for prefix, zh_prefix in (("high_", "高"), ("low_", "低")):
        if not normalized_key.startswith(prefix):
            continue
        nutrient_key = normalized_key[len(prefix) :]
        nutrient_label = NUTRITION_TAG_NUTRIENTS.get(nutrient_key)
        if nutrient_label:
            return f"{zh_prefix}{nutrient_label}"

    if normalized_key.startswith("rich_in_"):
        nutrient_label = NUTRITION_TAG_NUTRIENTS.get(normalized_key[len("rich_in_") :])
        if nutrient_label:
            return f"高{nutrient_label}"

    if normalized_key.endswith("_rich"):
        nutrient_label = NUTRITION_TAG_NUTRIENTS.get(normalized_key[: -len("_rich")])
        if nutrient_label:
            return f"高{nutrient_label}"

    return str(tag or "").strip()


def normalize_nutrition_tags(value) -> list[str]:
    raw_items = []
    if isinstance(value, list):
        raw_items = value
    elif isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            raw_items = []
        else:
            try:
                parsed = json.loads(normalized)
                if isinstance(parsed, list):
                    raw_items = parsed
                else:
                    raw_items = [item.strip() for item in normalized.split(",")]
            except json.JSONDecodeError:
                raw_items = [item.strip() for item in normalized.split(",")]

    tags = []
    seen = set()
    for item in raw_items:
        tag = _translate_nutrition_tag(item)
        if not tag or tag in seen:
            continue
        seen.add(tag)
        tags.append(tag)
    return tags


def _normalize_risk_flag(flag) -> dict | None:
    if isinstance(flag, str):
        code = flag.strip()
        severity = "medium"
        reason = ""
    elif isinstance(flag, dict):
        code = str(flag.get("code") or "").strip()
        severity = str(flag.get("severity") or "medium").strip().lower()
        reason = str(flag.get("reason") or "").strip()
    else:
        return None

    if code not in RISK_CODE_SET:
        return None
    if severity not in RISK_SEVERITY_ORDER:
        severity = "medium"

    return {"code": code, "severity": severity, "reason": reason}


def normalize_risk_flags(flags) -> list[dict]:
    by_code: dict[str, dict] = {}
    if not isinstance(flags, list):
        return []

    for flag in flags:
        normalized = _normalize_risk_flag(flag)
        if not normalized:
            continue

        existing = by_code.get(normalized["code"])
        if not existing:
            by_code[normalized["code"]] = normalized
            continue

        if RISK_SEVERITY_ORDER[normalized["severity"]] >= RISK_SEVERITY_ORDER[existing["severity"]]:
            if not normalized["reason"] and existing["reason"]:
                normalized["reason"] = existing["reason"]
            by_code[normalized["code"]] = normalized

    return sort_risk_flags(by_code.values())


def merge_risk_flags(*groups) -> list[dict]:
    merged = []
    for group in groups:
        merged.extend(normalize_risk_flags(group))
    return normalize_risk_flags(merged)


def sort_risk_flags(flags: Iterable[dict]) -> list[dict]:
    return sorted(
        flags,
        key=lambda item: (
            -RISK_SEVERITY_ORDER.get(item.get("severity"), 0),
            RISK_CODE_ORDER.index(item.get("code"))
            if item.get("code") in RISK_CODE_SET
            else len(RISK_CODE_ORDER),
        ),
    )


def build_backend_risk_flags(totals) -> list[dict]:
    normalized = normalize_nutrition_totals(totals)
    flags = []

    calories = normalized["calories_kcal"]
    protein = normalized["protein_g"]
    fat = normalized["fat_g"]
    carb = normalized["carb_g"]
    fiber = normalized["fiber_g"]
    sugar = normalized["sugar_g"]
    sodium = normalized["sodium_mg"]

    if calories >= 650:
        severity = "high" if calories >= 850 else "medium"
        flags.append(
            {"code": "high_calorie", "severity": severity, "reason": "总热量偏高"}
        )
    if sugar >= 25:
        severity = "high" if sugar >= 35 else "medium"
        flags.append({"code": "high_sugar", "severity": severity, "reason": "糖含量偏高"})
    if sodium >= 800:
        severity = "high" if sodium >= 1200 else "medium"
        flags.append({"code": "high_sodium", "severity": severity, "reason": "钠含量偏高"})
    if fat >= 28:
        severity = "high" if fat >= 40 else "medium"
        flags.append({"code": "high_fat", "severity": severity, "reason": "脂肪含量偏高"})
    if calories >= 250 and protein < 15:
        flags.append({"code": "low_protein", "severity": "medium", "reason": "蛋白质偏低"})
    if carb >= 20 and fiber < 4:
        flags.append({"code": "low_fiber", "severity": "low", "reason": "膳食纤维偏低"})

    return normalize_risk_flags(flags)


def infer_nutrition_tags(totals, risk_flags=None) -> list[str]:
    normalized = normalize_nutrition_totals(totals)
    risk_codes = {flag["code"] for flag in normalize_risk_flags(risk_flags)}
    tags = []

    def add(tag: str) -> None:
        if tag not in tags:
            tags.append(tag)

    if normalized["protein_g"] >= 25:
        add("高蛋白")
    if normalized["fiber_g"] >= 8:
        add("高纤维")
    if normalized["fat_g"] <= 10 and normalized["calories_kcal"] <= 350:
        add("低脂")
    if "high_sugar" in risk_codes:
        add("高糖")
    if "high_sodium" in risk_codes:
        add("高钠")
    if "high_calorie" in risk_codes:
        add("高热量")
    if "low_protein" in risk_codes:
        add("低蛋白")
    if "low_fiber" in risk_codes:
        add("低纤维")

    return tags[:6]
