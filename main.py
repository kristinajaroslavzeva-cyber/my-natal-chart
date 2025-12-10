from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import pytz
import swisseph as swe
import os
import random

# Попробуем подключить ИИ, но если библиотеки нет - не падаем
try:
    import google.generativeai as genai
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    print("WARNING: google-generativeai library not found.")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- НАСТРОЙКИ ---
current_dir = os.path.dirname(os.path.abspath(__file__))
ephe_path = os.path.join(current_dir, 'ephe')
swe.set_ephe_path(ephe_path)

# ВСТАВЬ СЮДА СВОЙ КЛЮЧ (В КАВЫЧКАХ!)
GEMINI_API_KEY = "AIzaSyAObmU1VR5hRc-bCcbYyfanS_6QQ2vr1ks"  

if AI_AVAILABLE:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        print(f"AI Config Error: {e}")
        AI_AVAILABLE = False

# --- ЗАПАСНАЯ БАЗА ТЕКСТОВ (Если ИИ сломается) ---
zodiac_detailed = {
    "Aries": "## ♈ Овен (Запасной текст)\nИИ сейчас недоступен, но звезды говорят, что вы полны энергии!",
    "Taurus": "## ♉ Телец (Запасной текст)\nИИ сейчас отдыхает, но ваша стабильность восхищает.",
    # ... (сюда можно вернуть те длинные тексты, что были раньше)
}

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

@app.post("/calculate")
async def calculate_chart(data: BirthData):
    try:
        local_dt = datetime.fromisoformat(data.birthDateTime)
        try:
            tz = pytz.timezone(data.zoneId)
            if local_dt.tzinfo is None:
                local_dt = tz.localize(local_dt)
        except:
            local_dt = local_dt.replace(tzinfo=pytz.UTC)
        
        utc_dt = local_dt.astimezone(pytz.utc)
        julian_day = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, 
                                utc_dt.hour + utc_dt.minute/60.0 + utc_dt.second/3600.0)

        calc_flag = swe.FLG_SWIEPH | swe.FLG_SPEED
        try:
            swe.calc_ut(julian_day, swe.SUN, calc_flag)
        except swe.Error:
            calc_flag = swe.FLG_MOSEPH | swe.FLG_SPEED

        bodies = {
            "Sun": swe.SUN, "Moon": swe.MOON, "Mercury": swe.MERCURY, 
            "Venus": swe.VENUS, "Mars": swe.MARS, "Jupiter": swe.JUPITER, 
            "Saturn": swe.SATURN, "Uranus": swe.URANUS, "Neptune": swe.NEPTUNE, 
            "Pluto": swe.PLUTO, "Chiron": swe.CHIRON, 
            "True Node": swe.TRUE_NODE, "Lilith": swe.MEAN_APOG
        }

        planets_result = []
        for name, pid in bodies.items():
            try:
                res = swe.calc_ut(julian_day, pid, calc_flag)
                coords = res[0]
                if not coords or len(coords) < 1: continue
                lon = coords[0]
                speed = coords[3] if len(coords) >= 4 else 0.0
                planets_result.append({
                    "name": name,
                    "eclipticLongitude": lon,
                    "sign": get_sign(lon),
                    "signDegree": lon % 30,
                    "isRetrograde": speed < 0
                })
            except: continue

        try:
            cusps, ascmc = swe.houses(julian_day, data.latitude, data.longitude, b'P')
            houses_result = []
            if len(cusps) >= 13:
                for i in range(1, 13):
                    h_lon = cusps[i]
                    houses_result.append({
                        "houseNumber": i,
                        "eclipticLongitude": h_lon,
                        "sign": get_sign(h_lon),
                        "signDegree": h_lon % 30
                    })
            asc = ascmc[0] if ascmc and len(ascmc) >= 1 else 0.0
            mc = ascmc[1] if ascmc and len(ascmc) >= 2 else 0.0
            angles = {"Ascendant": asc, "MC": mc}
        except:
             houses_result = []
             angles = {"Ascendant": 0.0, "MC": 0.0}

        return {"planets": planets_result, "houses": houses_result, "angles": angles}

    except Exception as e:
        print(f"CALC ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/interpret")
async def interpret(request: dict):
    # 1. Достаем данные
    try:
        chart = request.get('chart', request)
        planets = chart.get('planets', [])
        sun_sign = "Unknown"
        prompt_data = ""
        
        for p in planets:
            if p.get('name') == 'Sun':
                sun_sign = p.get('sign')
            prompt_data += f"{p['name']}: {p['sign']} ({p['signDegree']:.1f}°)\n"

        # 2. ПРОБУЕМ ИСПОЛЬЗОВАТЬ ИИ
        if AI_AVAILABLE and GEMINI_API_KEY != "ТВОЙ_КЛЮЧ_ЗДЕСЬ":
            try:
                full_prompt = (
                    f"Ты — астролог. Вот данные: {prompt_data}. "
                    "Напиши краткий гороскоп личности. Используй Markdown."
                )
                response = model.generate_content(full_prompt)
                if response.text:
                    return response.text
            except Exception as e:
                print(f"AI GENERATION FAILED: {e}")
                # Если ИИ упал, не паникуем, идем дальше к запасному тексту
        
        # 3. ЕСЛИ ИИ НЕ СРАБОТАЛ — ОТДАЕМ ЗАПАСНОЙ ТЕКСТ
        print("Using fallback text")
        fallback = zodiac_detailed.get(sun_sign, f"Ваше Солнце в знаке {sun_sign}.")
        return fallback

    except Exception as e:
        return f"Ошибка интерпретации: {str(e)}"

# Остальные функции (synastry, personal) оставь как есть или скопируй из прошлого кода

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
