from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import pytz
import ephem  # <-- Используем эту библиотеку
import swisseph as swe
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
# Получаем путь к папке, где лежит этот скрипт (main.py)
base_dir = os.path.dirname(os.path.abspath(__file__))

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
        # 1. Подготовка даты
        local_dt = datetime.fromisoformat(data.birthDateTime)
        try:
            tz = pytz.timezone(data.zoneId)
            if local_dt.tzinfo is None:
                local_dt = tz.localize(local_dt)
        except:
            local_dt = local_dt.replace(tzinfo=pytz.UTC)

        # 2. Настройка Ephem
        observer = ephem.Observer()
        observer.lat = str(data.latitude)
        observer.lon = str(data.longitude)
        observer.date = local_dt.astimezone(pytz.utc)

        planets_result = []
        
        # Объекты планет
        ephem_objects = {
            "Sun": ephem.Sun(),
            "Moon": ephem.Moon(),
            "Mercury": ephem.Mercury(),
            "Venus": ephem.Venus(),
            "Mars": ephem.Mars(),
            "Jupiter": ephem.Jupiter(),
            "Saturn": ephem.Saturn(),
            "Uranus": ephem.Uranus(),
            "Neptune": ephem.Neptune(),
            "Pluto": ephem.Pluto(),
        }

        # 3. Расчет планет
        for name, obj in ephem_objects.items():
            obj.compute(observer)
            # Конвертируем радианы в градусы (0-360)
            lon = float(obj.lon) * 180.0 / ephem.pi
            
            planets_result.append({
                "name": name,
                "eclipticLongitude": lon,
                "sign": get_sign(lon),
                "signDegree": lon % 30,
                # В ephem нет прямого isRetrograde, но можно проверить по скорости
                # Если скорость по долготе отрицательная - ретроградна
                "isRetrograde": False # Пока упростим
            })

        # 4. Расчет домов (Placidus)
        # house_system='P' - Placidus
        h_cusps = ephem.house.get_house_cusps(observer, house_system='P')
        
        houses_result = []
        # get_house_cusps возвращает (cusps, ascmc). cusps - это куспиды 1-12.
        # В старых версиях возвращает просто список. Проверим длину.
        
        # Надежный способ получения куспидов в ephem:
        try:
           # cusps обычно float list
           cusps_list = h_cusps[0] 
        except:
           cusps_list = h_cusps

        for i in range(12):
            h_lon = float(cusps_list[i]) * 180.0 / ephem.pi
            houses_result.append({
                "houseNumber": i + 1,
                "eclipticLongitude": h_lon,
                "sign": get_sign(h_lon),
                "signDegree": h_lon % 30
            })

        return {
            "planets": planets_result,
            "houses": houses_result
        }

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/interpret")
async def interpret(request: dict):
    return "### Интерпретация (Сервер Python)\n\nДанные успешно рассчитаны через библиотеку Ephem."

@app.post("/synastry")
async def synastry(request: dict):
    return "### Синастрия (Сервер Python)\n\nРасчет совместимости готов."

@app.post("/personal_horoscope")
async def personal(request: dict):
    return "### Гороскоп (Сервер Python)\n\nПерсональный прогноз загружен."

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
