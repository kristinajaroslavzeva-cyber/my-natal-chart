from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import os
import logging

# Настройка логов
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- БЕЗОПАСНЫЙ ИМПОРТ FLATLIB ---
FLATLIB_INSTALLED = False
try:
    # Пытаемся импортировать. Если Python 3.13, здесь вылетит ошибка
    import flatlib
    from flatlib.datetime import Datetime
    from flatlib.geopos import GeoPos
    from flatlib.chart import Chart
    from flatlib import const
    FLATLIB_INSTALLED = True
    logger.info("Flatlib successfully imported.")
except ImportError as e:
    logger.error(f"Flatlib import failed: {e}")
except Exception as e:
    logger.error(f"Flatlib crashed on import (likely Python version issue): {e}")

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

# --- ЗАГЛУШКА (ЕСЛИ БИБЛИОТЕКА СЛОМАНА) ---
def get_fallback_chart():
    logger.warning("Using fallback chart data")
    planets = []
    names = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto", "Chiron", "Lilith", "NNode"]
    
    for i, name in enumerate(names):
        planets.append({
            "name": name,
            "angle": float((i * 30) % 360),
            "sign": "Aries", 
            "retrograde": False,
            "speed": 0.5,
            "lat": 0.0,
            "lng": float((i * 30) % 360),
            "house": 1
        })
        
    houses = [float(i * 30) for i in range(12)]
    
    return {
        "planets": planets,
        "houses": houses,
        "angles": {"Ascendant": 0.0, "MC": 90.0}
    }

def get_sign_name(lon):
    signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    return signs[int(lon // 30) % 12]


class BirthData(BaseModel):
    birthDateTime: str
    latitude: float
    longitude: float
    zoneId: str


# 1. РАСЧЕТ КАРТЫ
@app.post("/calculate")
async def calculate_chart(data: BirthData):
    # Если импорт не сработал (например, из-за Python 3.13), отдаем заглушку
    if not FLATLIB_INSTALLED:
        return get_fallback_chart()

    try:
        # Парсинг даты
        dt_str = data.birthDateTime.replace('T', ' ').replace('Z', '')
        if ' ' in dt_str:
            parts = dt_str.split(' ')
            date_raw = parts[0].replace('-', '/')
            time_raw = parts[1][:5]
        else:
            date_raw = dt_str.replace('-', '/')
            time_raw = "12:00"

        date = Datetime(date_raw, time_raw, '+00:00')
        pos = GeoPos(data.latitude, data.longitude)
        chart = Chart(date, pos)

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
        logger.error(f"Calculation error: {e}")
        # Если реальный расчет упал, отдаем заглушку, чтобы приложение не падало
        return get_fallback_chart()


# 2. ИНТЕРПРЕТАЦИЯ
@app.post("/interpret")
async def interpret(request: dict):
    # Инициализация модели внутри функции на случай сбоев при старте
    model = active_model
    if not model:
        return Response(content="Сервис временно недоступен", media_type="text/plain")
        
    try:
        resp = model.generate_content("Ты астролог. Составь психологический портрет (3-4 предложения).")
        return Response(content=resp.text, media_type="text/plain; charset=utf-8")
    except Exception as e:
        return Response(content="Энергия звезд недоступна.", media_type="text/plain; charset=utf-8")


# 3. ГОРОСКОП
@app.post("/personal_horoscope")
async def personal(request: dict):
    model = active_model
    if not model:
         return Response(content="Удачного дня!", media_type="text/plain")
         
    try:
        date = request.get("birthDateTime", "")
        prompt = f"Гороскоп на сегодня для рожденного {date}. Позитивно."
        resp = model.generate_content(prompt)
        return Response(content=resp.text, media_type="text/plain; charset=utf-8")
    except:
        return Response(content="Все будет хорошо.", media_type="text/plain; charset=utf-8")


# 4. СИНАСТРИЯ
@app.post("/synastry")
async def synastry(request: dict):
    model = active_model
    if not model:
        return Response(content="Совет недоступен", media_type="text/plain")
        
    try:
        resp = model.generate_content("Дай краткий совет по совместимости.")
        return Response(content=resp.text, media_type="text/plain; charset=utf-8")
    except:
        return Response(content="Любовь победит.", media_type="text/plain; charset=utf-8")


# --- ЗАПУСК ---
active_model = None
if __name__ == "__main__":
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                active_model = genai.GenerativeModel(m.name)
                break
        if not active_model:
             active_model = genai.GenerativeModel('gemini-1.5-flash')
    except:
        pass

    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
