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

# ТВОЙ КЛЮЧ
GEMINI_API_KEY = "AIzaSyD-cVzx6xh-fUmajMe15-CV8RvNpLxLKNc"
genai.configure(api_key=GEMINI_API_KEY)

# --- НАСТРОЙКИ БЕЗОПАСНОСТИ (ЧТОБЫ НЕ БЫЛО ПУСТЫХ ОТВЕТОВ) ---
# Это критически важно для гороскопов, иначе Gemini блокирует слова про "смерть", "страсть" и т.д.
safety_settings = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

# --- АВТОПОДБОР МОДЕЛИ (КАК БЫЛО У ТЕБЯ) ---
active_model = None
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            # Инициализируем найденную модель СРАЗУ с настройками безопасности
            active_model = genai.GenerativeModel(
                model_name=m.name,
                safety_settings=safety_settings
            )
            print(f"Модель найдена и активирована: {m.name}")
            break
except Exception as e:
    print(f"Ошибка автоподбора модели: {e}")

# Если вдруг цикл не сработал (резерв)
if not active_model:
    print("Внимание: Автоподбор не сработал, пробуем стандартную...")
    active_model = genai.GenerativeModel(
        'gemini-pro', 
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
    return {"planets": [], "houses": [], "angles": {"Ascendant": 0.0, "MC": 0.0}}

@app.post("/interpret")
async def interpret(request: dict):
    try:
        # Промпт без Markdown, чтобы не ломать парсинг
        prompt = (
            "Ты профессиональный астролог. Напиши ПОДРОБНЫЙ, ГЛУБОКИЙ и РАЗВЕРНУТЫЙ "
            "психологический портрет личности. Не жалей слов. Опиши характер детально. "
            "ВАЖНО: Пиши обычным сплошным текстом. НЕ используй жирный шрифт, "
            "НЕ используй звездочки (**), НЕ используй заголовки (#)."
        )
        
        if active_model:
            resp = active_model.generate_content(prompt)
            # Проверка на пустоту
            if not resp.text:
                return Response(content="Ответ пустой. Попробуйте снова.", media_type="text/plain; charset=utf-8")
            return Response(content=resp.text, media_type="text/plain; charset=utf-8")
        else:
            return Response(content="Ошибка: Модель AI не инициализирована.", media_type="text/plain; charset=utf-8")
        
    except Exception as e:
        return Response(content=f"ОШИБКА: {str(e)}", media_type="text/plain; charset=utf-8")

@app.post("/personal_horoscope")
async def personal(request: dict):
    try:
        prompt = (
            "Напиши БОЛЬШОЙ и ПОДРОБНЫЙ гороскоп на сегодня. "
            "Расшифруй сферы: Любовь, Карьера, Деньги, Здоровье. "
            "Дай развернутый совет дня. "
            "ВАЖНО: Пиши обычным текстом без Markdown форматирования (без звездочек и решеток)."
        )
        
        if active_model:
            resp = active_model.generate_content(prompt)
             # Проверка на пустоту
            if not resp.text:
                return Response(content="Звезды молчат. Попробуйте позже.", media_type="text/plain; charset=utf-8")
            return Response(content=resp.text, media_type="text/plain; charset=utf-8")
        else:
             return Response(content="Ошибка: Модель AI не инициализирована.", media_type="text/plain; charset=utf-8")

    except Exception as e:
        return Response(content=f"ОШИБКА: {str(e)}", media_type="text/plain; charset=utf-8")

@app.post("/synastry")
async def synastry(request: dict):
    try:
        if active_model:
            resp = active_model.generate_content("Напиши подробный анализ совместимости. Дай 3 важных совета. Без форматирования.")
            return Response(content=resp.text, media_type="text/plain; charset=utf-8")
        else:
            return Response(content="Ошибка: Модель AI не инициализирована.", media_type="text/plain; charset=utf-8")
    except Exception as e:
        return Response(content=f"ОШИБКА: {str(e)}", media_type="text/plain; charset=utf-8")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
