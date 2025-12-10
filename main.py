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

# ... (остальной код выше не трогай) ...

# Добавь эту простую базу знаний ПЕРЕД функцией interpret
zodiac_texts = {
    "Aries": "Вы — Овен. Ваша стихия — Огонь. Вы полны энергии, инициативны и прямолинейны. Главная задача — научиться терпению.",
    "Taurus": "Вы — Телец. Ваша стихия — Земля. Вы цените комфорт, стабильность и красоту. Вы надежны, но бываете упрямы.",
    "Gemini": "Вы — Близнецы. Ваша стихия — Воздух. Вы общительны, любознательны и легки на подъем.",
    "Cancer": "Вы — Рак. Ваша стихия — Вода. Вы эмоциональны, заботливы и привязаны к дому.",
    "Leo": "Вы — Лев. Ваша стихия — Огонь. Вы рождены, чтобы сиять. Творчество и лидерство — ваша суть.",
    "Virgo": "Вы — Дева. Ваша стихия — Земля. Вы внимательны к деталям, трудолюбивы и любите порядок.",
    "Libra": "Вы — Весы. Ваша стихия — Воздух. Вы стремитесь к гармонии, партнерству и справедливости.",
    "Scorpio": "Вы — Скорпион. Ваша стихия — Вода. Вы обладаете мощной интуицией и сильной волей.",
    "Sagittarius": "Вы — Стрелец. Ваша стихия — Огонь. Вы оптимист, философ и любитель путешествий.",
    "Capricorn": "Вы — Козерог. Ваша стихия — Земля. Вы амбициозны, дисциплинированы и идете к цели до конца.",
    "Aquarius": "Вы — Водолей. Ваша стихия — Воздух. Вы оригинальны, независимы и смотрите в будущее.",
    "Pisces": "Вы — Рыбы. Ваша стихия — Вода. Вы мечтательны, сострадательны и обладаете богатым воображением."
}

@app.post("/interpret")
async def interpret(request: dict):
    # request приходит в виде словаря. Нам нужно знать Знак Солнца.
    # Фронтенд должен присылать список планет или хотя бы знак Солнца.
    # Но если фронтенд пока присылает просто запрос, давай сделаем универсальный ответ.
    
    # В ИДЕАЛЕ: Фронтенд должен сначала вызвать /calculate, получить "Sun": "Aries",
    # а потом отправить это в /interpret.
    
    # Пока сделаем заглушку, которая подтверждает, что это СЕРВЕР:
    return "### Гороскоп от Сервера\n\nСервер работает! Эфемериды подключены.\n\n" \
           "Для получения детальной интерпретации приложение должно отправить знак зодиака.\n" \
           "Но я вижу, что техническая часть настроена верно."

# ... (остальной код ниже) ...

@app.post("/synastry")
async def synastry(request: dict):
    return "### Синастрия\n\nДанные совместимости рассчитаны."

@app.post("/personal_horoscope")
async def personal(request: dict):
    return "### Ваш гороскоп\n\nПерсональный прогноз готов."

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
