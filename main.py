from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import pytz
import swisseph as swe
import os
import random

# --- ИНИЦИАЛИЗАЦИЯ ИИ ---
try:
    import google.generativeai as genai
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

current_dir = os.path.dirname(os.path.abspath(__file__))
ephe_path = os.path.join(current_dir, 'ephe')
swe.set_ephe_path(ephe_path)

# ВСТАВЬ КЛЮЧ
GEMINI_API_KEY = "AIzaSyAObmU1VR5hRc-bCcbYyfanS_6QQ2vr1ks"

if AI_AVAILABLE:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
    except:
        AI_AVAILABLE = False

# --- БАЗА ТЕКСТОВ (ЧИСТЫЙ ТЕКСТ БЕЗ ЗВЕЗДОЧЕК) ---
zodiac_detailed = {
    "Aries": "ВАШ ЗНАК — ОВЕН. Вы первопроходец. Ваша энергия безгранична. СИЛЬНЫЕ СТОРОНЫ: Смелость, лидерство. КАРМИЧЕСКАЯ ЗАДАЧА: Учиться терпению.",
    "Taurus": "ВАШ ЗНАК — ТЕЛЕЦ. Вы скала надежности. Вы цените комфорт. СИЛЬНЫЕ СТОРОНЫ: Упорство, стабильность. КАРМИЧЕСКАЯ ЗАДАЧА: Не бояться перемен.",
    "Gemini": "ВАШ ЗНАК — БЛИЗНЕЦЫ. Ваш ум быстр. Вы вечный ученик. СИЛЬНЫЕ СТОРОНЫ: Интеллект, гибкость. КАРМИЧЕСКАЯ ЗАДАЧА: Обрести фокус.",
    "Cancer": "ВАШ ЗНАК — РАК. Вы живете сердцем. Семья — ваша крепость. СИЛЬНЫЕ СТОРОНЫ: Эмпатия, забота. КАРМИЧЕСКАЯ ЗАДАЧА: Отпустить прошлое.",
    "Leo": "ВАШ ЗНАК — ЛЕВ. Вы рождены сиять. Ваша харизма притягивает. СИЛЬНЫЕ СТОРОНЫ: Уверенность, щедрость. КАРМИЧЕСКАЯ ЗАДАЧА: Служить другим.",
    "Virgo": "ВАШ ЗНАК — ДЕВА. Вы видите совершенство в деталях. СИЛЬНЫЕ СТОРОНЫ: Трудолюбие, логика. КАРМИЧЕСКАЯ ЗАДАЧА: Перестать критиковать себя.",
    "Libra": "ВАШ ЗНАК — ВЕСЫ. Вы создаете гармонию. СИЛЬНЫЕ СТОРОНЫ: Вкус, дипломатия. КАРМИЧЕСКАЯ ЗАДАЧА: Обрести стержень.",
    "Scorpio": "ВАШ ЗНАК — СКОРПИОН. Вы обладаете магией и волей. СИЛЬНЫЕ СТОРОНЫ: Интуиция, сила. КАРМИЧЕСКАЯ ЗАДАЧА: Прощать обиды.",
    "Sagittarius": "ВАШ ЗНАК — СТРЕЛЕЦ. Вы целитесь в звезды. СИЛЬНЫЕ СТОРОНЫ: Оптимизм, мудрость. КАРМИЧЕСКАЯ ЗАДАЧА: Внимание к деталям.",
    "Capricorn": "ВАШ ЗНАК — КОЗЕРОГ. Вы строите успех. СИЛЬНЫЕ СТОРОНЫ: Дисциплина, амбиции. КАРМИЧЕСКАЯ ЗАДАЧА: Открыть сердце.",
    "Aquarius": "ВАШ ЗНАК — ВОДОЛЕЙ. Вы новатор и бунтарь. СИЛЬНЫЕ СТОРОНЫ: Свобода, оригинальность. КАРМИЧЕСКАЯ ЗАДАЧА: Теплота к близким.",
    "Pisces": "ВАШ ЗНАК — РЫБЫ. Вы живете в мире грез. СИЛЬНЫЕ СТОРОНЫ: Фантазия, милосердие. КАРМИЧЕСКАЯ ЗАДАЧА: Связь с реальностью."
}

