from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import os
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- КЛЮЧ ---
GEMINI_API_KEY = "AIzaSyD-cVzx6xh-fUmajMe15-CV8RvNpLxLKNc"
genai.configure(api_key=GEMINI_API_KEY)

# --- НАСТРОЙКИ БЕЗОПАСНОСТИ ---
safety_settings = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

# --- АВТОПОДБОР МОДЕЛИ ---
active_model = None
try:
    # Ищем любую доступную модель
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            active_model = genai.GenerativeModel(m.name)
            print(f"Active model found: {m.name}")
            break
except Exception as e:
    print(f"Model selection error: {e}")

# Резерв, если цикл не сработал
if not active_model:
    active_model = genai.GenerativeModel('gemini-1.5-flash')

# -----------------------------------------------------------

class BirthData(BaseModel):
    birthDateTime: str
    latitude: float
    longitude: float
    zoneId: str

def get_sign_name(lon):
    """Определяет знак зодиака по градусу (0-360)"""
    signs = [
        "Aries", "Taurus", "Gemini", "Cancer", 
        "Leo", "Virgo", "Libra", "Scorpio", 
        "Sagittarius", "Capricorn", "Aquarius", "Pisces"
    ]
    idx = int(lon // 30)
    return signs[idx % 12]

# 1. РЕАЛЬНЫЙ РАСЧЕТ НАТАЛЬНОЙ КАРТЫ
@app.post("/calculate")
async def calculate_chart(data: BirthData):
    try:
        # 1. Подготовка данных для Flatlib
        # data.birthDateTime приходит в формате ISO (напр. 1990-05-20T14:30:00)
        # Flatlib требует формат "YYYY/MM/DD" и "HH:MM"
        
        # Обрезаем лишнее и меняем формат
        date_raw = data.birthDateTime.split('T')[0].replace('-', '/')
        time_raw = data.birthDateTime.split('T')[1][:5] # берем первые 5 символов времени HH:MM
        
        # Создаем объект даты (считаем время UTC для простоты, или можно учитывать zoneId, 
        # но для базового расчета достаточно UTC, если фронт шлет UTC)
        date = Datetime(date_raw, time_raw, '+00:00')
        pos = GeoPos(data.latitude, data.longitude)
        
        # 2. Строим карту
        chart = Chart(date, pos)

        # 3. Список планет, которые нам нужны
        # Flatlib ID планет
        planets_to_calc = [
            const.SUN, const.MOON, const.MERCURY, const.VENUS, const.MARS,
            const.JUPITER, const.SATURN, const.URANUS, const.NEPTUNE, const.PLUTO,
            const.CHIRON, const.NORTH_NODE
        ]

        output_planets = []

        for p_id in planets_to_calc:
            obj = chart.get(p_id)
            
            # Имя для фронтенда (North Node требует переименования, если фронт ждет NNode)
            name = p_id
            if p_id == const.NORTH_NODE:
                name = "NNode"
            
            # Формируем объект, чтобы не было ошибки TypeError на фронте
            planet_data = {
                "name": name,
                "angle": float(obj.lon),      # Реальный градус (0-360)
                "sign": get_sign_name(obj.lon), # Знак зодиака
                "retrograde": obj.isRetrograde(), # Ретроградность (True/False)
                "speed": float(obj.lonspeed), # Скорость (ВАЖНО для фикса ошибки)
                "lat": float(obj.lat),        # Широта эклиптическая
                "lng": float(obj.lon)         # Дублируем долготу если надо
            }
            output_planets.append(planet_data)

        # 4. Расчет домов (Placidus по умолчанию)
        output_houses = []
        for i in range(1, 13):
            # Flatlib хранит дома как House1, House2...
            h = chart.get(getattr(const, f'HOUSE{i}'))
            output_houses.append(float(h.lon))

        # 5. Углы (Ascendant, MC)
        asc = chart.get(const.ASC)
        mc = chart.get(const.MC)
        
        return {
            "planets": output_planets,
            "houses": output_houses,
            "angles": {
                "Ascendant": float(asc.lon),
                "MC": float(mc.lon)
            }
        }

    except Exception as e:
        print(f"Calculation Error: {e}")
        # Если вдруг реальный расчет упал (неверная дата и т.д.), возвращаем ошибку,
        # чтобы видеть её в логах, а не пустой экран.
        return Response(content=f"Error: {str(e)}", status_code=500)


# 2. ИНТЕРПРЕТАЦИЯ (GEMINI)
@app.post("/interpret")
async def interpret(request: dict):
    try:
        if active_model:
            prompt = "Ты профессиональный астролог. Составь краткий, но глубокий психологический портрет личности на основе натальной карты. Не используй разметку Markdown."
            resp = active_model.generate_content(prompt)
            return Response(content=resp.text, media_type="text/plain; charset=utf-8")
        
        return Response(content="Сервис временно недоступен.", media_type="text/plain; charset=utf-8")
    except Exception as e:
        return Response(content=str(e), media_type="text/plain; charset=utf-8")


# 3. ГОРОСКОП НА СЕГОДНЯ (GEMINI)
@app.post("/personal_horoscope")
async def personal(request: dict):
    try:
        birth_date = request.get("birthDateTime", "неизвестно")
        prompt = (
            f"Дата рождения: {birth_date}. "
            "Напиши персональный гороскоп на сегодня. "
            "Дай конкретный совет в позитивном ключе. Не более 3 предложений."
        )

        if active_model:
            resp = active_model.generate_content(prompt)
            if resp.text:
                return Response(content=resp.text, media_type="text/plain; charset=utf-8")
        
        return Response(content="Сегодня отличный день для новых начинаний.", media_type="text/plain; charset=utf-8")

    except Exception as e:
        return Response(content="Звезды молчат.", media_type="text/plain; charset=utf-8")


# 4. СИНАСТРИЯ (GEMINI)
@app.post("/synastry")
async def synastry(request: dict):
    try:
        # Здесь в будущем можно добавить реальный расчет совместимости,
        # но пока оставляем текстовую интерпретацию от ИИ.
        if active_model:
            resp = active_model.generate_content("Опиши астрологическую совместимость для пары. Дай совет.")
            return Response(content=resp.text, media_type="text/plain; charset=utf-8")
        return Response(content="Сервис временно недоступен", media_type="text/plain; charset=utf-8")
    except Exception as e:
        return Response(content=f"Ошибка: {str(e)}", media_type="text/plain; charset=utf-8")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
