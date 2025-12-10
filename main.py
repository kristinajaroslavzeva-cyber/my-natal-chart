from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import pytz
import swisseph as swe
import os
import google.generativeai as genai

# --- НАСТРОЙКИ ---
# Вставь сюда свой ключ, который получишь в Google AI Studio
GEMINI_API_KEY = "AIzaSyAObmU1VR5hRc-bCcbYyfanS_6QQ2vr1ksА" 

# Настраиваем ИИ
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash') # Используем быструю модель

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Настройка эфемерид
current_dir = os.path.dirname(os.path.abspath(__file__))
ephe_path = os.path.join(current_dir, 'ephe')
swe.set_ephe_path(ephe_path)

class BirthData(BaseModel):
    birthDateTime: str
    latitude: float
    longitude: float
    zoneId: str

def get_sign(longitude):
    signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", 
             "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    idx = int(longitude / 30)
    return signs[idx % 12]

# ... Функция calculate_chart ОСТАЕТСЯ ТАКОЙ ЖЕ, КАК БЫЛА В ПРОШЛОМ КОДЕ ...
# (Я сокращу её здесь для краткости, но ты оставь полную версию с расчетом планет и домов)
@app.post("/calculate")
async def calculate_chart(data: BirthData):
    # ... (Тут должен быть весь код расчета из прошлого сообщения) ...
    # ... Обязательно вставь сюда полный код calculate_chart ...
    # ... Чтобы ИИ получал данные, их нужно сначала посчитать ...
    pass # <-- Удали это и верни код расчета!

@app.post("/interpret")
async def interpret(request: dict):
    try:
        # 1. Получаем данные карты от приложения
        chart = request.get('chart', request)
        planets = chart.get('planets', [])
        houses = chart.get('houses', [])
        
        # 2. Формируем "Промпт" (Запрос) для ИИ
        # Мы собираем данные в текст, чтобы ИИ их понял
        prompt_data = "Рассчитанные данные натальной карты:\n"
        for p in planets:
            prompt_data += f"{p['name']}: {p['sign']} ({p['signDegree']:.1f}°), Дом: неизвестен пока.\n"
        
        # Добавляем инструкцию для ИИ
        full_prompt = (
            f"Ты — профессиональный астролог. Вот данные карты клиента:\n{prompt_data}\n\n"
            "Напиши краткую, но емкую интерпретацию личности (психологический портрет). "
            "Сделай акцент на Солнце, Луне и Асценденте (если есть). "
            "Текст должен быть вдохновляющим, структурированным, с использованием Markdown. "
            "Не пиши технические термины, пиши для человека."
        )

        # 3. Спрашиваем ИИ
        response = model.generate_content(full_prompt)
        
        # 4. Отдаем текст приложению
        return response.text

    except Exception as e:
        return f"Ошибка ИИ: {str(e)}. (Возможно, ключ неверный или лимит исчерпан)."

# ... остальные функции (synastry, personal) можно тоже подключить к ИИ ...

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
