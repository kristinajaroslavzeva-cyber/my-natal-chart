from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import pytz
import swisseph as swe
import os

app = FastAPI()

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- НАСТРОЙКА ЭФЕМЕРИД ---
current_dir = os.path.dirname(os.path.abspath(__file__))
ephe_path = os.path.join(current_dir, 'ephe')
swe.set_ephe_path(ephe_path)

# Простая база текстов (можно расширять)
zodiac_texts = {
    "Aries": "Вы — Овен ♈. Стихия — Огонь. Вы полны энергии, инициативны и прямолинейны.",
    "Taurus": "Вы — Телец ♉. Стихия — Земля. Вы цените комфорт, стабильность и красоту.",
    "Gemini": "Вы — Близнецы ♊. Стихия — Воздух. Вы общительны и любознательны.",
    "Cancer": "Вы — Рак ♋. Стихия — Вода. Вы эмоциональны и заботливы.",
    "Leo": "Вы — Лев ♌. Стихия — Огонь. Вы рождены, чтобы сиять и вести за собой.",
    "Virgo": "Вы — Дева ♍. Стихия — Земля. Вы внимательны к деталям и любите порядок.",
    "Libra": "Вы — Весы ♎. Стихия — Воздух. Вы стремитесь к гармонии и партнерству.",
    "Scorpio": "Вы — Скорпион ♏. Стихия — Вода. Вы обладаете мощной интуицией.",
    "Sagittarius": "Вы — Стрелец ♐. Стихия — Огонь. Вы оптимист и философ.",
    "Capricorn": "Вы — Козерог ♑. Стихия — Земля. Вы амбициозны и дисциплинированы.",
    "Aquarius": "Вы — Водолей ♒. Стихия — Воздух. Вы оригинальны и независимы.",
    "Pisces": "Вы — Рыбы ♓. Стихия — Вода. Вы мечтательны и сострадательны."
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
        # Проверка путей перед расчетом
        if not os.path.exists(ephe_path):
            raise Exception(f"CRITICAL ERROR: Ephemeris folder not found at {ephe_path}")

        # 1. Подготовка времени (UTC)
        local_dt = datetime.fromisoformat(data.birthDateTime)
        try:
            tz = pytz.timezone(data.zoneId)
            if local_dt.tzinfo is None:
                local_dt = tz.localize(local_dt)
        except:
            local_dt = local_dt.replace(tzinfo=pytz.UTC)
        
        utc_dt = local_dt.astimezone(pytz.utc)

        # 2. Юлианский день
        julian_day = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, 
                                utc_dt.hour + utc_dt.minute/60.0 + utc_dt.second/3600.0)

        # 3. Объекты
        bodies = {
            "Sun": swe.SUN, "Moon": swe.MOON, "Mercury": swe.MERCURY, 
            "Venus": swe.VENUS, "Mars": swe.MARS, "Jupiter": swe.JUPITER, 
            "Saturn": swe.SATURN, "Uranus": swe.URANUS, "Neptune": swe.NEPTUNE, 
            "Pluto": swe.PLUTO, "Chiron": swe.CHIRON, 
            "True Node": swe.TRUE_NODE, "Lilith": swe.MEAN_APOG
        }

        planets_result = []

        # 4. Расчет планет
        for name, pid in bodies.items():
            res = swe.calc_ut(julian_day, pid, swe.FLG_SWIEPH + swe.FLG_SPEED)
            coords = res[0]
            lon = coords[0]
            speed = coords[3]

            planets_result.append({
                "name": name,
                "eclipticLongitude": lon,
                "sign": get_sign(lon),
                "signDegree": lon % 30,
                "isRetrograde": speed < 0
            })

        # 5. Расчет домов
        cusps, ascmc = swe.houses(julian_day, data.latitude, data.longitude, b'P')
        houses_result = []
        
        for i in range(1, 13):
            h_lon = cusps[i]
            houses_result.append({
                "houseNumber": i,
                "eclipticLongitude": h_lon,
                "sign": get_sign(h_lon),
                "signDegree": h_lon % 30
            })

        return {
            "planets": planets_result,
            "houses": houses_result,
            "angles": {"Ascendant": ascmc[0], "MC": ascmc[1]}
        }

    except Exception as e:
        print(f"Server Error: {e}")
        # Возвращаем текст ошибки, чтобы видеть его в приложении
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")

@app.post("/interpret")
async def interpret(request: dict):
    # Пытаемся определить знак по данным, если они есть
    # Но пока возвращаем общий ответ + текст знака, если он передан
    return "### Интерпретация (Сервер)\n\nДанные успешно получены с сервера. Тексты интерпретации загружены."

@app.post("/synastry")
async def synastry(request: dict):
    return "### Синастрия\n\nСервер готов к расчету совместимости."

@app.post("/personal_horoscope")
async def personal(request: dict):
    return "### Ваш гороскоп\n\nПерсональный прогноз на сегодня (Сервер)."

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
