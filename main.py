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

        # 2. Режим (Файлы или Moshier)
        calc_flag = swe.FLG_SWIEPH | swe.FLG_SPEED
        try:
            swe.calc_ut(julian_day, swe.SUN, calc_flag)
        except swe.Error:
            print("WARNING: Files issue. Switching to Moshier.")
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
                
                # ЗАЩИТА №1: Проверяем, есть ли вообще координаты
                if not coords or len(coords) < 1:
                    print(f"Skipping {name}: No coordinates returned")
                    continue

                lon = coords[0]
                
                # ЗАЩИТА №2: Скорость
                if len(coords) >= 4:
                    speed = coords[3]
                else:
                    speed = 0.0

                planets_result.append({
                    "name": name,
                    "eclipticLongitude": lon,
                    "sign": get_sign(lon),
                    "signDegree": lon % 30,
                    "isRetrograde": speed < 0
                })
            except Exception as e:
                print(f"Error planet {name}: {e}")
                continue

        # 4. Дома (ЗДЕСЬ БЫЛА СКРЫТАЯ ОШИБКА)
        try:
            cusps, ascmc = swe.houses(julian_day, data.latitude, data.longitude, b'P')
            
            houses_result = []
            # swe.houses возвращает 13 куспидов (0-й пустой)
            if len(cusps) >= 13:
                for i in range(1, 13):
                    h_lon = cusps[i]
                    houses_result.append({
                        "houseNumber": i,
                        "eclipticLongitude": h_lon,
                        "sign": get_sign(h_lon),
                        "signDegree": h_lon % 30
                    })
            else:
                # Если куспидов нет, создаем пустышки, чтобы фронтенд не падал
                houses_result = []

            # ЗАЩИТА №3: Асцендент и MC
            # ascmc должен содержать [Asc, MC, ARMC, Vertex, ...]
            # Ошибка tuple index out of range часто была ТУТ
            asc = 0.0
            mc = 0.0
            
            if ascmc and len(ascmc) >= 2:
                asc = ascmc[0]
                mc = ascmc[1]
            else:
                print("WARNING: No Ascendant/MC calculated")
            
            angles = {"Ascendant": asc, "MC": mc}

        except Exception as e:
             print(f"House calculation failed completely: {e}")
             houses_result = []
             angles = {"Ascendant": 0.0, "MC": 0.0}

        # 5. Результат
        return {
            "planets": planets_result,
            "houses": houses_result,
            "angles": angles
        }

    except Exception as e:
        print(f"FATAL ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/interpret")
async def interpret(request: dict):
    return "### Интерпретация\n\nСервер работает."

@app.post("/synastry")
async def synastry(request: dict):
    return "### Синастрия\n\nСервер работает."

@app.post("/personal_horoscope")
async def personal(request: dict):
    return "### Гороскоп\n\nСервер работает."

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
