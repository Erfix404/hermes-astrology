# ✨ Astraea — Celestial Intelligence Engine (v4.0.0)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Tests Passing](https://img.shields.io/badge/Tests-176%20Passed%20(100%25)-success.svg)](https://github.com/Erfix404/hermes-astrology)
[![Ephemeris: NASA JPL / SwissEph](https://img.shields.io/badge/Ephemeris-JPL%20%7C%20SwissEph-purple.svg)](https://www.astro.com/swisseph/)

**آستریا (Astraea) — ابرموتور قطعی و چندسنتی هوش کیهانی، آسترولوژی و پیشگویی برای هوش مصنوعی**  
*Astraea — Deterministic Multi-Tradition Celestial Intelligence Engine & AI-Agent Backend*

---

## 📖 درباره آستریا (About Astraea)

**Astraea (آستریا)** نام الهه باستانی ستارگان، حقیقت و پاکی کیهانی است. این پروژه یک ابرموتور جامع، مستقل (Zero-Dependency) و فوق‌العاده دقیق است که سه سنت اصیل تاریخ بشر (**غربی/هلنیستی**، **ودیک/جیوتیش**، و **چینی/باژی**) را همراه با نجوم رویدادی، مالی و باطنی در یک معماری یکپارچه ادغام کرده است.

برخلاف چت‌بات‌های متداول که موقعیت سیارات را توهم (Hallucinate) می‌کنند، Astraea موقعیت‌های نجومی را بر پایه ریاضیات مداری **NASA JPL DE421 / Swiss Ephemeris** و فرمول‌های معتبر کهن محاسبه کرده و در عین حال، با مجهز بودن به یک **موتور تطبیق لحن ۳ سطحی (ساده و خودمانی تا تحلیل فوق‌حرفه‌ای)**، به هر کاربری با هر میزان از دانش پاسخی دلنشین، کاربردی و انسانی ارائه می‌دهد.

---

### 🌐 سنت‌های تحت پوشش (Supported Traditions)

| سنت (Tradition) | سیستم محاسباتی (System) | مبنای تحلیلی (Core Focus) |
|---|---|---|
| **♈ غربی و هلنیستی (Western & Hellenistic)** | تروپیکال / بطلمیوس، والنس، لیلی | کهن‌الگوهای روانی، اربابان زمان (ZR, Profections, Firdaria)، پراگرسیون‌ها، آستروداین |
| **☪ ودیک و هندی (Vedic / Jyotisha)** | سایدریال (آیانامشا لاهیری ۲۴°) | کارما، شادبالا ۶/۶ کامل (BPHS)، داشای ۳ سطحی، چارا داشای جیمینی، گوچارا با سده‌ساتی |
| **🏛️ جهانی و اسلامی-عبری (Mundane & Medieval)** | چارت‌های اینگرس پایتخت‌ها / ابن‌عزرا | اینگرس‌های فصلی بوناتی/لیلی با اعتبار زمانی پویا، کسوف‌ها با تریگر کارتر، لوت‌های ۱۳گانه ازدواج |
| **木 چینی (Chinese BaZi)** | چهار ستون سرنوشت (Four Pillars) | تعادل عناصر پنج‌گانه (Wu Xing)، ستون‌های شانس ده‌ساله (Da Yun)، ده کهن‌الگو (Ten Gods) |
| **🔮 باطنی و هرمسی (Hermetic & Esoteric)** | ۳۶ دکان، گلدن دان و تاروت | انطباق ۳۶ دکان با تصاویر باستانی آغاز خرد و کارت‌های تاروت، درخت حیات قبالا |

---

## 🌟 قابلیت‌های برجسته نسخه ۴.۰ (Key Features in v4.0.0)

### ۱. پیشگویی و اربابان زمان (Master Forecasting & Time-Lords)
* **Zodiacal Releasing (رهایش برجی والنس):** محاسبه فصول اوج شغلی و مالی، پدیده‌های جهش و گسست پیوند (Loosing of the Bond) بر روی تقویم نمادین ۳۶۰ روزه.
* **Annual & Monthly Profections:** فعال شدن پویای خانه‌ها و ارباب سال/ماه.
* **Medieval Firdaria:** دوره‌های ۷۵ ساله بر اساس سکت روز و شب به همراه ۷ زیردوره سیاره‌ای منسوب به ابن‌عزرا.
* **Secondary Progressions & Solar Arc:** پراگرسیون‌های ثانویه و رصد فازهای ۸ گانه ماه پراگرس‌شده.
* **3-Level Vimshottari Dasha:** تفکیک دقیق مهاداشا، آنتارداشا و پراتیانتارداشا (سطح ۳) به همراه داشای برجی چارا (Jaimini / Rao).

### ۲. هوش تصمیم‌گیری و پرونده‌های تخصصی (Domain Blueprints & Decisions)
* **موتور انتخاب زمان طلایی (`find_best_time`):** اسکن خودکار ۳۰/۶۰ روز آینده و گزینش ۳ پنجره طلایی برای بیزنس، عقد، خرید ملک، سفر و جراحی بر اساس کتاب انتخابات ابن‌عزرا.
* **چارت فضا-زمان دیویسون (`davison` & `davison_progression`):** محاسبه چارت واقعی رابطه در فضا-زمان و پیشگویی مسیر رابطه با پراگرسیون دیویسون.
* **سینستری دراکونیک (`draconic` & `draconic_synastry`):** کشف قراردادهای کارمایی روح با انتقال گره شمالی به ۰ درجه حمل.
* **پرونده جامع ثروت و شغل (`wealth_blueprint`):** تلفیق خانه‌های ۲ و ۱۰، سهم‌المال، چارت دسامشا D10، ایندو لاگنا و عنصر پول باژی.
* **پرونده ازدواج و عشق (`love_blueprint`):** خانه ۷، ناوامشا D9، لوت‌های ۱۳گانه ابن‌عزرا و ابطال مانگلیک دوشا (Kuja Dosha).

### ۳. اصلاح ساعت تولد، کریپتو و راهکارها (Advanced Engines)
* **اصلاح خودکار ساعت تولد (`rectify_birth_time` / BTR):** اسکن بازه زمانی و محاسبه معکوس زوایای چارت با دایرکشن‌های قوس خورشیدی و تقارن تروتین هرمس بر اساس وقایع گذشته زندگی.
* **آسترو-تریدینگ و نجوم مالی (`crypto` / `financial`):** رصد شاخص نوسان و زوایای ترانزیت به چارت جنسیس بیت‌کوین، اتریوم، اس‌اندپی ۵۰۰ و طلا.
* **تجویز علمی راهکارها و سنگ‌ها (`remedies_blueprint`):** تجویز سنگ **فقط** برای سعد کارکردی (نه داستاهانا)، اقلام اهدا و خیریه (Daan) و عادات رفتاری لیز گرین.
* **ابرموتور اجماع سه‌سنتی (`tri_consensus`):** محاسبه درصد قطعیت رویدادها (Confidence Score ۴۵٪ تا ۹۸٪) از تقاطع همزمان غربی، ودیک و باژی.
* **تقویم روزانه ساعات سعد و نحس (`daily_panchang` / `choghadiya`):** دوره‌های ۸‌گانه روز/شب (آمریت، شوب، لاب و...) به همراه پنجره‌های ابحیجیت، برهما و راهو کالام.
* **امتیازدهی آستروداین (`astrodynes`):** نمره‌دهی عددی به توان (Power) و هارمونی (Harmony) سیارات و خانه‌ها (کلیسای نور).

---

## 🚀 راهنمای سریع (Quick Start)

### نصب و کلون مخزن
```bash
git clone https://github.com/Erfix404/hermes-astrology.git
cd hermes-astrology
```

### اجرای مستقیم از طریق خط فرمان (CLI)
```bash
# محاسبه چارت کامل ۳ سنتی
python scripts/astro_engine.py --json '{"year":1995,"month":4,"day":15,"hour":14,"minute":30,"lat":35.6892,"lng":51.3890,"tz":"Asia/Tehran","systems":["western","vedic","bazi"]}'

# جستجوی ۳ زمان طلایی برای شروع بیزنس در ۳۰ روز آینده
python scripts/astro_engine.py --json '{"lat":35.6892,"lng":51.3890,"mode":"find_best_time","activity":"business_commerce","days_ahead":30}'

# بررسی آب‌وهوای کریپتو و نوسانات بیت‌کوین
python scripts/astro_engine.py --json '{"mode":"crypto","asset":"BTC"}'

# اجرای تست‌های جامع (۱۷۶ تست)
python -m unittest discover tests
```

### استفاده به عنوان کتابخانه پایتون (Python API)
```python
import sys
sys.path.insert(0, "scripts")
from astro_engine import calculate_full_profile

# استخراج پرونده کامل ثروت و شغل
result = calculate_full_profile({
    "year": 1990, "month": 6, "day": 15, "hour": 11, "minute": 0,
    "lat": 35.6892, "lng": 51.3890, "tz": "Asia/Tehran",
    "mode": "wealth_blueprint"
})

print(result["wealth_blueprint"]["synthesis_summary"])
```

---

## 🛠️ معماری و سازگاری (Architecture)
- **Zero-Dependency Core:** متکی بر ماژول‌های استاندارد پایتون (`math`, `datetime`, `json`).
- **Resilient Fallback:** در صورت عدم دسترسی به فایل‌های سوئیس اپفمریس، محاسبات به صورت خودکار به مدل دقیق Moshier و بیلتین سوئیچ می‌کنند بدون اینکه خطایی رخ دهد.
- **REST API + MCP Server:** آماده اتصال به FastAPI، کلاینت‌های هوش مصنوعی (Claude Desktop, Cursor, Devin) و دستیاران اختصاصی.

---

## 📜 لایسنس
این پروژه تحت لایسنس **MIT** منتشر شده است و استفاده شخصی و تجاری از آن آزاد است.
Developed with ❤️ by **Erfan Ashouri (Erfix404)**.
