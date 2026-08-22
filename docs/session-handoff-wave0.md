# 📋 Session Handoff — موج ۰ (Wave 0)

**تاریخ:** 2026-08-22
**وضعیت:** جلسه فعلی پر شده — ادامه در چت جدید
**هدف این فایل:** انتقال کامل وضعیت به جلسه بعدی

---

## 🎯 وضعیت کلی پروژه

- **Repo:** `C:\Users\TOP\Desktop\test\hermes-astrology`
- **GitHub:** https://github.com/Erfix404/hermes-astrology
- **نسخه فعلی:** v2.7.1 → هدف: bump به v2.7.2 بعد از اتمام موج ۰
- **Roadmap:** [research-roadmap.md](research-roadmap.md) — ۶ موج تحقیقاتی تعریف شده

---

## ✅ تسک‌های انجام‌شده

### موج ۰-۱: رفع باگ mode های عمومی (KeyError) — ✅ تمام شد
- مشکل: dispatch mode های public مثل `weekly_calendar` قبل از `to_utc()` انجام نمی‌شد → KeyError بدون داده تولد
- راه‌حل: لیست `PUBLIC_MODES` تعریف شد و dispatch قبل از `to_utc()` منتقل شد
- فایل تغییر یافته: `scripts/astro_engine.py` (حدود خط 3486)
- تست جدید: `tests/test_engine.py` کلاس `TestPublicModesNoBirthData` (۴ تست)
- **نتیجه: ۱۱۵/۱۱۵ تست پاس**
- دو تست محیطی fail بودن که fix شدن:
  - `astro_cli.py`: اضافه کردن `sys.stdout.reconfigure(encoding='utf-8')` برای ویندوز cp1256
  - `api.py`: fallback import برای `mcp_server` وقتی پکیج `skills` موجود نیست

### موج ۰-۲: پاکسازی OCR در planet_in_house.json — ✅ تمام شد
- اسکریپت ساخته شد: `scripts/clean_planet_in_house.py`
- ۲۴/۱۲۰ رکورد پاک شد (شامل TWELFTH/PLUTO که یک فصل کامل کتاب اشتباهی paste شده بود)
- الگوهای حذف‌شده: `--PAGE N --`, footer های running, bullet ها, whitespace اضافی

---

## ⏳ تسک‌های باقی‌مانده (موج ۰)

### موج ۰-۳: node_type option (true/mean) — ⬜ شروع نشده
- **تحقیق انجام شده توسط subagent قبلی:**
  - Swiss Ephemeris: `SE_MEAN_NODE = 10`, `SE_TRUE_NODE = 11`
  - True node = osculating node؛ Mean node = smoothed average
  - True node حول mean نوسان می‌کنه با amplitude ~1.5°، period ~173 days (نیاز به تأیید منبع)
  - astro.com default: TRUE node
  - Vedic: JHora default true، Parashara's Light default mean؛ سنت کلاسیک Parashari = mean
  - Western traditional (Lilly): mean node
- **کار باقی‌مانده:** پیاده‌سازی پارامتر `node_type: "true"|"mean"` در engine + تست

### موج ۰-۴: Terms بطلمیوسی — ⬜ شروع نشده
- **تحقیق انجام شده:**
  - Tetrabiblos I.21 سه جدول داره: Chaldean، Egyptian، Ptolemaic
  - Egyptian table: Saturn=57, Jupiter=79, Mars=66, Venus=82, Mercury=76 (=360) — سازگار بین همه منابع باستانی
  - Ptolemaic terms: ۶ نسخه متفاوت وجود داره (Lilly 1647, Ashmand 1822, Robbins 1940, Boll-Boer/Schmidt, Plato of Tivoli, Hephaistio)
  - Lilly table تفاوت مهم در Gemini داره (Lilly: Saturn 4th term, Mars 5th؛ critical editions: برعکس)
  - منبع اصلی: مقاله Deborah Houlding "Ptolemy's Terms & Conditions" از skyscript (PDF 44 صفحه‌ای دانلود شده بود)
- **کار باقی‌مانده:** استخراج جدول دقیق degree-by-degree + پیاده‌سازی کنار Egyptian terms موجود

### موج ۰-۵: تکمیل Shadbala (6/6) — 🔄 در حال کار
- **وضعیت فعلی Shadbala در پروژه:** فقط ۳ بخش از ۶ بخش پیاده‌سازی شده:
  - Sthana bala (موقعیت) ✅
  - Dig bala (جهت) ✅ — توجه: این Drik نیست! Dig = directional
  - Kala bala (زمان) ✅
