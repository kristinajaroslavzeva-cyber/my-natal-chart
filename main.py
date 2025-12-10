from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import pytz
import swisseph as swe
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

# --- 1. НАСТРОЙКА ЭФЕМЕРИД (МАТЕМАТИКА) ---
current_dir = os.path.dirname(os.path.abspath(__file__))
ephe_path = os.path.join(current_dir, 'ephe')
swe.set_ephe_path(ephe_path)

# --- 2. НАСТРОЙКА ИИ (ЛИТЕРАТУРА) ---
# ВСТАВЬ СЮДА КЛЮЧ
GEMINI_API_KEY = "AIzaSyAObmU1VR5hRc-bCcbYyfanS_6QQ2vr1ks" 
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

class BirthData(BaseModel):
    birthDateTime: str
    latitude: float
    longitude: float
    zoneId: str

def get_sign(longitude):
    signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", 
             "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    return signs[int(longitude / 30) % 12]

# --- РАСЧЕТ КООРДИНАТ (ЭФЕМЕРИДЫ) ---
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
        # Вернем пустую структуру при ошибке, чтобы приложение не падало
        return {"planets": [], "houses": [], "angles": {"Ascendant": 0.0, "MC": 0.0}}

# --- ИНТЕРПРЕТАЦИЯ (ТОЛЬКО ИИ) ---
@app.post("/interpret")
async def interpret(request: dict):
    # 1. Берем данные от эфемерид
    chart = request.get('chart', request)
    planets = chart.get('planets', [])
    
    prompt_data = ""
    for p in planets:
        prompt_data += f"{p['name']} в знаке {p['sign']}; "

    # 2. Отправляем в ИИ
    try:
        full_prompt = (
            f"Ты профессиональный астролог. Вот данные натальной карты: {prompt_data}. "
            "Напиши подробный, интересный, живой психологический портрет человека. "
            "Не используй Markdown, звездочки или решетки. Пиши просто текстом."
        )
        resp = model.generate_content(full_prompt)
        result_text = resp.text
    except Exception as e:
        result_text = f"Ошибка ИИ: {str(e)}. Проверь ключ."

    # 3. Отдаем ЧИСТЫЙ ТЕКСТ (без кавычек и JSON)
    return Response(content=result_text, media_type="text/plain")

# --- ГОРОСКОП НА СЕГОДНЯ (ТОЛЬКО ИИ) ---
@app.post("/personal_horoscope")
async def personal(request: dict):
    try:
        resp = model.generate_content(
            "Напиши персональный гороскоп на сегодня. "
            "Раздели на Любовь, Карьеру и Совет. "
            "Не используй Markdown и звездочки. Пиши просто текстом."
        )
        result_text = resp.text
    except Exception as e:
        result_text = f"Ошибка ИИ при генерации гороскопа: {str(e)}"

    # Отдаем ЧИСТЫЙ ТЕКСТ
    return Response(content=result_text, media_type="text/plain")

# --- СИНАСТРИЯ (ТОЛЬКО ИИ) ---
@app.post("/synastry")
async def synastry(request: dict):
    # Для теста синастрии пока просто попросим общий совет
    try:
        resp = model.generate_content("Напиши короткий совет по совместимости для пары. Просто текст.")
        result_text = resp.text
    except Exception as e:
        result_text = "Ошибка ИИ."

    return Response(content=result_text, media_type="text/plain")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
