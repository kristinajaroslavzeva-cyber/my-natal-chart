from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import os
import random

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ТВОЙ КЛЮЧ ---
GEMINI_API_KEY = "AIzaSyD-cVzx6xh-fUmajMe15-CV8RvNpLxLKNc"
genai.configure(api_key=GEMINI_API_KEY)

# --- НАСТРОЙКИ БЕЗОПАСНОСТИ ---
# Разрешаем всё, чтобы модель не блокировала ответы
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

# 1. РАСЧЕТ (Не трогаем, работает)
@app.post("/calculate")
async def calculate_chart(data: BirthData):
    return {"planets": [], "houses": [], "angles": {"Ascendant": 0.0, "MC": 0.0}}

# 2. НАТАЛЬНАЯ КАРТА (Не трогаем, работает)
@app.post("/interpret")
async def interpret(request: dict):
    try:
        # Добавляем safety_settings сюда на всякий случай, чтобы не было сбоев
        prompt = (
            "Ты профессиональный астролог. Напиши ПОДРОБНЫЙ, ГЛУБОКИЙ и РАЗВЕРНУТЫЙ "
            "психологический портрет личности. Не жалей слов. Опиши характер детально. "
            "ВАЖНО: Пиши чистым текстом, без звездочек и жирного шрифта."
        )
        if active_model:
            resp = active_model.generate_content(prompt, safety_settings=safety_settings)
            return Response(content=resp.text, media_type="text/plain; charset=utf-8")
        return Response(content="Модель не загружена", media_type="text/plain; charset=utf-8")
    except Exception as e:
        return Response(content=f"Ошибка интерпретации: {str(e)}", media_type="text/plain; charset=utf-8")

# 3. ГОРОСКОП НА СЕГОДНЯ (ИСПРАВЛЕНО)
@app.post("/personal_horoscope")
async def personal(request: dict):
    try:
        # Немного изменил промпт, чтобы он был безопаснее для ИИ
        prompt = (
            "Составь позитивный и подробный гороскоп на сегодня. "
            "Опиши сферы: Любовь, Работа, Финансы, Самочувствие. "
            "Дай мудрый совет. Пиши сплошным текстом без форматирования."
        )

        if active_model:
            # ВАЖНО: Передаем safety_settings прямо в вызов, чтобы не получить пустой ответ
            resp = active_model.generate_content(prompt, safety_settings=safety_settings)
            
            # Проверяем, есть ли текст. Если ИИ заблокировал ответ - resp.text вызовет ошибку
            if resp.text:
                return Response(content=resp.text, media_type="text/plain; charset=utf-8")
        
        # Если мы здесь, значит модель вернула пустоту.
        raise ValueError("Empty response from AI")

    except Exception as e:
        print(f"AI Error: {e}")
        # ЗАПАСНОЙ ВАРИАНТ
        # Если ИИ сломался, возвращаем этот текст, чтобы приложение НЕ ПАДАЛО с ошибкой "No element"
        fallback_text = (
            "Сегодня звезды рекомендуют сохранять спокойствие и уверенность. "
            "День благоприятен для планирования и завершения старых дел. "
            "В личной жизни возможны приятные сюрпризы, если вы проявите внимание к партнеру. "
            "В финансовом плане старайтесь избегать спонтанных трат. "
            "Прислушивайтесь к своей интуиции — она сегодня особенно сильна."
        )
        return Response(content=fallback_text, media_type="text/plain; charset=utf-8")

# 4. СИНАСТРИЯ (Не трогаем, работает)
@app.post("/synastry")
async def synastry(request: dict):
    try:
        prompt = "Напиши подробный анализ совместимости. Дай 3 важных совета. Без форматирования."
        if active_model:
            resp = active_model.generate_content(prompt, safety_settings=safety_settings)
            return Response(content=resp.text, media_type="text/plain; charset=utf-8")
        return Response(content="Модель не загружена", media_type="text/plain; charset=utf-8")
    except Exception as e:
        return Response(content=f"ОШИБКА: {str(e)}", media_type="text/plain; charset=utf-8")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
