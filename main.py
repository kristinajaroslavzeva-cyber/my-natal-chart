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
    print("WARNING: google-generativeai library not found.")

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

# --- БАЗА ЗНАНИЙ (ДЛИННЫЕ ТЕКСТЫ) ---
zodiac_detailed = {
    "Aries": "**♈ ОВЕН: Первопроходец**\n\nВы — искра, из которой разгорается пламя. Ваша энергия безгранична. Вы не ждете момента, вы создаете его.\n\n*Сила:* Смелость и лидерство.\n*Карма:* Учиться терпению.",
    "Taurus": "**♉ ТЕЛЕЦ: Созидатель**\n\nВы — скала надежности. Вы цените комфорт и умеете наслаждаться жизнью. Ваше терпение легендарно.\n\n*Сила:* Упорство и стабильность.\n*Карма:* Не бояться перемен.",
    "Gemini": "**♊ БЛИЗНЕЦЫ: Коммуникатор**\n\nВаш ум быстр как молния. Вы вечный ученик, которому интересно всё на свете.\n\n*Сила:* Интеллект и гибкость.\n*Карма:* Обрести фокус.",
    "Cancer": "**♋ РАК: Хранитель**\n\nВы чувствуете этот мир сердцем. Семья и дом — ваша крепость. Ваша интуиция безошибочна.\n\n*Сила:* Эмпатия и забота.\n*Карма:* Отпустить прошлое.",
    "Leo": "**♌ ЛЕВ: Король**\n\nВы рождены сиять. Ваша харизма притягивает людей, а щедрость не знает границ.\n\n*Сила:* Творчество и уверенность.\n*Карма:* Служить другим.",
    "Virgo": "**♍ ДЕВА: Аналитик**\n\nВы видите совершенство в деталях. Ваш порядок и логика спасают мир от хаоса.\n\n*Сила:* Трудолюбие и ум.\n*Карма:* Перестать критиковать себя.",
    "Libra": "**♎ ВЕСЫ: Дипломат**\n\nВы создаете гармонию. Ваша миссия — красота и справедливость. Вы мастер компромиссов.\n\n*Сила:* Вкус и такт.\n*Карма:* Обрести стержень.",
    "Scorpio": "**♏ СКОРПИОН: Мистик**\n\nВы обладаете мощной магией. Вы видите людей насквозь и не боитесь кризисов.\n\n*Сила:* Воля и интуиция.\n*Карма:* Прощать обиды.",
    "Sagittarius": "**♐ СТРЕЛЕЦ: Философ**\n\nВы целитесь в звезды. Ваш оптимизм и жажда знаний открывают любые двери.\n\n*Сила:* Мудрость и широта взглядов.\n*Карма:* Внимание к деталям.",
    "Capricorn": "**♑ КОЗЕРОГ: Стратег**\n\nВы строите успех кирпичик за кирпичиком. Ваша дисциплина вызывает уважение.\n\n*Сила:* Амбиции и надежность.\n*Карма:* Открыть сердце.",
    "Aquarius": "**♒ ВОДОЛЕЙ: Новатор**\n\nВы гость из будущего. Свобода для вас важнее всего. Вы меняете правила игры.\n\n*Сила:* Оригинальность.\n*Карма:* Теплота к близким.",
    "Pisces": "**♓ РЫБЫ: Мечтатель**\n\nВы живете в мире интуиции. Ваша душа глубока, как океан. Вы творец.\n\n*Сила:* Милосердие и фантазия.\n*Карма:* Связь с реальностью."
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

# --- 1. РАСЧЕТ ---
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

        # Дома
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

# --- 2. ИНТЕРПРЕТАЦИЯ (Возвращаем JSON!) ---
@app.post("/interpret")
async def interpret(request: dict):
    try:
        chart = request.get('chart', request)
        planets = chart.get('planets', [])
        sun_sign = "Aries" # Дефолт
        
        prompt_data = ""
        for p in planets:
            if p.get('name') == 'Sun': sun_sign = p.get('sign')
            prompt_data += f"{p['name']}: {p['sign']}\n"

        # Пробуем ИИ
        if AI_AVAILABLE and len(GEMINI_API_KEY) > 20:
            try:
                resp = model.generate_content(f"Ты астролог. Опиши личность кратко и ярко: {prompt_data}")
                if resp.text: 
                    # ВАЖНО: Возвращаем JSON, а не просто текст
                    return {"content": resp.text}
            except: pass
        
        # Если ИИ нет - берем красивый текст из словаря
        text = zodiac_detailed.get(sun_sign, "Знак не определен")
        return {"content": text} # <--- ВОТ ЭТО ИСПРАВИТ ПРОБЛЕМУ "1 СТРОКИ"

    except Exception as e:
        return {"content": f"Ошибка: {str(e)}"}

# --- 3. ГОРОСКОП (Возвращаем JSON!) ---
@app.post("/personal_horoscope")
async def personal(request: dict):
    # Генератор заглушки (если ИИ спит)
    text = (
        "### 🔮 Ваш прогноз\n\n"
        "**Общее:** Сегодня день открытий. Слушайте интуицию.\n"
        "**Любовь:** Возможен приятный сюрприз.\n"
        "**Карьера:** Ваши усилия будут замечены."
    )
    
    if AI_AVAILABLE and len(GEMINI_API_KEY) > 20:
        try:
            resp = model.generate_content("Напиши позитивный гороскоп на сегодня (Любовь, Карьера, Совет).")
            if resp.text: text = resp.text
        except: pass

    # ВАЖНО: Возвращаем JSON
    return {"content": text}

# --- 4. СИНАСТРИЯ (Возвращаем JSON!) ---
@app.post("/synastry")
async def synastry(request: dict):
    text = (
        "### ❤️ Совместимость\n\n"
        "**Потенциал:** Вы отлично дополняете друг друга.\n"
        "**Совет:** Ищите компромиссы."
    )
    return {"content": text}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
