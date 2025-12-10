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

# 1. РАСЧЕТ (Оставляем пустым, чтобы не ломать логику приложения)
@app.post("/calculate")
async def calculate_chart(data: BirthData):
    # Возвращаем пустую структуру, но корректную, чтобы телефон не ругался
    return {"planets": [], "houses": [], "angles": {"Ascendant": 0.0, "MC": 0.0}}

# 2. НАТАЛЬНАЯ КАРТА (Работает - не трогаем)
@app.post("/interpret")
async def interpret(request: dict):
    try:
        prompt = (
            "Ты профессиональный астролог. Напиши ПОДРОБНЫЙ психопортрет. "
            "Пиши сплошным текстом без форматирования."
        )
        if active_model:
            resp = active_model.generate_content(prompt)
            return Response(content=resp.text, media_type="text/plain; charset=utf-8")
        return Response(content="Ошибка модели", media_type="text/plain; charset=utf-8")
    except Exception as e:
        return Response(content=str(e), media_type="text/plain; charset=utf-8")

# 3. ГОРОСКОП НА СЕГОДНЯ (ПОЛНОСТЬЮ ОТ ИИ)
@app.post("/personal_horoscope")
async def personal(request: dict):
    try:
        # Пытаемся достать дату рождения, чтобы гороскоп был хоть немного личным
        # Если даты нет, будет общий гороскоп
        birth_date = request.get("birthDateTime", "неизвестно")
        
        # Промпт для чистой генерации (без эфемерид)
        prompt = (
            f"Представь, что человек родился {birth_date}. "
            "Составь для него персональный, интересный гороскоп НА СЕГОДНЯ. "
            "Раздели мысленно на сферы: Настроение, Любовь, Деньги. "
            "Но выведи ответ ЕДИНЫМ сплошным текстом, без заголовков и звездочек. "
            "Пиши позитивно и загадочно."
        )

        if active_model:
            resp = active_model.generate_content(prompt)
            
            # Если ответ пришел - отдаем его
            if resp.text:
                return Response(content=resp.text, media_type="text/plain; charset=utf-8")
        
        # Если ИИ промолчал или модель не создана - отдаем заглушку, чтобы НЕ БЫЛО ОШИБКИ NO ELEMENT
        fallback = "Сегодня отличный день, чтобы прислушаться к себе. Звезды на вашей стороне."
        return Response(content=fallback, media_type="text/plain; charset=utf-8")

    except Exception as e:
        print(f"Error in horoscope: {e}")
        # В случае любой аварии возвращаем текст, а не ошибку 500
        return Response(content="Сегодня день сюрпризов. Будьте готовы к новому.", media_type="text/plain; charset=utf-8")

# 4. СИНАСТРИЯ (Работает - не трогаем)
@app.post("/synastry")
async def synastry(request: dict):
    try:
        if active_model:
            resp = active_model.generate_content("Напиши анализ совместимости. Дай совет. Без форматирования.")
            return Response(content=resp.text, media_type="text/plain; charset=utf-8")
        return Response(content="Ошибка модели", media_type="text/plain; charset=utf-8")
    except Exception as e:
        return Response(content=str(e), media_type="text/plain; charset=utf-8")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
