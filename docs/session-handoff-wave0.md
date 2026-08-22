# 📋 Session Handoff — موج ۰ (Wave 0)

**تاریخ:** 2026-08-22
**وضعیت:** ✅ **موج ۰ کامل شد** — همه ۶ تسک انجام و commit شدن
**نسخه:** v2.7.2 (bump شد)

---

## 🎯 وضعیت کلی پروژه

- **Repo:** `C:\Users\TOP\Desktop\test\hermes-astrology`
- **GitHub:** https://github.com/Erfix404/hermes-astrology
- **تست‌ها:** ۱۲۳/۱۲۳ پاس
- **Roadmap:** [research-roadmap.md](research-roadmap.md) — ۶ موج؛ موج ۰ تمام → بعدی: موج ۱ (پیشگویی غربی)

---

## ✅ موج ۰ — همه انجام شد (commits: efeb008, e135524, 0044b65, 9889050)

### ۰-۱ ✅ PUBLIC_MODES dispatch fix | ۰-۲ ✅ OCR cleanup planet_in_house.json
(جزئیات در git log)

### ۰-۳ ✅ node_type option ("true"|"mean")
- `body_longitudes(jd, node_type=None)` — default: true با swe، mean با builtin
- `calculate_full_profile` از `data["node_type"]` می‌خونه و در `_meta` گزارش می‌ده
- **باگ جانبی کشف و رفع شد:** بدون فایل‌های .se1، swe بی‌صدا به builtin (~1-2 arcmin) برمی‌گشت!
  حالا `_swe_calc_flags(jd)` با probe تاریخ-محور FLG_MOSEPH رو انتخاب می‌کنه (دقت 0.1 arcsec)
  و فقط Chiron (بدون seas_18.se1) به Keplerian fallback می‌ره
- pyswisseph نصب شد (`pip install pyswisseph`)
- تست: `TestNodeTypeOption` (۳ تست)

### ۰-۴ ✅ Ptolemaic terms کنار Egyptian bounds
- `dignity_western` هر دو سیستم رو چک می‌کنه: "term (Egyptian bound)" / "term (Ptolemaic)"
- جدول طبق بازسازی Houlding (Robbins/Hephaistio critical reading)
- منبع: `book/Houlding_ptolemy_terms.pdf` (44 صفحه؛ متن prose توصیف کامل داره؛ جدول‌ها عکس هستن)
- تست: `TestPtolemaicTerms` — جمع ۳۰°/برج + ۵ ارباب یکتا + تفکیک دو سیستم در Gemini 22°

### ۰-۵ ✅ Cheshta + Drik Bala واقعی (BPHS Ch.27)
- Cheshta: Sun = ayana از declination جنوبی (asin formula؛ max ۶۰ ویروپا در انقلاب جدی)؛
  Moon = paksha از tithi؛ Mars..Saturn = Cheshta Kendra از apogee کلاسیک ÷۳
- Drik: تابع piecewise speculum + وزن‌دهی خیر/شریر طبق شلوکا ۱۹
- **پونی‌تیل:** mean longitude ≈ true sidereal تا engine واقعاً mean بده
- اسپک کامل فرمول‌ها: subagent از صفحات txt استخراج کرد (روش امن زیر)
- تست: `TestShadbalaCheshtaDrik` (۳ تست)

### ۰-۶ ✅ bump v2.7.2 + این فایل

---

## ⚠️ روش صحیح خوندن کتاب (درس چت خراب‌شده — همیشه رعایت شود!)
1. **هرگز صفحه PDF رو به صورت عکس/base64 نخون** — کانتکس منفجر می‌شه
2. استخراج متن با pymupdf به فایل txt → فقط صفحات لازم
3. **subagent برای تحقیق کتاب** — کانتکس جداگانه، فقط اسپک ساختاریافته برگردونه
4. صفحات BPHS آماده‌ست: `book/bphs_pages/page_205..244.txt`
5. OCR عکس (اگه لایه متنی نبود): `scripts/vision_ocr.py` با 9Router — ولی مدل Vision روتر
   فعلاً image_url رو پاس نمی‌ده (بررسی شد؛ "[image omitted]") — باید مدل دیگه یا fix روتر

---

## 🔑 نکات فنی مهم

- `.env` در ریشه ریپو: OPENROUTER_BASE_URL/API_KEY برای 9Router (**gitignore شده — لو نرو**)
- swisseph بدون فایل‌های ephe → MOSEPH fallback خودکار (فقط Chiron محدود می‌شه)
  برای دقت کامل: دانلود ephe files از github.com/aloistr/swisseph/tree/master/ephe به `ephe/`
- تست: `python -m unittest discover tests`

---

## 🚀 قدم بعدی: موج ۱ — پیشگویی غربی (طبق research-roadmap.md)

1. Transits interpreted (عمق بیشتر از transits فعلی)
2. Secondary progressions interpreted
3. Solar arc interpreted (الان فقط directions خام)
4. Profection years / annual themes
5. Firdaria
6. ZR (Zodiacal Releasing) — تحقیق سنگین، subagent لازم

هر موج: اول audit موجود → بعد subagent تحقیق → پیاده‌سازی + تست → commit.
