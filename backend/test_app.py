import asyncio
import io
import json
import os
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
import httpx
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))

import main
from services import vision_service
from utils import cleanup, db


class LifeLensApiTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_uploads_dir = main.UPLOADS_DIR
        self.original_db_path = db.DB_PATH
        self.original_max_upload_bytes = main.MAX_UPLOAD_SIZE_BYTES
        self.original_max_upload_mb = main.MAX_UPLOAD_SIZE_MB
        self.original_thumbnail_retention_days = main.THUMBNAIL_RETENTION_DAYS
        self.original_thumbnail_max_edge = main.THUMBNAIL_MAX_EDGE
        self.original_thumbnail_quality = main.THUMBNAIL_QUALITY
        self.original_upload_storage_limit_mb = main.UPLOAD_STORAGE_LIMIT_MB
        self.original_upload_storage_limit_bytes = main.UPLOAD_STORAGE_LIMIT_BYTES

        temp_root = Path(self.temp_dir.name)
        main.UPLOADS_DIR = temp_root / "uploads"
        main.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        db.DB_PATH = temp_root / "lifelens.db"

        for route in main.app.routes:
            if getattr(route, "name", None) == "uploads":
                route.app.directory = str(main.UPLOADS_DIR)
                if hasattr(route.app, "all_directories"):
                    route.app.all_directories = [str(main.UPLOADS_DIR)]

        self.client_context = TestClient(main.app)
        self.client = self.client_context.__enter__()

    def tearDown(self):
        self.client_context.__exit__(None, None, None)
        main.UPLOADS_DIR = self.original_uploads_dir
        db.DB_PATH = self.original_db_path
        main.MAX_UPLOAD_SIZE_BYTES = self.original_max_upload_bytes
        main.MAX_UPLOAD_SIZE_MB = self.original_max_upload_mb
        main.THUMBNAIL_RETENTION_DAYS = self.original_thumbnail_retention_days
        main.THUMBNAIL_MAX_EDGE = self.original_thumbnail_max_edge
        main.THUMBNAIL_QUALITY = self.original_thumbnail_quality
        main.UPLOAD_STORAGE_LIMIT_MB = self.original_upload_storage_limit_mb
        main.UPLOAD_STORAGE_LIMIT_BYTES = self.original_upload_storage_limit_bytes

        for route in main.app.routes:
            if getattr(route, "name", None) == "uploads":
                route.app.directory = str(main.UPLOADS_DIR)
                if hasattr(route.app, "all_directories"):
                    route.app.all_directories = [str(main.UPLOADS_DIR)]

        try:
            self.temp_dir.cleanup()
        except PermissionError:
            pass

    def _make_image_bytes(self, image_format="PNG"):
        image = Image.new("RGB", (12, 12), color=(255, 120, 0))
        buffer = io.BytesIO()
        image.save(buffer, format=image_format)
        return buffer.getvalue()

    def _default_user_context(self):
        return {
            "age": 25,
            "goal": "muscle_gain",
            "health_conditions": ["Nut Allergy"],
        }

    def _valid_analysis_result(self):
        return {
            "main_name": "鸡胸肉沙拉",
            "nutrition_totals": {
                "calories_kcal": 320,
                "protein_g": 32,
                "fat_g": 9,
                "carb_g": 12,
                "fiber_g": 5,
                "sugar_g": 4,
                "sodium_mg": 360,
            },
            "nutrition_tags": ["高蛋白", "高纤维", "低脂"],
            "risk_flags": [],
            "thought_process": "识别为一份鸡胸肉沙拉。",
            "items": [
                {
                    "name": "鸡胸肉沙拉",
                    "ingredient_evidence": "可见鸡胸肉、生菜和少量酱汁",
                    "nutrition": {
                        "calories_kcal": 320,
                        "protein_g": 32,
                        "fat_g": 9,
                        "carb_g": 12,
                        "fiber_g": 5,
                        "sugar_g": 4,
                        "sodium_mg": 360,
                    },
                    "nutrition_tags": ["高蛋白", "高纤维", "低脂"],
                    "risk_flags": [],
                }
            ],
            "total_analysis": {
                "summary": "高蛋白低脂。",
                "suggestion": "适合控脂期食用。",
                "confidence": 0.91,
            },
        }

    def _init_user(self, user_id=""):
        return self.client.post("/api/v1/user/init", json={"user_id": user_id})

    def _auth_headers(self, user_id):
        return {"X-User-Id": user_id}

    def _save_record_payload(self):
        return {
            "main_name": "牛油果鸡胸肉沙拉",
            "total_calories": 420,
            "total_traffic_light": "green",
            "summary": "蛋白质充足，脂肪质量较好。",
            "warning_message": "",
            "nutrition_totals": {
                "calories_kcal": 420,
                "protein_g": 31.5,
                "fat_g": 18.0,
                "carb_g": 26.0,
                "fiber_g": 9.0,
                "sugar_g": 4.0,
                "sodium_mg": 410,
            },
            "nutrition_tags": ["高蛋白", "高纤维"],
            "image_url": "/uploads/demo.jpg",
            "image_expires_at": "2026-04-11T00:00:00Z",
        }

    def _history_advice_payload(self, question=""):
        return {
            "question": question,
            "window_days": 0,
            "client_context": {"today": "2026-03-21"},
            "user_context": self._default_user_context(),
            "weekly_stats": [
                {"fullDate": "2026-03-20", "label": "3/20", "calories": 520, "protein": 28.5, "fat": 18.0, "carb": 42.0},
                {"fullDate": "2026-03-21", "label": "3/21", "calories": 610, "protein": 24.0, "fat": 22.0, "carb": 56.0},
            ],
            "recent_entries": [
                {
                    "timestamp": "2026-03-21T12:30:00Z",
                    "local_date": "2026-03-21",
                    "main_name": "鸡胸肉沙拉",
                    "total_traffic_light": "yellow",
                    "warning_message": "这餐需要注意：蛋白质偏低。建议控制分量并优化搭配。",
                    "nutrition_totals": {
                        "calories_kcal": 420,
                        "protein_g": 20.0,
                        "fat_g": 16.0,
                        "carb_g": 36.0,
                        "fiber_g": 5.0,
                        "sugar_g": 8.0,
                        "sodium_mg": 480,
                    },
                    "nutrition_tags": ["高蛋白", "低脂"],
                    "summary": "整体较轻盈，但蛋白质仍可提升。",
                }
            ],
        }

    def _analysis_result_with_flags(self, flags, *, goal="healthy_eat", health_conditions=None):
        payload = {
            "main_name": "测试餐",
            "nutrition_totals": {
                "calories_kcal": 520,
                "protein_g": 18,
                "fat_g": 16,
                "carb_g": 48,
                "fiber_g": 4,
                "sugar_g": 12,
                "sodium_mg": 420,
            },
            "risk_flags": flags,
            "items": [
                {
                    "name": "测试餐",
                    "ingredient_evidence": "根据图片判断为一份测试餐",
                    "nutrition": {
                        "calories_kcal": 520,
                        "protein_g": 18,
                        "fat_g": 16,
                        "carb_g": 48,
                        "fiber_g": 4,
                        "sugar_g": 12,
                        "sodium_mg": 420,
                    },
                    "risk_flags": flags,
                }
            ],
            "total_analysis": {
                "summary": "测试摘要",
                "suggestion": "测试建议",
                "confidence": 0.82,
            },
        }
        user_context = {
            "goal": goal,
            "health_conditions": health_conditions or [],
        }
        return main._normalize_analysis_result(payload, user_context)

    def test_health_endpoint(self):
        response = self.client.get("/api/v1/health")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["service"], "lifelens-api")
        self.assertEqual(payload["max_upload_size_mb"], main.MAX_UPLOAD_SIZE_MB)
        self.assertEqual(payload["thumbnail_retention_days"], main.THUMBNAIL_RETENTION_DAYS)
        self.assertEqual(payload["thumbnail_max_edge"], main.THUMBNAIL_MAX_EDGE)
        self.assertEqual(payload["thumbnail_quality"], main.THUMBNAIL_QUALITY)
        self.assertEqual(payload["upload_storage_limit_mb"], main.UPLOAD_STORAGE_LIMIT_MB)

    def test_init_user_is_idempotent_and_returns_qr_data(self):
        user_id = "46bc4d8c-c5e2-4758-b2ed-b8fa928687ec"

        first = self._init_user(user_id)
        second = self._init_user(user_id)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        first_data = first.json()["data"]
        second_data = second.json()["data"]
        self.assertEqual(first_data["user_id"], user_id)
        self.assertEqual(first_data["friend_code"], second_data["friend_code"])
        self.assertTrue(first_data["qr_payload"].startswith("lifelens:add:"))
        self.assertTrue(first_data["qr_image_data_url"].startswith("data:image/png;base64,"))

    def test_init_user_rejects_invalid_uuid(self):
        response = self._init_user("not-a-uuid")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "用户标识无效")

    def test_add_friend_is_bidirectional_and_idempotent(self):
        alice = self._init_user("46bc4d8c-c5e2-4758-b2ed-b8fa928687ec").json()["data"]
        bob = self._init_user("b621f702-9fa4-4cfd-95be-5847cca09a95").json()["data"]

        first_add = self.client.post(
            "/api/v1/friends/add",
            headers=self._auth_headers(alice["user_id"]),
            json={"friend_code": bob["friend_code"]},
        )
        second_add = self.client.post(
            "/api/v1/friends/add",
            headers=self._auth_headers(alice["user_id"]),
            json={"friend_code": bob["friend_code"]},
        )
        reverse_feed = self.client.get(
            "/api/v1/friends/feed",
            headers=self._auth_headers(bob["user_id"]),
        )

        self.assertEqual(first_add.status_code, 200)
        self.assertTrue(first_add.json()["data"]["created"])
        self.assertEqual(second_add.status_code, 200)
        self.assertFalse(second_add.json()["data"]["created"])
        self.assertEqual(reverse_feed.status_code, 200)
        self.assertEqual(reverse_feed.json()["data"]["total_friends"], 1)

    def test_add_friend_rejects_self_and_invalid_code(self):
        user = self._init_user("46bc4d8c-c5e2-4758-b2ed-b8fa928687ec").json()["data"]

        invalid_format = self.client.post(
            "/api/v1/friends/add",
            headers=self._auth_headers(user["user_id"]),
            json={"friend_code": "12345"},
        )
        self_add = self.client.post(
            "/api/v1/friends/add",
            headers=self._auth_headers(user["user_id"]),
            json={"friend_code": user["friend_code"]},
        )

        self.assertEqual(invalid_format.status_code, 400)
        self.assertIn("6 位数字", invalid_format.json()["message"])
        self.assertEqual(self_add.status_code, 400)
        self.assertEqual(self_add.json()["message"], "不能添加自己为好友")

    def test_add_friend_returns_not_found_for_unknown_target(self):
        user = self._init_user("46bc4d8c-c5e2-4758-b2ed-b8fa928687ec").json()["data"]

        response = self.client.post(
            "/api/v1/friends/add",
            headers=self._auth_headers(user["user_id"]),
            json={"friend_code": "999999"},
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["message"], "好友不存在")

    def test_create_diet_record_and_friend_feed(self):
        alice = self._init_user("46bc4d8c-c5e2-4758-b2ed-b8fa928687ec").json()["data"]
        bob = self._init_user("b621f702-9fa4-4cfd-95be-5847cca09a95").json()["data"]

        self.client.post(
            "/api/v1/friends/add",
            headers=self._auth_headers(alice["user_id"]),
            json={"friend_code": bob["friend_code"]},
        )

        record_response = self.client.post(
            "/api/v1/diet-records",
            headers=self._auth_headers(alice["user_id"]),
            json=self._save_record_payload(),
        )
        feed_response = self.client.get(
            "/api/v1/friends/feed",
            headers=self._auth_headers(bob["user_id"]),
        )

        self.assertEqual(record_response.status_code, 200)
        self.assertIn("recorded_at", record_response.json()["data"])
        self.assertEqual(feed_response.status_code, 200)
        payload = feed_response.json()["data"]
        self.assertEqual(payload["total_friends"], 1)
        self.assertEqual(len(payload["items"]), 1)
        self.assertEqual(payload["items"][0]["friend_code"], alice["friend_code"])
        self.assertEqual(payload["items"][0]["main_name"], "牛油果鸡胸肉沙拉")
        self.assertEqual(payload["items"][0]["nutrition_totals"]["protein_g"], 31.5)
        self.assertEqual(payload["items"][0]["nutrition_tags"], ["高蛋白", "高纤维"])
        self.assertEqual(payload["items"][0]["warning_message"], "")

    def test_feed_only_returns_today_records_in_beijing(self):
        alice = self._init_user("46bc4d8c-c5e2-4758-b2ed-b8fa928687ec").json()["data"]
        bob = self._init_user("b621f702-9fa4-4cfd-95be-5847cca09a95").json()["data"]

        self.client.post(
            "/api/v1/friends/add",
            headers=self._auth_headers(alice["user_id"]),
            json={"friend_code": bob["friend_code"]},
        )

        reference_time = datetime(2026, 3, 12, 4, 30, tzinfo=timezone.utc)
        old_record_time = (reference_time - timedelta(days=1)).replace(hour=10, minute=0)
        today_record_time = reference_time.replace(hour=2, minute=0)

        db.save_diet_record(
            alice["user_id"],
            recorded_at=old_record_time.isoformat().replace("+00:00", "Z"),
            **self._save_record_payload(),
        )
        db.save_diet_record(
            alice["user_id"],
            recorded_at=today_record_time.isoformat().replace("+00:00", "Z"),
            **self._save_record_payload(),
        )

        payload = db.get_today_friend_feed(bob["user_id"], reference_time=reference_time)
        self.assertEqual(payload["total_friends"], 1)
        self.assertEqual(len(payload["items"]), 1)
        self.assertEqual(payload["items"][0]["recorded_at"], "2026-03-12T02:00:00Z")

    def test_cleanup_expired_diet_records_removes_old_rows(self):
        user = self._init_user("46bc4d8c-c5e2-4758-b2ed-b8fa928687ec").json()["data"]

        db.save_diet_record(
            user["user_id"],
            recorded_at="2025-01-01T00:00:00Z",
            **self._save_record_payload(),
        )
        db.save_diet_record(
            user["user_id"],
            recorded_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            **self._save_record_payload(),
        )

        deleted = db.cleanup_expired_diet_records(30)
        payload = db.get_today_friend_feed(user["user_id"])

        self.assertGreaterEqual(deleted, 1)
        with db.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS total FROM diet_records")
            self.assertEqual(cursor.fetchone()["total"], 1)
        self.assertEqual(payload["total_friends"], 0)

    def test_normalize_analysis_result_prefers_item_totals_and_normalizes_numbers(self):
        result = main._normalize_analysis_result(
            {
                "main_name": "酸奶燕麦杯",
                "nutrition_totals": {
                    "calories_kcal": "999",
                    "protein_g": "99",
                    "fat_g": "99",
                    "carb_g": "99",
                    "fiber_g": "99",
                    "sugar_g": "99",
                    "sodium_mg": "99",
                },
                "risk_flags": [{"code": "high_sugar", "severity": "low", "reason": "顶层提示"}],
                "items": [
                    {
                        "name": "酸奶",
                        "nutrition": {
                            "calories_kcal": "200.4",
                            "protein_g": "12.3",
                            "fat_g": "6.2",
                            "carb_g": "15.4",
                            "fiber_g": "0.0",
                            "sugar_g": "10.2",
                            "sodium_mg": "120.3",
                        },
                    },
                    {
                        "name": "燕麦水果",
                        "nutrition": {
                            "calories_kcal": "219.6",
                            "protein_g": "8.3",
                            "fat_g": "3.4",
                            "carb_g": "31.1",
                            "fiber_g": "4.5",
                            "sugar_g": "11.1",
                            "sodium_mg": "79.6",
                        },
                    },
                ],
                "total_analysis": {
                    "summary": "营养较均衡。",
                    "suggestion": "注意控制加糖量。",
                    "confidence": "0.88",
                },
            },
            {"goal": "healthy_eat", "health_conditions": []},
        )

        self.assertEqual(result["total_calories"], 420)
        self.assertEqual(result["nutrition_totals"]["protein_g"], 20.6)
        self.assertEqual(result["nutrition_totals"]["sodium_mg"], 200)
        self.assertEqual(result["total_analysis"]["confidence"], 0.88)
        self.assertTrue(any(flag["code"] == "high_sugar" for flag in result["risk_flags"]))
        self.assertIn("高糖", result["nutrition_tags"])

    def test_normalize_analysis_result_translates_english_nutrition_tags(self):
        result = main._normalize_analysis_result(
            {
                "main_name": "照烧虾仁蔬菜盖饭",
                "nutrition_totals": {
                    "calories_kcal": 580,
                    "protein_g": 37,
                    "fat_g": 11.5,
                    "carb_g": 78,
                    "fiber_g": 4.5,
                    "sugar_g": 13.5,
                    "sodium_mg": 952,
                },
                "nutrition_tags": ["high_protein", "balanced_meal", "高钠"],
                "items": [
                    {
                        "name": "照烧虾仁蔬菜盖饭",
                        "nutrition": {
                            "calories_kcal": 580,
                            "protein_g": 37,
                            "fat_g": 11.5,
                            "carb_g": 78,
                            "fiber_g": 4.5,
                            "sugar_g": 13.5,
                            "sodium_mg": 952,
                        },
                        "nutrition_tags": ["High Protein", "balanced-meal", "low_fat"],
                    }
                ],
                "total_analysis": {
                    "summary": "测试摘要",
                    "suggestion": "测试建议",
                    "confidence": 0.9,
                },
            },
            {"goal": "healthy_eat", "health_conditions": []},
        )

        self.assertEqual(result["nutrition_tags"], ["高蛋白", "营养均衡", "高钠"])
        self.assertEqual(
            result["items"][0]["nutrition_tags"],
            ["高蛋白", "营养均衡", "低脂"],
        )

    def test_personalized_risk_scoring_branches(self):
        cases = [
            {
                "name": "糖尿病高糖",
                "flags": [{"code": "high_sugar", "severity": "high", "reason": "含糖饮料较多"}],
                "goal": "healthy_eat",
                "conditions": ["Diabetes"],
                "expected": "red",
            },
            {
                "name": "高血压高钠",
                "flags": [{"code": "high_sodium", "severity": "high", "reason": "酱汁偏咸"}],
                "goal": "healthy_eat",
                "conditions": ["Hypertension"],
                "expected": "red",
            },
            {
                "name": "高胆固醇饱和脂肪",
                "flags": [{"code": "high_saturated_fat", "severity": "high", "reason": "油炸与肥肉较多"}],
                "goal": "healthy_eat",
                "conditions": ["High Cholesterol"],
                "expected": "red",
            },
            {
                "name": "坚果过敏",
                "flags": [{"code": "allergen_risk", "severity": "high", "reason": "疑似含坚果碎"}],
                "goal": "healthy_eat",
                "conditions": ["Nut Allergy"],
                "expected": "red",
            },
            {
                "name": "无麸质",
                "flags": [{"code": "gluten_risk", "severity": "high", "reason": "疑似含小麦面包"}],
                "goal": "healthy_eat",
                "conditions": ["Gluten Free"],
                "expected": "red",
            },
            {
                "name": "乳糖不耐受",
                "flags": [{"code": "lactose_risk", "severity": "high", "reason": "含奶油与奶酪"}],
                "goal": "healthy_eat",
                "conditions": ["Lactose Intolerant"],
                "expected": "red",
            },
            {
                "name": "增肌低蛋白",
                "flags": [{"code": "low_protein", "severity": "medium", "reason": "以主食为主"}],
                "goal": "muscle_gain",
                "conditions": [],
                "expected": "yellow",
            },
            {
                "name": "减脂高热量高脂肪",
                "flags": [
                    {"code": "high_calorie", "severity": "high", "reason": "总热量偏高"},
                    {"code": "high_fat", "severity": "medium", "reason": "脂肪含量偏高"},
                ],
                "goal": "weight_loss",
                "conditions": [],
                "expected": "red",
            },
        ]

        for case in cases:
            with self.subTest(case["name"]):
                result = self._analysis_result_with_flags(
                    case["flags"],
                    goal=case["goal"],
                    health_conditions=case["conditions"],
                )
                self.assertEqual(result["total_traffic_light"], case["expected"])
                self.assertTrue(result["warning_message"])

    def test_init_db_migrates_legacy_diet_records_schema(self):
        with db.get_db() as conn:
            cursor = conn.cursor()
            cursor.executescript(
                """
                DROP TABLE IF EXISTS diet_records;
                DELETE FROM users;
                INSERT INTO users (user_id, friend_code, created_at)
                VALUES ('46bc4d8c-c5e2-4758-b2ed-b8fa928687ec', '123456', '2026-03-12T00:00:00Z');
                CREATE TABLE diet_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    main_name TEXT NOT NULL,
                    total_calories INTEGER NOT NULL,
                    total_traffic_light TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    image_url TEXT,
                    image_expires_at TEXT,
                    recorded_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                );
                INSERT INTO diet_records (
                    user_id,
                    main_name,
                    total_calories,
                    total_traffic_light,
                    summary,
                    image_url,
                    image_expires_at,
                    recorded_at
                )
                VALUES (
                    '46bc4d8c-c5e2-4758-b2ed-b8fa928687ec',
                    '旧版记录',
                    300,
                    'yellow',
                    '旧版摘要',
                    '/uploads/legacy.jpg',
                    '',
                    '2026-03-12T00:00:00Z'
                );
                """
            )
            conn.commit()

        db.init_db()

        with db.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(diet_records)")
            columns = {row["name"] for row in cursor.fetchall()}
            self.assertIn("warning_message", columns)
            self.assertIn("protein_g", columns)
            self.assertIn("nutrition_tags_json", columns)
            cursor.execute("SELECT main_name, warning_message, protein_g FROM diet_records")
            row = cursor.fetchone()
            self.assertEqual(row["main_name"], "旧版记录")
            self.assertEqual(row["warning_message"], "")
            self.assertEqual(row["protein_g"], 0)

    def test_history_advice_rejects_empty_recent_entries(self):
        payload = self._history_advice_payload()
        payload["recent_entries"] = []

        response = self.client.post("/api/v1/vision/history-advice", json=payload)

        self.assertEqual(response.status_code, 400)
        self.assertIn("暂无可用饮食记录", response.json()["message"])

    @patch.object(main, "generate_history_advice", new_callable=AsyncMock)
    def test_history_advice_accepts_non_weekly_window(self, advice_mock):
        advice_mock.return_value = {
            "answer": "可以回答",
            "observations": [],
            "suggestions": [],
            "focus_tags": [],
        }

        payload = self._history_advice_payload(question="今天吃得怎么样")
        payload["window_days"] = 1

        response = self.client.post("/api/v1/vision/history-advice", json=payload)

        self.assertEqual(response.status_code, 200)
        advice_mock.assert_awaited_once()

    @patch.object(main, "generate_history_advice", new_callable=AsyncMock)
    def test_history_advice_defaults_question_and_normalizes_response(self, advice_mock):
        advice_mock.return_value = {
            "answer": "",
            "observations": ["观察1", "", "观察2", "观察3", "观察4"],
            "suggestions": "bad-shape",
            "focus_tags": ["蛋白偏低", "高糖偏多", "高糖偏多", "晚餐过重", "零食偏多"],
        }

        response = self.client.post(
            "/api/v1/vision/history-advice",
            json=self._history_advice_payload(question=""),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["answer"], "已收到你的饮食记录，可以继续针对今天、最近或整体习惯提问。")
        self.assertEqual(payload["observations"], ["观察1", "观察2", "观察3"])
        self.assertEqual(payload["suggestions"], [])
        self.assertEqual(payload["focus_tags"], ["蛋白偏低", "高糖偏多", "晚餐过重", "零食偏多"])

        advice_mock.assert_awaited_once()
        args = advice_mock.await_args.args
        self.assertEqual(args[0], main.DEFAULT_HISTORY_ADVICE_QUESTION)
        self.assertEqual(args[1][0]["fullDate"], "2026-03-20")
        self.assertEqual(args[4]["today"], "2026-03-21")

    def test_rejects_invalid_file_type(self):
        response = self.client.post(
            "/api/v1/vision/analyze",
            files={"file": ("bad.svg", io.BytesIO(b"<svg></svg>"), "image/svg+xml")},
            data={"user_context": json.dumps(self._default_user_context())},
        )

        self.assertEqual(response.status_code, 415)
        payload = response.json()
        self.assertIn("trace_id", payload)
        self.assertEqual(list(main.UPLOADS_DIR.iterdir()), [])

    def test_rejects_oversized_upload(self):
        main.MAX_UPLOAD_SIZE_BYTES = 8
        main.MAX_UPLOAD_SIZE_MB = 1

        response = self.client.post(
            "/api/v1/vision/analyze",
            files={"file": ("large.jpg", io.BytesIO(b"123456789"), "image/jpeg")},
            data={"user_context": json.dumps(self._default_user_context())},
        )

        self.assertEqual(response.status_code, 413)
        self.assertIn("上传图片不能超过", response.json()["message"])
        self.assertEqual(list(main.UPLOADS_DIR.iterdir()), [])

    @patch.object(main, "analyze_food_image", new_callable=AsyncMock)
    def test_analyze_success_returns_accessible_image_url(self, analyze_mock):
        analyze_mock.return_value = self._valid_analysis_result()

        response = self.client.post(
            "/api/v1/vision/analyze",
            files={"file": ("meal.png", io.BytesIO(self._make_image_bytes("PNG")), "image/png")},
            data={"user_context": json.dumps(self._default_user_context())},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        image_url = payload["data"]["image_url"]
        image_expires_at = payload["data"]["image_expires_at"]
        saved_path = main.UPLOADS_DIR / Path(image_url).name
        saved_files = list(main.UPLOADS_DIR.iterdir())
        self.assertEqual(len(saved_files), 1)
        self.assertTrue(saved_path.exists())
        self.assertEqual(saved_path.suffix, ".jpg")
        self.assertNotIn("_source", saved_path.name)
        self.assertGreater(
            datetime.fromisoformat(image_expires_at.replace("Z", "+00:00")).timestamp(),
            time.time(),
        )

        with Image.open(saved_path) as saved_image:
            self.assertLessEqual(max(saved_image.size), main.THUMBNAIL_MAX_EDGE)

        image_response = self.client.get(image_url)
        self.assertEqual(image_response.status_code, 200)
        self.assertTrue(image_response.content)

    @patch.object(main, "analyze_food_image", new_callable=AsyncMock)
    def test_analyze_success_returns_accessible_image_url_for_jpeg_upload(self, analyze_mock):
        analyze_mock.return_value = self._valid_analysis_result()

        response = self.client.post(
            "/api/v1/vision/analyze",
            files={"file": ("meal.jpg", io.BytesIO(self._make_image_bytes("JPEG")), "image/jpeg")},
            data={"user_context": json.dumps(self._default_user_context())},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        image_url = payload["data"]["image_url"]
        saved_path = main.UPLOADS_DIR / Path(image_url).name
        saved_files = sorted(path.name for path in main.UPLOADS_DIR.iterdir())

        self.assertEqual(saved_path.name, Path(image_url).name)
        self.assertEqual(saved_path.suffix, ".jpg")
        self.assertEqual(saved_files, [saved_path.name])
        self.assertTrue(saved_path.exists())

        image_response = self.client.get(image_url)
        self.assertEqual(image_response.status_code, 200)
        self.assertTrue(image_response.content)

    def test_source_upload_path_differs_from_thumbnail_path_for_jpeg(self):
        trace_id = "sample-trace"
        source_path = main._build_source_upload_path(trace_id, "JPEG")
        thumbnail_path = main._build_thumbnail_path(trace_id)

        self.assertEqual(source_path.name, "sample-trace_source.jpg")
        self.assertEqual(thumbnail_path.name, "sample-trace.jpg")
        self.assertNotEqual(source_path, thumbnail_path)

    @patch.object(main, "analyze_food_image", new_callable=AsyncMock)
    def test_analyze_upstream_error_is_sanitized_and_cleans_upload(self, analyze_mock):
        analyze_mock.side_effect = main.VisionServiceError("图像分析服务暂时不可用，请稍后重试")

        response = self.client.post(
            "/api/v1/vision/analyze",
            files={"file": ("meal.png", io.BytesIO(self._make_image_bytes("PNG")), "image/png")},
            data={"user_context": json.dumps(self._default_user_context())},
        )

        self.assertEqual(response.status_code, 502)
        payload = response.json()
        self.assertEqual(payload["message"], "图像分析服务暂时不可用，请稍后重试")
        self.assertIn("trace_id", payload)
        self.assertEqual(list(main.UPLOADS_DIR.iterdir()), [])

    @patch.object(main, "generate_alternative_suggestions", new_callable=AsyncMock)
    def test_generate_alternatives_success(self, alternatives_mock):
        alternatives_mock.return_value = {
            "ordering_hint": "换成凉拌鸡胸肉。",
            "cooking_hint": "少油少盐。",
        }

        response = self.client.post(
            "/api/v1/vision/generate-alternatives",
            json={
                "analysis_result": {"main_name": "炸鸡", "total_traffic_light": "red"},
                "user_context": self._default_user_context(),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["ordering_hint"], "换成凉拌鸡胸肉。")

    @patch.object(main, "generate_alternative_suggestions", new_callable=AsyncMock)
    def test_generate_alternatives_error_branch(self, alternatives_mock):
        alternatives_mock.side_effect = main.VisionServiceError("爆改建议服务暂时不可用，请稍后重试")

        response = self.client.post(
            "/api/v1/vision/generate-alternatives",
            json={
                "analysis_result": {"main_name": "炸鸡", "total_traffic_light": "red"},
                "user_context": self._default_user_context(),
            },
        )

        self.assertEqual(response.status_code, 502)
        payload = response.json()
        self.assertEqual(payload["message"], "爆改建议服务暂时不可用，请稍后重试")
        self.assertIn("trace_id", payload)

    def test_migrate_legacy_webp_thumbnails_to_jpg(self):
        legacy_webp_path = main.UPLOADS_DIR / "legacy.webp"
        legacy_webp_path.write_bytes(self._make_image_bytes("WEBP"))

        main._migrate_legacy_webp_thumbnails()

        migrated_jpg_path = main.UPLOADS_DIR / "legacy.jpg"
        self.assertFalse(legacy_webp_path.exists())
        self.assertTrue(migrated_jpg_path.exists())

        with Image.open(migrated_jpg_path) as migrated_image:
            self.assertEqual(migrated_image.format, "JPEG")

    def test_cleanup_removes_old_files_and_enforces_storage_limit(self):
        old_path = main.UPLOADS_DIR / "old.webp"
        mid_path = main.UPLOADS_DIR / "mid.webp"
        new_path = main.UPLOADS_DIR / "new.webp"

        old_path.write_bytes(b"a" * 10)
        mid_path.write_bytes(b"b" * 10)
        new_path.write_bytes(b"c" * 10)

        now = time.time()
        os.utime(old_path, (now - 3 * 86400, now - 3 * 86400))
        os.utime(mid_path, (now - 100, now - 100))
        os.utime(new_path, (now - 50, now - 50))

        cleanup.enforce_storage_limit(str(main.UPLOADS_DIR), 15)
        remaining_after_limit = sorted(path.name for path in main.UPLOADS_DIR.iterdir())
        self.assertEqual(remaining_after_limit, ["new.webp"])

        os.utime(new_path, (now - 3 * 86400, now - 3 * 86400))
        self.assertTrue(new_path.exists())

        import asyncio

        asyncio.run(cleanup.cleanup_old_files(str(main.UPLOADS_DIR), days=1))
        self.assertEqual(list(main.UPLOADS_DIR.iterdir()), [])


class VisionServiceHelpersTestCase(unittest.TestCase):
    def test_qwen_models_disable_thinking(self):
        self.assertEqual(
            vision_service._get_model_request_kwargs("qwen3.5-flash"),
            {"extra_body": {"enable_thinking": False}},
        )
        self.assertEqual(
            vision_service._get_model_request_kwargs("qwen-plus"),
            {"extra_body": {"enable_thinking": False}},
        )
        self.assertEqual(
            vision_service._get_model_request_kwargs("doubao-seed-2-0-lite-260215"),
            {},
        )

    def test_prepare_inference_image_compresses_and_converts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "large.png"
            Image.new("RGBA", (2048, 1536), color=(30, 144, 255, 255)).save(source_path)

            prepared_path, meta = vision_service._prepare_inference_image(str(source_path))
            try:
                self.assertTrue(Path(prepared_path).exists())
                self.assertEqual(Path(prepared_path).suffix.lower(), ".jpg")
                self.assertEqual(meta["original_mime"], "image/png")
                self.assertEqual(meta["original_size"], [2048, 1536])
                self.assertLessEqual(max(meta["prepared_size"]), vision_service.MODEL_IMAGE_MAX_EDGE)

                with Image.open(prepared_path) as prepared_image:
                    self.assertEqual(prepared_image.format, "JPEG")
                    self.assertLessEqual(
                        max(prepared_image.size), vision_service.MODEL_IMAGE_MAX_EDGE
                    )
            finally:
                if os.path.exists(prepared_path):
                    os.remove(prepared_path)

    def test_compact_history_advice_context_trims_noise(self):
        weekly_stats = [
            {
                "fullDate": f"2026-03-{day:02d}",
                "label": f"3/{day}",
                "calories": 500 + day,
                "protein": 20 + day,
                "fat": 10 + day,
                "carb": 30 + day,
            }
            for day in range(20, 28)
        ]
        recent_entries = [
            {
                "timestamp": f"2026-03-{20 + index:02d}T12:00:00Z",
                "main_name": f"餐食{index}",
                "total_traffic_light": "yellow" if index % 2 else "green",
                "warning_message": "" if index == 2 else f"提醒{index}",
                "nutrition_totals": {
                    "calories_kcal": 0 if index == 2 else 350 + index,
                    "protein_g": 0 if index == 2 else 20 + index,
                    "fat_g": 0 if index == 2 else 8 + index,
                    "carb_g": 0 if index == 2 else 25 + index,
                    "fiber_g": 0,
                    "sugar_g": 0,
                    "sodium_mg": 0,
                },
                "nutrition_tags": ["高蛋白", "", "低脂"] if index != 2 else [],
                "summary": "" if index == 2 else f"摘要{index}",
            }
            for index in range(12)
        ]

        compact = vision_service._compact_history_advice_context(
            weekly_stats,
            recent_entries,
            {
                "goal": "muscle_gain",
                "health_conditions": ["Diabetes"],
                "age": 25,
            },
        )

        self.assertEqual(len(compact["weekly"]), vision_service.MAX_WEEKLY_DAYS_FOR_PROMPT)
        self.assertEqual(len(compact["recent_meals"]), vision_service.MAX_RECENT_ENTRIES_FOR_PROMPT)
        self.assertEqual(compact["recent_meals"][0]["meal"], "餐食11")
        self.assertNotIn("warning", compact["recent_meals"][-1])
        self.assertNotIn("summary", compact["recent_meals"][-1])
        self.assertNotIn("tags", compact["recent_meals"][-1])
        self.assertNotIn("nutrition", compact["recent_meals"][-1])
        self.assertEqual(compact["recent_meals"][0]["tags"], ["高蛋白", "低脂"])
        self.assertEqual(compact["profile"]["goal"], "muscle_gain")
        self.assertEqual(compact["weekly_avg"]["kcal"], 524)

    def test_create_json_completion_falls_back_from_json_schema(self):
        schema_error = httpx.Response(
            400,
            request=httpx.Request("POST", "https://example.com/v1/chat/completions"),
        )
        create_mock = AsyncMock(
            side_effect=[
                vision_service.BadRequestError(
                    "The parameter `response_format.type` specified in the request are not valid: `json_schema` is not supported by this model.",
                    response=schema_error,
                    body={"error": {"param": "response_format.type"}},
                ),
                SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            message=SimpleNamespace(
                                content='{"answer":"ok","observations":[],"suggestions":[],"focus_tags":[]}'
                            )
                        )
                    ]
                ),
            ]
        )
        fake_client = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create_mock))
        )

        with patch.object(vision_service, "_get_async_client", return_value=fake_client):
            vision_service._RESPONSE_FORMAT_SUPPORT.clear()
            result, meta = asyncio.run(
                vision_service._create_json_completion(
                    model="qwen3.5-flash",
                    messages=[{"role": "user", "content": "hi"}],
                    timeout=10,
                    response_formats=[
                        vision_service._build_json_schema_response_format(
                            vision_service.HISTORY_ADVICE_JSON_SCHEMA
                        ),
                        {"type": "json_object"},
                    ],
                )
            )

        self.assertEqual(result["answer"], "ok")
        self.assertEqual(meta["response_format_mode"], "json_object")
        self.assertTrue(meta["response_format_fallback"])
        self.assertEqual(
            create_mock.await_args_list[0].kwargs["response_format"]["type"], "json_schema"
        )
        self.assertEqual(
            create_mock.await_args_list[1].kwargs["response_format"]["type"], "json_object"
        )


if __name__ == "__main__":
    unittest.main()
