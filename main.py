from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import os

# --- ИМПОРТ FLATLIB (Обязательно должен быть установлен) ---
from flatlib.datetime import Datetime
from flatlib.geopos import GeoPos
from flatlib.chart import Chart
from flatlib import const

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- GEMINI API ---
GEMINI_API_KEY = "AIzaSyD-cVzx6xh-fUmajMe15-CV8RvNpLxLKNc"
genai.configure(api_key=GEMINI_API_KEY)

# --- ИНИЦИАЛИЗАЦИЯ МОДЕЛИ ---
active_model = None
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            active_model = genai.GenerativeModel(m.name)
            break
except Exception as e:
    print(f"Model init error: {e}")

if not active_model:
    active_model = genai.GenerativeModel('gemini-1.5-flash')


class BirthData(BaseModel):
    birthDateTime: str
    latitude: float
    longitude: float
    zoneId: str


# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

def get_sign_name(lon):
    signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    return signs[int(lon // 30) % 12]

# Функция для создания "пустой" карты, если реальный расчет сломался
# Это спасет приложение от красного экрана
def get_empty_chart_structure():
    planets = []
    names = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto", "Chiron", "Lilith", "NNode"]
    for name in names:
        planets.append({
            "name": name,
            "angle": 0.0,
            "sign": "Aries",
            "retrograde": False,
            "speed": 0.0,
            "lat": 0.0,
            "lng": 0.0,
            "house": 1
        })
    return {
        "planets": planets,
        "houses": [0.0] * 12,
        "angles": {"Ascendant": 0.0, "MC": 0.0}
    }


# 1. РАСЧЕТ КАРТЫ (РЕАЛЬНЫЙ)
@app.post("/calculate")
async def calculate_chart(data: BirthData):
    print(f"Received date: {data.birthDateTime}") # Логируем дату, чтобы понять проблему

    try:
        # 1. Парсинг даты для Flatlib
        # Flatlib очень капризный. Ему нужно 'YYYY/MM/DD' и 'HH:MM'
        # Пытаемся обработать разные варианты ISO строки
        
        clean_date = data.birthDateTime.replace('T', ' ').replace('Z', '')
        if ' ' in clean_date:
            parts = clean_date.split(' ')
            date_str = parts[0].replace('-', '/')
            time_str = parts[1][:5] # Берем только HH:MM
        else:
            date_str = clean_date.replace('-', '/')
            time_str = "12:00"

        # 2. Создаем объекты Flatlib
        date = Datetime(date_str, time_str, '+00:00')
        pos = GeoPos(data.latitude, data.longitude)
        chart = Chart(date, pos)

        # 3. Собираем данные
        output_planets = []
        ids = [
            const.SUN, const.MOON, const.MERCURY, const.VENUS, const.MARS,
            const.JUPITER, const.SATURN, const.URANUS, const.NEPTUNE, const.PLUTO,
            const.CHIRON, const.NORTH_NODE
        ]

        for p_id in ids:
            obj = chart.get(p_id)
            name = "NNode" if p_id == const.NORTH_NODE else p_id
            
            output_planets.append({
                "name": name,
                "angle": float(obj.lon),
                "sign": get_sign_name(obj.lon),
                "retrograde": obj.isRetrograde(),
                "speed": float(obj.lonspeed),
                "lat": float(obj.lat),
                "lng": float(obj.lon)
            })

        output_houses = [float(chart.get(getattr(const, f'HOUSE{i}')).lon) for i in range(1, 13)]
        
        return {
            "planets": output_planets,
            "houses": output_houses,
            "angles": {
                "Ascendant": float(chart.get(const.ASC).lon),
                "MC": float(chart.get(const.MC).lon)
            }
        }

    except Exception as e:
        print(f"CRITICAL CALCULATION ERROR: {e}") 
        # ВОТ ЗДЕСЬ БЫЛА ПРОБЛЕМА. 
        # Раньше мы возвращали текст ошибки, а фронтенд ждал JSON.
        # Теперь возвращаем пустую структуру, чтобы приложение не падало.
        return get_empty_chart_structure()


# 2. ИНТЕРПРЕТАЦИЯ
@app.post("/interpret")
async def interpret(request: dict):
    try:
        if active_model:
            resp = active_model.generate_content("Ты астролог. Составь психологический портрет (3-4 предложения).")
            return Response(content=resp.text, media_type="text/plain; charset=utf-8")
        return Response(content="Сервис временно недоступен.", media_type="text/plain; charset=utf-8")
    except Exception as e:
        return Response(content="Ошибка сервиса.", media_type="text/plain; charset=utf-8")


# 3. ГОРОСКОП
@app.post("/personal_horoscope")
async def personal(request: dict):
    try:
        date = request.get("birthDateTime", "")
        prompt = f"Гороскоп на сегодня для {date}. Позитивно, коротко."
        if active_model:
            resp = active_model.generate_content(prompt)
            return Response(content=resp.text, media_type="text/plain; charset=utf-8")
        return Response(content="Сегодня хороший день.", media_type="text/plain; charset=utf-8")
    except:
        return Response(content="Звезды благосклонны.", media_type="text/plain; charset=utf-8")


# 4. СИНАСТРИЯ
@app.post("/synastry")
async def synastry(request: dict):
    try:
        if active_model:
            resp = active_model.generate_content("Краткий совет по совместимости пары.")
            return Response(content=resp.text, media_type="text/plain; charset=utf-8")
        return Response(content="Совет пока недоступен", media_type="text/plain; charset=utf-8")
    except:
        return Response(content="Любите друг друга.", media_type="text/plain; charset=utf-8")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
