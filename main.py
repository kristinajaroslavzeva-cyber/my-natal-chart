from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- НАСТРОЙКА GEMINI ---
# ВАЖНО: Никогда не свети реальный ключ в скриншотах или чатах!
# Вставь свой ключ сюда (тот, что начинался на AIza...)
GEMINI_API_KEY = "AIzaSyD-cVzx6xh-fUmajMe15-CV8RvNpLxLKNc"
genai.configure(api_key=GEMINI_API_KEY)

# Настройки безопасности: ОТКЛЮЧАЕМ блокировку, чтобы гороскопы не резались
# из-за слов "смерть", "секс", "опасность" и т.д.
safety_settings = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

# Используем конкретную, стабильную модель
model = genai.GenerativeModel(
    model_name='gemini-1.5-flash',
    safety_settings=safety_settings
)

# -----------------------------------------------------------

class BirthData(BaseModel):
    birthDateTime: str
    latitude: float
    longitude: float
    zoneId: str

@app.post("/calculate")
async def calculate_chart(data: BirthData):
    # Заглушка для теста
    return {"planets": [], "houses": [], "angles": {"Ascendant": 0.0, "MC": 0.0}}

@app.post("/interpret")
async def interpret(request: dict):
    try:
        prompt = (
            "Ты профессиональный астролог. Напиши ПОДРОБНЫЙ, ГЛУБОКИЙ и РАЗВЕРНУТЫЙ "
            "психологический портрет личности. Не жалей слов. Опиши характер детально. "
            "ВАЖНО: Пиши обычным сплошным текстом. НЕ используй жирный шрифт, "
            "НЕ используй звездочки (**), НЕ используй заголовки (#)."
        )
        # Убрали stream=True, ждем полный ответ сразу
        resp = model.generate_content(prompt)
        
        # Проверка, вернулся ли текст (иногда бывает пусто)
        if not resp.text:
            return Response(content="Не удалось составить интерпретацию. Попробуйте снова.", media_type="text/plain; charset=utf-8")
            
        return Response(content=resp.text, media_type="text/plain; charset=utf-8")
        
    except Exception as e:
        print(f"Ошибка Interpret: {e}")
        return Response(content=f"ОШИБКА СЕРВЕРА: {str(e)}", media_type="text/plain; charset=utf-8")

@app.post("/personal_horoscope")
async def personal(request: dict):
    try:
        prompt = (
            "Напиши БОЛЬШОЙ и ПОДРОБНЫЙ гороскоп на сегодня. "
            "Расшифруй сферы: Любовь, Карьера, Деньги, Здоровье. "
            "Дай развернутый совет дня. "
            "ВАЖНО: Пиши обычным текстом без Markdown форматирования (без звездочек и решеток)."
        )
        resp = model.generate_content(prompt)

        if not resp.text:
             return Response(content="Звезды сегодня молчат. Попробуйте позже.", media_type="text/plain; charset=utf-8")

        return Response(content=resp.text, media_type="text/plain; charset=utf-8")

    except Exception as e:
        print(f"Ошибка Horoscope: {e}")
        return Response(content=f"ОШИБКА СЕРВЕРА: {str(e)}", media_type="text/plain; charset=utf-8")

@app.post("/synastry")
async def synastry(request: dict):
    try:
        prompt = "Напиши подробный анализ совместимости. Дай 3 важных совета. Пиши простым текстом без форматирования."
        resp = model.generate_content(prompt)
        return Response(content=resp.text, media_type="text/plain; charset=utf-8")
    except Exception as e:
        return Response(content=f"ОШИБКА: {str(e)}", media_type="text/plain; charset=utf-8")

if __name__ == "__main__":
    import uvicorn
    # Порт 10000 для Render, 8000 для локалки
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
