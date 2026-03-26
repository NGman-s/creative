import base64
import json
import logging
import mimetypes
import os
import time

from PIL import Image
import pillow_avif
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

logger = logging.getLogger(__name__)

# Configuration for Qwen-VL-Max (assuming OpenAI-compatible endpoint like DashScope)
# For DashScope:
# API_KEY: Your DashScope API Key
# BASE_URL: "https://dashscope.aliyuncs.com/compatible-mode/v1"
# MODEL: "qwen-vl-max"

async_client = AsyncOpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url=os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
)


class VisionServiceError(Exception):
    """Safe error surfaced to API clients."""


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def _ensure_api_key_configured():
    if os.getenv("DASHSCOPE_API_KEY"):
        return
    logger.error("DASHSCOPE_API_KEY is not configured")
    raise VisionServiceError("图像分析服务暂时不可用，请稍后重试")


async def analyze_food_image(image_path, user_context):
    converted_path = None
    try:
        _ensure_api_key_configured()

        ext = os.path.splitext(image_path)[1].lower()
        mime_type, _ = mimetypes.guess_type(image_path)
        if not mime_type:
            mime_map = {
                ".webp": "image/webp",
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".gif": "image/gif",
                ".bmp": "image/bmp",
                ".avif": "image/avif",
            }
            mime_type = mime_map.get(ext, "image/jpeg")

        if ext == ".avif" or mime_type == "image/avif":
            logger.info("Converting AVIF to JPEG: %s", image_path)
            try:
                img = Image.open(image_path)
                converted_path = image_path.rsplit(".", 1)[0] + "_converted.jpg"
                img.convert("RGB").save(converted_path, "JPEG", quality=95)
                image_path = converted_path
                mime_type = "image/jpeg"
                logger.info("Successfully converted AVIF to JPEG: %s", converted_path)
            except Exception:
                logger.exception("AVIF conversion failed for %s", image_path)

        base64_image = encode_image(image_path)
        logger.info("Analyzing image: %s, detected MIME: %s", image_path, mime_type)

        prompt = f"""
        Role: Professional Nutritionist and AI Vision Expert.
        Task: Analyze the provided food image and return a structured nutrition estimate for the whole meal based on the user's profile.

        IMPORTANT: All text content in the output (values for name, summary, suggestion, thought_process, tags, etc.) MUST be in Simplified Chinese (简体中文). Keep the JSON keys in English.
        IMPORTANT: Return STRICT JSON only. Do not wrap the JSON in markdown. Do not add any extra keys.

        User Profile:
        - Age: {user_context.get('age')}
        - Gender: {user_context.get('gender', 'Not specified')}
        - Height: {user_context.get('height', 'Not specified')} cm
        - Weight: {user_context.get('weight', 'Not specified')} kg
        - Activity Level: {user_context.get('activity_level', 'Not specified')}
        - Goal: {user_context.get('goal')}
        - Health Conditions: {', '.join(user_context.get('health_conditions', []))}

        Instructions:
        1. First, identify all food items in the image and estimate their portions accurately.
        2. Estimate nutrition values using numbers only. Do not add units inside numeric fields.
        3. MANDATORY SAFETY CHECK: Cross-reference identified ingredients with the user's health conditions.
           - Start your thought_process by explicitly listing the health conditions considered.
           - IF USER HAS ALLERGIES: flag any possible allergen or cross-contamination risk.
           - If user has Diabetes: be highly sensitive to sugar, sweet drinks, refined carbs, and high-GI foods.
           - If user has Hypertension: be highly sensitive to sodium, salty sauces, pickles, and processed meats.
           - If user has High Cholesterol: be sensitive to fried foods, fatty cuts, and high saturated fat sources.
           - If user has Gluten Free or Lactose Intolerant needs, flag suspicious ingredients.
        4. Allowed risk flag codes ONLY:
           - high_calorie
           - high_sugar
           - high_sodium
           - high_fat
           - high_saturated_fat
           - low_protein
           - low_fiber
           - allergen_risk
           - gluten_risk
           - lactose_risk
        5. Allowed severity values ONLY: low, medium, high.
        6. For each item, include a short ingredient_evidence in Chinese describing the visual basis or likely ingredients.
        7. 'nutrition_totals' should summarize the whole meal, but items must still contain their own nutrition for backend reconciliation.
        8. If uncertain, provide the most likely estimate and explain the uncertainty briefly in thought_process.

        Output Format (STRICT JSON):
        {{
            "main_name": "整餐名称",
            "nutrition_totals": {{
                "calories_kcal": 0,
                "protein_g": 0,
                "fat_g": 0,
                "carb_g": 0,
                "fiber_g": 0,
                "sugar_g": 0,
                "sodium_mg": 0
            }},
            "nutrition_tags": ["标签1", "标签2"],
            "risk_flags": [
                {{
                    "code": "high_sugar",
                    "severity": "medium",
                    "reason": "含糖酱汁较多"
                }}
            ],
            "thought_process": "Detailed step-by-step reasoning in Chinese",
            "items": [
                {{
                    "name": "单个食物名称",
                    "ingredient_evidence": "简短说明视觉证据或主要食材",
                    "nutrition": {{
                        "calories_kcal": 0,
                        "protein_g": 0,
                        "fat_g": 0,
                        "carb_g": 0,
                        "fiber_g": 0,
                        "sugar_g": 0,
                        "sodium_mg": 0
                    }},
                    "nutrition_tags": ["Tag1", "Tag2"],
                    "risk_flags": [
                        {{
                            "code": "low_protein",
                            "severity": "low",
                            "reason": "主食较多，优质蛋白较少"
                        }}
                    ]
                }}
            ],
            "total_analysis": {{
                "summary": "整餐简要总结",
                "suggestion": "结合用户目标给出实用建议",
                "confidence": 0.95
            }}
        }}
        """

        response = await async_client.chat.completions.create(
            model="qwen3-vl-flash",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            response_format={"type": "json_object"},
            timeout=45.0
        )

        content = response.choices[0].message.content
        return json.loads(content)
    except VisionServiceError:
        raise
    except Exception:
        logger.exception("Error in analyze_food_image")
        raise VisionServiceError("图像分析服务暂时不可用，请稍后重试")
    finally:
        if converted_path and os.path.exists(converted_path):
            try:
                os.remove(converted_path)
                logger.info("Cleaned up converted file: %s", converted_path)
            except Exception:
                logger.exception("Error cleaning up %s", converted_path)


