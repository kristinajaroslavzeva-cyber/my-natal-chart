from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import google.generativeai as genai

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# КЛЮЧ
GEMINI_API_KEY = "AIzaSyD-cVzx6xh-fUmajMe15-CV8RvNpLxLKNc"
genai.configure(api_key=GEMINI_API_KEY)

# --- АВТОПОДБОР МОДЕЛИ (Чтобы не было 404) ---
active_model = None
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            active_model = genai.GenerativeModel(m.name)
            break
except:
    pass

# Если автоподбор не сработал - берем Flash
if not active_model:
    active_model = genai.GenerativeModel('gemini-1.5-flash')

# -----------------------------------------------------------

class BirthData(BaseModel):
    birthDateTime: str
    latitude: float
    longitude: float
    zoneId: str

# Расчет (оставляем пустым, чтобы не мешал тесту ИИ)
@app.post("/calculate")
async def calculate_chart(data: BirthData):
    return {"planets": [], "houses": [], "angles": {"Ascendant": 0.0, "MC": 0.0}}

# --- ИНТЕРПРЕТАЦИЯ (ТЕПЕРЬ ДЛИННАЯ) ---
@app.post("/interpret")
async def interpret(request: dict):
    try:
        # ВОТ ЗДЕСЬ Я ИСПРАВИЛ "КОРОТКИЙ" НА "ПОДРОБНЫЙ"
        prompt = (
            "Ты профессиональный астролог. Напиши ПОДРОБНЫЙ, ГЛУБОКИЙ и РАЗВЕРНУТЫЙ "
            "психологический портрет личности. Не жалей слов. Опиши характер детально. "
            "ВАЖНО: Пиши чистым текстом, без звездочек и жирного шрифта."
        )
        resp = active_model.generate_content(prompt)
        return Response(content=resp.text, media_type="text/plain; charset=utf-8")
        
    except Exception as e:
        return Response(content=f"ОШИБКА: {str(e)}", media_type="text/plain; charset=utf-8")

# --- ГОРОСКОП (ТЕПЕРЬ ДЛИННЫЙ) ---
@app.post("/personal_horoscope")
async def personal(request: dict):
    try:
        # И ЗДЕСЬ ТОЖЕ
        prompt = (
            "Напиши БОЛЬШОЙ и ПОДРОБНЫЙ гороскоп на сегодня. "
            "Расшифруй сферы: Любовь, Карьера, Деньги, Здоровье. "
            "Дай развернутый совет дня. "
            "Пиши чистым текстом без форматирования."
        )
        resp = active_model.generate_content(prompt)
        return Response(content=resp.text, media_type="text/plain; charset=utf-8")

    except Exception as e:
        return Response(content=f"ОШИБКА: {str(e)}", media_type="text/plain; charset=utf-8")

@app.post("/synastry")
async def synastry(request: dict):
    try:
        resp = active_model.generate_content("Напиши подробный анализ совместимости. Дай 3 важных совета. Без форматирования.")
        return Response(content=resp.text, media_type="text/plain; charset=utf-8")
    except Exception as e:
        return Response(content=f"ОШИБКА: {str(e)}", media_type="text/plain; charset=utf-8")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
