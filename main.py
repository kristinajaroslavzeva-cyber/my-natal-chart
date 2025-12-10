from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import pytz
import swisseph as swe
import os

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

# --- БАЗА ОГРОМНЫХ ТЕКСТОВ ---
zodiac_detailed = {
    "Aries": "ВАШ ЗНАК — ОВЕН. Вы — первопроходец Зодиака, искра, из которой разгорается пламя. Ваша энергия безгранична, а воля способна пробить любые стены. Вы не ждете подходящего момента — вы создаете его сами. Ваша прямолинейность может обезоруживать, а смелость вдохновляет окружающих.\n\nСИЛЬНЫЕ СТОРОНЫ: Неиссякаемый оптимизм, лидерские качества, умение быстро принимать решения. Вы честны и не держите камня за пазухой.\n\nКАРМИЧЕСКАЯ ЗАДАЧА: Научиться терпению и доводить начатое до конца. Ваша главная сила — в умении управлять своим внутренним огнем.",
    "Taurus": "ВАШ ЗНАК — ТЕЛЕЦ. Вы — воплощение надежности и созидательной силы Земли. Вы умеете видеть красоту в материальном мире и создавать вокруг себя комфорт. Ваше спокойствие подобно скале, о которую разбиваются любые штормы. Вы никуда не спешите, потому что знаете: всё лучшее требует времени.\n\nСИЛЬНЫЕ СТОРОНЫ: Потрясающее терпение, практичность, верность слову и делу. У вас есть уникальный дар — приумножать ресурсы.\n\nКАРМИЧЕСКАЯ ЗАДАЧА: Преодолеть страх перемен.",
    "Gemini": "ВАШ ЗНАК — БЛИЗНЕЦЫ. Вы — вечный ученик и коммуникатор Вселенной. Ваша стихия — Воздух, и вы так же легки, переменчивы и вездесущи. Ваш разум работает быстрее молнии, обрабатывая гигабайты информации каждую секунду.\n\nСИЛЬНЫЕ СТОРОНЫ: Интеллектуальная гибкость, остроумие, дар слова. Вы способны найти общий язык с королем и нищим.\n\nКАРМИЧЕСКАЯ ЗАДАЧА: Обрести глубину и концентрацию.",
    "Cancer": "ВАШ ЗНАК — РАК. Вы живете в ритме Луны, управляющей приливами и отливами эмоций. Ваша душа — глубокий океан. Вы обладаете невероятной эмпатией и интуитивно чувствуете настроение людей. Для вас нет ничего важнее дома, семьи и чувства безопасности.\n\nСИЛЬНЫЕ СТОРОНЫ: Забота, развитая интуиция, умение хранить тайны.\n\nКАРМИЧЕСКАЯ ЗАДАЧА: Научиться отпускать прошлое.",
    "Leo": "ВАШ ЗНАК — ЛЕВ. Вы — Солнце, вокруг которого вращаются остальные планеты. Вы рождены, чтобы творить, любить и быть замеченным. Ваша щедрость не знает границ, а благородство — ваша вторая натура.\n\nСИЛЬНЫЕ СТОРОНЫ: Харизма, творческий потенциал, уверенность в себе.\n\nКАРМИЧЕСКАЯ ЗАДАЧА: Победить гордыню и научиться служить другим.",
    "Virgo": "ВАШ ЗНАК — ДЕВА. Вы видите этот мир через призму деталей, которые незаметны другим. Ваш инструмент — безупречная логика и анализ. Вы стремитесь к совершенству во всем.\n\nСИЛЬНЫЕ СТОРОНЫ: Трудолюбие, скромность, острый ум и практичность.\n\nКАРМИЧЕСКАЯ ЗАДАЧА: Перестать критиковать себя и мир. Примите несовершенство жизни.",
    "Libra": "ВАШ ЗНАК — ВЕСЫ. Вы — мастер равновесия и дипломатии. Ваша миссия — приносить в этот мир гармонию и красоту. Вы не выносите конфликтов и всегда ищете компромисс.\n\nСИЛЬНЫЕ СТОРОНЫ: Изысканный вкус, справедливость, обаяние и такт.\n\nКАРМИЧЕСКАЯ ЗАДАЧА: Обрести внутренний стержень и научиться говорить нет.",
    "Scorpio": "ВАШ ЗНАК — СКОРПИОН. Вы — самый загадочный и мощный знак Зодиака. Ваш взгляд проникает в душу. Вы не боитесь кризисов, боли и трансформации.\n\nСИЛЬНЫЕ СТОРОНЫ: Магнетизм, несгибаемая воля, глубокая интуиция.\n\nКАРМИЧЕСКАЯ ЗАДАЧА: Трансформировать свои страсти в духовную силу.",
    "Sagittarius": "ВАШ ЗНАК — СТРЕЛЕЦ. Вы — вечный искатель истины и путешественник. Ваши стрелы всегда летят высоко в небо. Вы не можете жить без цели, смысла и новых горизонтов.\n\nСИЛЬНЫЕ СТОРОНЫ: Широта взглядов, щедрость, энтузиазм.\n\nКАРМИЧЕСКАЯ ЗАДАЧА: Научиться такту и вниманию к деталям.",
    "Capricorn": "ВАШ ЗНАК — КОЗЕРОГ. Вы — архитектор своей судьбы. Пока другие мечтают, вы строите. Вы обладаете невероятной самодисциплиной и амбициями.\n\nСИЛЬНЫЕ СТОРОНЫ: Ответственность, стратегическое мышление, упорство.\n\nКАРМИЧЕСКАЯ ЗАДАЧА: Открыть свое сердце.",
    "Aquarius": "ВАШ ЗНАК — ВОДОЛЕЙ. Вы — гость из будущего. Ваше мышление нестандартно, вы цените свободу превыше всего. Вы — бунтарь и гуманист.\n\nСИЛЬНЫЕ СТОРОНЫ: Оригинальность, независимость, изобретательность.\n\nКАРМИЧЕСКАЯ ЗАДАЧА: Соединить свою гениальность с теплотой сердца.",
    "Pisces": "ВАШ ЗНАК — РЫБЫ. Вы замыкаете зодиакальный круг. Вы живете в мире грез, музыки и интуиции. Ваша душа тонка и проницательна.\n\nСИЛЬНЫЕ СТОРОНЫ: Богатое воображение, милосердие, духовность.\n\nКАРМИЧЕСКАЯ ЗАДАЧА: Не терять связь с реальностью."
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
        return {"planets": [], "houses": [], "angles": {"Ascendant": 0.0, "MC": 0.0}}

# --- ИНТЕРПРЕТАЦИЯ ---
@app.post("/interpret")
async def interpret(request: dict):
    chart = request.get('chart', request)
    planets = chart.get('planets', [])
    sun_sign = "Aries"
    
    prompt_data = ""
    for p in planets:
        if p.get('name') == 'Sun': sun_sign = p.get('sign')
        prompt_data += f"{p['name']}: {p['sign']}; "

    result_text = zodiac_detailed.get(sun_sign, "Знак зодиака не определен.")

    if AI_AVAILABLE:
        try:
            full_prompt = (
                f"Ты астролог. Данные: {prompt_data}. "
                "Напиши психологический портрет. Пиши просто текст."
            )
            resp = model.generate_content(full_prompt)
            if resp.text: result_text = resp.text
        except: pass

    # ВОТ ЭТО ИСПРАВЛЯЕТ "НЕТ ДАННЫХ". Мы шлем чистый текст.
    return Response(content=result_text, media_type="text/plain")

# --- ГОРОСКОП ---
@app.post("/personal_horoscope")
async def personal(request: dict):
    result_text = "ВАШ ПРОГНОЗ. Сегодня день открытий. Слушайте интуицию. В любви возможен сюрприз. На работе ваши усилия заметят. Совет: Верьте в себя!"

    if AI_AVAILABLE:
        try:
            resp = model.generate_content("Напиши гороскоп на сегодня. Просто текст.")
            if resp.text: result_text = resp.text
        except: pass

    # ВОТ ЭТО ИСПРАВЛЯЕТ БЕЛЫЙ ЭКРАН.
    return Response(content=result_text, media_type="text/plain")

# --- СИНАСТРИЯ ---
@app.post("/synastry")
async def synastry(request: dict):
    result_text = "СОВМЕСТИМОСТЬ. Вы отлично дополняете друг друга. Между вами глубокая связь. Совет: учитесь слушать партнера."
    return Response(content=result_text, media_type="text/plain")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