class BirthData(BaseModel):
    birthDateTime: str
    latitude: float
    longitude: float
    zoneId: str

def get_sign(longitude):
    signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", 
             "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    return signs[int(longitude / 30) % 12]

# --- РАСЧЕТ ---
@app.post("/calculate")
async def calculate_chart(data: BirthData):
    try:
        local_dt = datetime.fromisoformat(data.birthDateTime)
        try:
            tz = pytz.timezone(data.zoneId)
            if local_dt.tzinfo is None: local_dt = tz.localize(local_dt)
        except: local_dt = local_dt.replace(tzinfo=pytz.UTC)
        
        utc_dt = local_dt.astimezone(pytz.utc)
        julian_day = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, 
                                utc_dt.hour + utc_dt.minute/60.0 + utc_dt.second/3600.0)

        calc_flag = swe.FLG_SWIEPH | swe.FLG_SPEED
        try: swe.calc_ut(julian_day, swe.SUN, calc_flag)
        except swe.Error: calc_flag = swe.FLG_MOSEPH | swe.FLG_SPEED

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
                if not coords: continue
                planets_result.append({
                    "name": name, "eclipticLongitude": coords[0],
                    "sign": get_sign(coords[0]), "signDegree": coords[0] % 30,
                    "isRetrograde": coords[3] < 0 if len(coords) >= 4 else False
                })
            except: continue

        try:
            cusps, ascmc = swe.houses(julian_day, data.latitude, data.longitude, b'P')
            houses_result = []
            if len(cusps) >= 13:
                for i in range(1, 13):
                    houses_result.append({
                        "houseNumber": i, "eclipticLongitude": cusps[i],
                        "sign": get_sign(cusps[i]), "signDegree": cusps[i] % 30
                    })
            angles = {"Ascendant": ascmc[0] if ascmc else 0.0, "MC": ascmc[1] if ascmc and len(ascmc) > 1 else 0.0}
        except:
             houses_result = []; angles = {"Ascendant": 0.0, "MC": 0.0}

        return {"planets": planets_result, "houses": houses_result, "angles": angles}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- ИНТЕРПРЕТАЦИЯ (Возвращает ЧИСТЫЙ ТЕКСТ) ---
@app.post("/interpret")
async def interpret(request: dict):
    try:
        chart = request.get('chart', request)
        planets = chart.get('planets', [])
        sun_sign = "Aries"
        
        prompt_data = ""
        for p in planets:
            if p.get('name') == 'Sun': sun_sign = p.get('sign')
            prompt_data += f"{p['name']}: {p['sign']}; "

        if AI_AVAILABLE:
            try:
                full_prompt = (
                    f"Ты астролог. Данные: {prompt_data}. "
                    "Напиши психологический портрет. "
                    "НЕ ИСПОЛЬЗУЙ жирный шрифт, звездочки или решетки. Просто текст."
                )
                resp = model.generate_content(full_prompt)
                if resp.text: return resp.text # ВОЗВРАЩАЕМ ПРОСТО ТЕКСТ
            except: pass
        
        return zodiac_detailed.get(sun_sign, "Знак зодиака не определен.")

    except Exception as e:
        return f"Ошибка: {str(e)}"

# --- ГОРОСКОП (Возвращает ЧИСТЫЙ ТЕКСТ) ---
@app.post("/personal_horoscope")
async def personal(request: dict):
    if AI_AVAILABLE:
        try:
            resp = model.generate_content("Напиши гороскоп на сегодня. Без форматирования, просто текст.")
            if resp.text: return resp.text
        except: pass

    return "ВАШ ПРОГНОЗ. Сегодня день открытий. Слушайте интуицию. В любви возможен сюрприз. На работе ваши усилия заметят."

# --- СИНАСТРИЯ (Возвращает ЧИСТЫЙ ТЕКСТ) ---
@app.post("/synastry")
async def synastry(request: dict):
    return "СОВМЕСТИМОСТЬ. Вы отлично дополняете друг друга. Между вами глубокая связь. Совет: учитесь слушать партнера."

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
