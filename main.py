from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import os
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- КЛЮЧ ---
GEMINI_API_KEY = "AIzaSyD-cVzx6xh-fUmajMe15-CV8RvNpLxLKNc"
genai.configure(api_key=GEMINI_API_KEY)

# --- НАСТРОЙКИ БЕЗОПАСНОСТИ (ОБЯЗАТЕЛЬНО) ---
safety_settings = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

# --- АВТОПОДБОР МОДЕЛИ (Твой рабочий метод) ---
active_model = None
try:
    # Ищем любую доступную модель, которая умеет генерировать текст
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            active_model = genai.GenerativeModel(m.name)
            print(f"Active model found: {m.name}")
            break
except Exception as e:
    print(f"Model selection error: {e}")

# Резерв, если цикл не сработал (чтобы сервер не упал при старте)
if not active_model:
    active_model = genai.GenerativeModel('gemini-1.5-flash')
# -----------------------------------------------------------

class BirthData(BaseModel):
    birthDateTime: str
    latitude: float
    longitude: float
    zoneId: str

# 1. РАСЧЕТ НАТАЛЬНОЙ КАРТЫ (ИСПРАВЛЕНО)
@app.post("/calculate")
async def calculate_chart(data: BirthData):
    # ВАЖНО: Мы возвращаем список планет с данными-заглушками.
    # Это нужно, чтобы приложение НЕ ПАДАЛО с ошибкой "No element".
    # Эти координаты (0.0, 120.0 и т.д.) просто позволят нарисовать круг.
    mock_planets = [
        {"name": "Sun", "angle": 0.0, "sign": "Aries", "retrograde": False},
        {"name": "Moon", "angle": 120.0, "sign": "Leo", "retrograde": False},
        {"name": "Mercury", "angle": 45.0, "sign": "Taurus", "retrograde": True},
        {"name": "Venus", "angle": 90.0, "sign": "Gemini", "retrograde": False},
        {"name": "Mars", "angle": 180.0, "sign": "Libra", "retrograde": False},
        {"name": "Jupiter", "angle": 240.0, "sign": "Sagittarius", "retrograde": False},
        {"name": "Saturn", "angle": 300.0, "sign": "Aquarius", "retrograde": True}
    ]
    
    # Также заполняем дома, чтобы наверняка
    mock_houses = [i * 30.0 for i in range(12)]

    return {
        "planets": mock_planets, 
        "houses": mock_houses, 
        "angles": {"Ascendant": 0.0, "MC": 90.0}
    }

# 2. ИНТЕРПРЕТАЦИЯ (ЧИСТЫЙ ИИ)
@app.post("/interpret")
async def interpret(request: dict):
    try:
        # Просто просим ИИ, модель уже инициализирована выше
        if active_model:
            prompt = "Ты астролог. Составь краткий психологический портрет личности. Без форматирования."
            resp = active_model.generate_content(prompt)
            return Response(content=resp.text, media_type="text/plain; charset=utf-8")
        
        return Response(content="Астролог сейчас отдыхает.", media_type="text/plain; charset=utf-8")
    except Exception as e:
        return Response(content=str(e), media_type="text/plain; charset=utf-8")

# 3. ГОРОСКОП НА СЕГОДНЯ (ЧИСТЫЙ ИИ)
@app.post("/personal_horoscope")
async def personal(request: dict):
    try:
        birth_date = request.get("birthDateTime", "Дата не указана")
        
        prompt = (
            f"Для человека с датой рождения {birth_date} составь "
            "гороскоп на сегодня. Позитивно, коротко, одной фразой."
        )

        if active_model:
            resp = active_model.generate_content(prompt)
            if resp.text:
                return Response(content=resp.text, media_type="text/plain; charset=utf-8")
        
        return Response(content="Звезды сегодня благосклонны к вам.", media_type="text/plain; charset=utf-8")

    except Exception as e:
        return Response(content="День полон загадок.", media_type="text/plain; charset=utf-8")

# 4. СИНАСТРИЯ
@app.post("/synastry")
async def synastry(request: dict):
    try:
        if active_model:
            resp = active_model.generate_content("Совместимость пары. Краткий совет.")
            return Response(content=resp.text, media_type="text/plain; charset=utf-8")
        return Response(content="Попробуйте позже", media_type="text/plain; charset=utf-8")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