- **۳ بخش باقی‌مانده:** Cheshta bala, Naisargika bala, Drik bala
- **تحقیق تا الان:**
  - PDF کتاب BPHS Santhanam دانلود شد به `/tmp/bphs_san.pdf` (7MB, 855 صفحه)
    - اگر `/tmp` پاک شده، دوباره دانلود کن از: `https://archive.org/download/brihatparasarahorashastrabyr.santhanam/Brihat%20Par%C4%81%C5%9Bara%20Hor%C4%81%20%C5%9Ah%C4%81stra%20By%20R.%20Santhanam.pdf`
  - فصل Shadbala: صفحات ۲۱۷-۲۳۷ (فصل ۲۷)
  - **Naisargika Bala تأیید شد** (صفحه ۲۲۷): Sun=60, Moon=51.43, Venus=42.86, Jupiter=34.29, Mercury=25.71, Mars=17.14, Saturn=8.57 (همون که تو کد هست ✅)
  - Cheshta Bala شروع می‌شه صفحه ۲۲۸-۲۲۹ (سُکت ۱۹-۲۱): ۸ حالت حرکت سیاره
  - **درس مهم یادگرفته شده:** ❗ هرگز صفحات کتاب رو به صورت عکس (base64 PNG) نخون — کانتکس رو منفجر می‌کنه!
  
### ⚠️ روش صحیح خوندن کتاب (بسیار مهم!)
1. **استخراج متن به فایل‌های txt جداگانه** — نه عکس!
```bash
python -c "
import pymupdf
doc = pymupdf.open('/tmp/bphs_san.pdf')
for i in range(doc.page_count):
    text = doc[i].get_text()
    with open(f'/tmp/bphs_pages/page_{i}.txt', 'w', encoding='utf-8') as f:
        f.write(text)
"
```
2. **فقط صفحات مورد نیاز رو بخون** — نه کل کتاب
3. **از subagent استفاده کن** — کانتکس جداگانه داره، فقط خلاصه برگردونه
4. یا از grep روی فایل‌های txt استفاده کن دنبال کلمات کلیدی مثل "Cheshta", "Drik bala"

### موج ۰-۶: تست کامل + bump v2.7.2 + commit — ⬜ شروع نشده
- بعد از تموم شدن ۳-۵ اجرا بشه

---

## 🔧 وضعیت فنی

### فایل‌های تغییر یافته (uncommitted):
```
scripts/astro_engine.py      — PUBLIC_MODES + dispatch قبل از to_utc()
scripts/astro_cli.py         — UTF-8 reconfigure
scripts/api.py               — fallback import mcp_server
scripts/clean_planet_in_house.py — جدید
data/planet_in_house.json    — ۲۴ رکورد پاک شده
tests/test_engine.py         — TestPublicModesNoBirthData
docs/research-roadmap.md     — نقشه راه ۶ موج
docs/session-handoff-wave0.md — این فایل
```

### دستورات مفید:
```bash
# اجرای تست‌ها
python -m unittest tests.test_engine tests.test_cli

# وضعیت git
git status --short && git diff --stat

# دانلود مجدد BPHS (اگر /tmp پاک شده)
python -c "
import urllib.request
url = 'https://archive.org/download/brihatparasarahorashastrabyr.santhanam/Brihat%20Par%C4%81%C5%9Bara%20Hor%C4%81%20%C5%9Ah%C4%81stra%20By%20R.%20Santhanam.pdf'
req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
data = urllib.request.urlopen(req, timeout=120).read()
open('/tmp/bphs_san.pdf','wb').write(data)
print(f'Downloaded {len(data)} bytes')
"
```

---

## 📝 نکات مهم برای جلسه بعد

1. **اول commit کن** کارهای انجام‌شده موج ۰-۱ و ۰-۲ رو (قبل از شروع کار جدید)
2. **هرگز عکس کتاب نخون** — فقط متن استخراج کن به فایل txt
3. **subagent برای تحقیق کتاب** — کانتکس اصلی رو آلوده نکن
4. **تست‌ها رو هر بار اجرا کن** بعد از هر تغییر: `python -m unittest discover tests`
5. **Naisargika Bala تأیید شده** — فقط Cheshta و Drik مونده
6. برای Cheshta Bala: صفحات ۲۲۸-۲۳۲ BPHS رو بخون (بعد از استخراج txt)
7. برای Drik Bala: احتمالاً صفحات ۲۳۲-۲۳۵

---

## 🚀 ترتیب پیشنهادی جلسه بعد

1. Commit کارهای فعلی (موج ۰-۱، ۰-۲)
2. استخراج متن BPHS به فایل‌های txt
3. Subagent بفرست برای خوندن Cheshta/Drik bala از فایل‌ها
4. پیاده‌سازی node_type option (موج ۰-۳) — تحقیقش کامله
5. پیاده‌سازی Ptolemaic terms (موج ۰-۴) — جدول باید استخراج بشه
6. تکمیل Shadbala (موج ۰-۵) — با اطلاعات subagent
7. تست کامل + bump نسخه + commit (موج ۰-۶)