async def generate_alternative_suggestions(analysis_result, user_context):
    start_time = time.time()
    try:
        _ensure_api_key_configured()
        food_name = analysis_result.get("main_name", "未知食物")

        logger.info("Generating suggestions for: %s", food_name)

        prompt = f"""
        Role: Professional Nutritionist and AI Diet Expert.
        Task: Based on a previous food analysis which resulted in a YELLOW or RED alert, provide two types of "AI Hack" (AI 爆改) suggestions to make the meal healthier.

        Context:
        - Food Name: {food_name}
        - Calories: {analysis_result.get('total_calories')} kcal
        - Nutrition Totals: {json.dumps(analysis_result.get('nutrition_totals', {}), ensure_ascii=False)}
        - Nutrition Tags: {', '.join(analysis_result.get('nutrition_tags', []))}
        - Risk Flags: {json.dumps(analysis_result.get('risk_flags', []), ensure_ascii=False)}
        - Warning Message: {analysis_result.get('warning_message')}
        - Current Rating: {analysis_result.get('total_traffic_light')}
        - User Goal: {user_context.get('goal')}
        - User Health Conditions: {', '.join(user_context.get('health_conditions', []))}

        Instructions:
        1. Provide an 'ordering_hint': a healthier option for ordering, directly targeting the biggest risk flags first.
        2. Provide a 'cooking_hint': a practical way to remake or adjust the dish at home, clearly reducing the problematic nutrient.
        3. Keep suggestions concise, practical, and highly relevant to the warning message, risk flags, and user context.
        4. Both suggestions MUST be in Simplified Chinese (简体中文).

        Output Format (STRICT JSON):
        {{
            "ordering_hint": "Ordering suggestion here",
            "cooking_hint": "Cooking suggestion here"
        }}
        """

        response = await async_client.chat.completions.create(
            model="qwen-flash",
            messages=[
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}]
                }
            ],
            response_format={"type": "json_object"},
            timeout=30.0
        )

        content = response.choices[0].message.content
        duration = time.time() - start_time
        logger.info("Suggestions for %s generated in %.2fs", food_name, duration)
        return json.loads(content)
    except VisionServiceError:
        raise
    except Exception:
        duration = time.time() - start_time
        logger.exception("Error in generate_alternative_suggestions after %.2fs", duration)
        raise VisionServiceError("爆改建议服务暂时不可用，请稍后重试")
