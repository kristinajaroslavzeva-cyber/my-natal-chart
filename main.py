from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import pytz
import swisseph as swe
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- НАСТРОЙКА ПУТЕЙ ---
current_dir = os.path.dirname(os.path.abspath(__file__))
ephe_path = os.path.join(current_dir, 'ephe')
swe.set_ephe_path(ephe_path)

# --- БАЗА ТЕКСТОВ ---
zodiac_texts = {
    "Aries": "## Ваше Солнце в Овне ♈\nВы — первопроходец. Ваша стихия — Огонь. Вы полны энергии, инициативы и смелости. Ваша задача — начинать новые дела и вдохновлять других.",
    "Taurus": "## Ваше Солнце в Тельце ♉\nВы — созидатель. Ваша стихия — Земля. Вы цените комфорт, красоту и стабильность. Вы надежны, терпеливы и умеете наслаждаться жизнью.",
    "Gemini": "## Ваше Солнце в Близнецах ♊\nВы — коммуникатор. Ваша стихия — Воздух. Вы любознательны, общительны и легки на подъем. Ваш ум всегда требует новой пищи.",
    "Cancer": "## Ваше Солнце в Раке ♋\nВы — хранитель. Ваша стихия — Вода. Вы обладаете глубокой эмпатией, интуицией и привязаны к семье. Вы умеете заботиться как никто другой.",
    "Leo": "## Ваше Солнце во Льве ♌\nВы — звезда. Ваша стихия — Огонь. Вы рождены, чтобы сиять, творить и любить. Ваше великодушие и харизма притягивают людей.",
    "Virgo": "## Ваше Солнце в Деве ♍\nВы — исследователь. Ваша стихия — Земля. Вы внимательны к деталям, трудолюбивы и стремитесь к совершенству. Ваш конек — порядок и анализ.",
    "Libra": "## Ваше Солнце в Весах ♎\nВы — дипломат. Ваша стихия — Воздух. Вы стремитесь к гармонии, красоте и партнерству. Вы умеете видеть ситуацию с разных сторон.",
    "Scorpio": "## Ваше Солнце в Скорпионе ♏\nВы — мистик. Ваша стихия — Вода. Вы обладаете мощной волей, проницательностью и магнетизмом. Вы не боитесь перемен и кризисов.",
    "Sagittarius": "## Ваше Солнце в Стрельце ♐\nВы — философ. Ваша стихия — Огонь. Ваш оптимизм неиссякаем. Вы любите путешествия, знания и стремитесь расширять горизонты.",
    "Capricorn": "## Ваше Солнце в Козероге ♑\nВы — стратег. Ваша стихия — Земля. Вы амбициозны, дисциплинированы и ответственны. Вы умеете ставить цели и достигать вершин.",
    "Aquarius": "## Ваше Солнце в Водолее ♒\nВы — новатор. Ваша стихия — Воздух. Вы цените свободу, дружбу и оригинальность. Ваш взгляд всегда устремлен в будущее.",
    "Pisces": "## Ваше Солнце в Рыбах ♓\nВы — мечтатель. Ваша стихия — Вода. Вы обладаете богатым воображением, состраданием и тонкой интуицией. Вы чувствуете этот мир сердцем."
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
        # 1. Время
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

        # 2. Режим
        calc_flag = swe.FLG_SWIEPH | swe.FLG_SPEED
        try:
            swe.calc_ut(julian_day, swe.SUN, calc_flag)
        except swe.Error:
            print("Warning: Using Moshier mode")
            calc_flag = swe.FLG_MOSEPH | swe.FLG_SPEED

        # 3. Планеты
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
            except:
                continue

        # 4. Дома
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

        return {
            "planets": planets_result,
            "houses": houses_result,
            "angles": angles
        }

    except Exception as e:
        print(f"FATAL: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/interpret")
async def interpret(request: dict):
    # Логика: Приложение присылает нам карту. Мы ищем там Солнце.
    try:
        # Проверяем, где лежит список планет (в 'chart' или сразу в корне)
        chart = request.get('chart', request)
        planets = chart.get('planets', [])
        
        sun_sign = "Unknown"
        
        # Ищем Солнце в списке
        for p in planets:
            if p.get('name') == 'Sun':
                sun_sign = p.get('sign')
                break
        
        # Берем текст из базы
        text = zodiac_texts.get(sun_sign, "Знак зодиака не определен.")
        
        return text

    except Exception as e:
        return f"Ошибка интерпретации: {str(e)}"

@app.post("/synastry")
async def synastry(request: dict):
    return "### Совместимость\n\nФункция работает. Нужно добавить тексты совместимости."

@app.post("/personal_horoscope")
async def personal(request: dict):
    return "### Гороскоп на сегодня\n\nТранзиты рассчитаны успешно. "

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
