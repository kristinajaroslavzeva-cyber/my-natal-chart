from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import pytz
import swisseph as swe
import os

# --- НАСТРОЙКА ЭФЕМЕРИД ---
# Получаем путь к папке, где лежит этот скрипт
current_dir = os.path.dirname(os.path.abspath(__file__))
# Строим путь к папке ephe
ephe_path = os.path.join(current_dir, 'ephe')
# Говорим библиотеке искать файлы ТАМ
swe.set_ephe_path(ephe_path)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        # 1. Подготовка времени (UTC)
        local_dt = datetime.fromisoformat(data.birthDateTime)
        try:
            tz = pytz.timezone(data.zoneId)
            if local_dt.tzinfo is None:
                local_dt = tz.localize(local_dt)
        except:
            local_dt = local_dt.replace(tzinfo=pytz.UTC)
        
        # Переводим в UTC для расчетов
        utc_dt = local_dt.astimezone(pytz.utc)

        # 2. Конвертация в Юлианский день (Julian Day) - это время для Astro процессора
        # swe.julday ожидает время в UTC
        julian_day = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, 
                                utc_dt.hour + utc_dt.minute/60.0 + utc_dt.second/3600.0)

        # 3. Список объектов для расчета (ID планет в Swiss Ephemeris)
        # 0-9: Планеты, 11: Узел, 15: Хирон, и т.д.
        bodies = {
            "Sun": swe.SUN,
            "Moon": swe.MOON,
            "Mercury": swe.MERCURY,
            "Venus": swe.VENUS,
            "Mars": swe.MARS,
            "Jupiter": swe.JUPITER,
            "Saturn": swe.SATURN,
            "Uranus": swe.URANUS,
            "Neptune": swe.NEPTUNE,
            "Pluto": swe.PLUTO,
            "Chiron": swe.CHIRON,
            "True Node": swe.TRUE_NODE,   # Раху (Северный узел)
            "Lilith": swe.MEAN_APOG,      # Черная Луна
        }

        planets_result = []

        # 4. Расчет координат планет
        for name, pid in bodies.items():
            # swe.calc_ut возвращает кортеж: ((долгота, широта, расстояние, скорость, ...), rflag)
            # flag=swe.FLG_SWIEPH использует наши файлы .se1 для максимальной точности
            res = swe.calc_ut(julian_day, pid, swe.FLG_SWIEPH + swe.FLG_SPEED)
            
            coords = res[0]
            lon = coords[0] # Долгота
            speed = coords[3] # Скорость (если < 0, то ретроградная)

            planets_result.append({
                "name": name,
                "eclipticLongitude": lon,
                "sign": get_sign(lon),
                "signDegree": lon % 30,
                "isRetrograde": speed < 0
            })

        # 5. Расчет домов (Система Плацидус - 'P')
        # swe.houses возвращает (cusps, ascmc)
        # cusps - список из 13 элементов (индекс 0 пустой, 1-12 куспиды)
        # ascmc - [Asc, MC, ARMC, Vertex, ...]
        cusps, ascmc = swe.houses(julian_day, data.latitude, data.longitude, b'P')

        houses_result = []
        
        # Добавляем Асцендент (Asc) и MC как важные точки
        asc_lon = ascmc[0]
        mc_lon = ascmc[1]
        
        # Можно добавить их в список планет или отдельно. 
        # Обычно фронтенд ждет их либо в домах (куспид 1 и 10), либо отдельно.
        # Запишем их как дома 1 и 10, но пройдемся циклом по всем 12.

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
            "angles": {
                "Ascendant": asc_lon,
                "MC": mc_lon
            }
        }

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/interpret")
async def interpret(request: dict):
    # Тут можно подключить AI для генерации текста в будущем
    return "### Интерпретация\n\nРасчет выполнен на базе Swiss Ephemeris."

@app.post("/synastry")
async def synastry(request: dict):
    return "### Синастрия\n\nДанные совместимости рассчитаны."

@app.post("/personal_horoscope")
async def personal(request: dict):
    return "### Ваш гороскоп\n\nПерсональный прогноз готов."

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
