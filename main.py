from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import os

# --- ПОПЫТКА ИМПОРТА FLATLIB ---
try:
    from flatlib.datetime import Datetime
    from flatlib.geopos import GeoPos
    from flatlib.chart import Chart
    from flatlib import const
    FLATLIB_INSTALLED = True
except ImportError:
    FLATLIB_INSTALLED = False
    print("ВНИМАНИЕ: flatlib не установлен. Будут использоваться заглушки.")

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

safety_settings = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

active_model = None
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            active_model = genai.GenerativeModel(m.name)
            break
except Exception as e:
    print(f"Model selection error: {e}")

if not active_model:
    active_model = genai.GenerativeModel('gemini-1.5-flash')


class BirthData(BaseModel):
    birthDateTime: str
    latitude: float
    longitude: float
    zoneId: str

# --- ФУНКЦИЯ-СПАСАТЕЛЬ (БЕЗОПАСНЫЕ ДАННЫЕ) ---
# Если реальный расчет падает, отдаем это, чтобы приложение НЕ КРАШИЛОСЬ
def get_safe_fallback_data():
    mock_planets = []
    # Стандартный набор, чтобы круг отрисовался
    names = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto", "Chiron", "Lilith", "NNode"]
    for i, name in enumerate(names):
        mock_planets.append({
            "name": name,
            "angle": float(i * 30), # Просто расставим по кругу
            "sign": "Aries",
            "retrograde": False,
            "speed": 0.5,
            "lat": 0.0,
            "lng": float(i * 30),
            "house": 1
        })
    return {
        "planets": mock_planets,
        "houses": [float(i*30) for i in range(12)],
        "angles": {"Ascendant": 0.0, "MC": 90.0}
    }

def get_sign_name(lon):
    signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    idx = int(lon // 30)
    return signs[idx % 12]

# 1. РАСЧЕТ КАРТЫ (REAL + FALLBACK)
@app.post("/calculate")
async def calculate_chart(data: BirthData):
    # Если библиотеки нет, сразу отдаем безопасные данные, но не ошибку!
    if not FLATLIB_INSTALLED:
        return get_safe_fallback_data()

    try:
        # Пытаемся распарсить дату. Форматы бывают разные (2023-01-01T12:00 или 2023-01-01 12:00)
        dt_str = data.birthDateTime.replace('T', ' ')
        if ' ' in dt_str:
            date_raw = dt_str.split(' ')[0].replace('-', '/')
            time_raw = dt_str.split(' ')[1][:5] # HH:MM
        else:
            # Если пришла только дата без времени
            date_raw = dt_str.replace('-', '/')
            time_raw = "12:00"

        date = Datetime(date_raw, time_raw, '+00:00')
        pos = GeoPos(data.latitude, data.longitude)
        chart = Chart(date, pos)

        planets_to_calc = [
            const.SUN, const.MOON, const.MERCURY, const.VENUS, const.MARS,
            const.JUPITER, const.SATURN, const.URANUS, const.NEPTUNE, const.PLUTO,
            const.CHIRON, const.NORTH_NODE
        ]

        output_planets = []
        for p_id in planets_to_calc:
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
        print(f"CRITICAL ERROR in calculation: {e}")
        # ВАЖНО: Если произошла ошибка (неверная дата и т.д.),
        # мы возвращаем безопасные данные, чтобы приложение НЕ УПАЛО.
        return get_safe_fallback_data()


# 2. ИНТЕРПРЕТАЦИЯ (GEMINI - ИИ)
@app.post("/interpret")
async def interpret(request: dict):
    try:
        if active_model:
            prompt = "Ты астролог. Дай краткий психологический портрет личности (3-4 предложения). Без форматирования."
            resp = active_model.generate_content(prompt)
            return Response(content=resp.text, media_type="text/plain; charset=utf-8")
        return Response(content="Астролог думает...", media_type="text/plain; charset=utf-8")
    except Exception as e:
        return Response(content="Энергия звезд недоступна.", media_type="text/plain; charset=utf-8")


# 3. ГОРОСКОП (GEMINI - ИИ)
@app.post("/personal_horoscope")
async def personal(request: dict):
    try:
        birth_date = request.get("birthDateTime", "")
        prompt = f"Гороскоп на сегодня для рожденного {birth_date}. Позитивно, 2 предложения."
        
        if active_model:
            resp = active_model.generate_content(prompt)
            return Response(content=resp.text, media_type="text/plain; charset=utf-8")
        
        return Response(content="Сегодня хороший день.", media_type="text/plain; charset=utf-8")
    except Exception as e:
        return Response(content="Звезды отдыхают.", media_type="text/plain; charset=utf-8")


# 4. СИНАСТРИЯ (GEMINI - ИИ)
@app.post("/synastry")
async def synastry(request: dict):
    try:
        if active_model:
            resp = active_model.generate_content("Краткий совет по совместимости пары.")
            return Response(content=resp.text, media_type="text/plain; charset=utf-8")
        return Response(content="Совет пока недоступен", media_type="text/plain; charset=utf-8")
    except Exception as e:
        return Response(content="Ошибка сервиса.", media_type="text/plain; charset=utf-8")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
