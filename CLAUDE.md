# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture Overview
LifeLens (智眼生活) is an AI-native nutrition analysis mobile app ("Smart Dining") that uses a "Camera-First" approach.

- **Frontend**: Uni-app (Vue 3 + Vite + Pinia). Designed for mobile (H5/Mini-program) with a HUD-style AR overlay UI.
- **Backend**: Python FastAPI. Acts as a gateway to multimodal LLMs.
- **AI Engine**: Qwen3-VL-Flash (via DashScope API) for visual recognition and nutrition estimation.
- **Key Flow**: Image capture -> Frontend compression -> Backend API -> Qwen-VL -> JSON Response -> AR Overlay.

## Build & Run Commands

### Backend (Python FastAPI)
*   **Setup**: `cd backend && pip install -r requirements.txt`
*   **Run Server**: `cd backend && python main.py` (Runs on localhost:8000)
*   **Test API**: `cd backend && python test_api.py` (Standalone verification script)
*   **Env Config**: Ensure `DASHSCOPE_API_KEY` is set in `backend/.env` or environment variables.

### Frontend (Uni-app/Vue3)
*   **Setup**: `cd frontend && npm install`
*   **Run H5 Dev**: `cd frontend && npm run dev:h5`
*   **Run WeChat MP Dev**: `cd frontend && npm run dev:mp-weixin`
*   **Build H5**: `cd frontend && npm run build:h5`

## Project Structure
*   **frontend/**
    *   `src/pages/`: UI screens (Home/Camera, Profile, History).
    *   `src/components/`: Reusable UI (HUD overlay, loading animations).
    *   `src/store/`: Pinia state management (User profile, Scan history).
    *   `src/utils/`: Helpers for requests (`request.js`), image compression, and permissions.
*   **backend/**
    *   `main.py`: FastAPI entry point and route definitions.
    *   `services/`: Core business logic (LLM integration, Prompt engineering).
    *   `test_api.py`: Script to verify backend connectivity without the frontend.
    *   `temp_images/`: Storage for uploaded images during processing.

## Code Style & Conventions
*   **Frontend**: Vue 3 Composition API (`<script setup>`).
*   **Backend**: Python 3.9+ with type hinting.
*   **Mock Mode**: The system includes a "Demo Mode" (activates by clicking Logo 5 times) for unstable networks, returning local mock data instead of calling the LLM.
*   **Image Handling**: Images are compressed on the frontend before upload to reduce latency.
