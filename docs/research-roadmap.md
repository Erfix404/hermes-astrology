# 🗺️ نقشه راه تحقیقاتی — hermes-astrology v3.0

**تاریخ شروع:** 2026-08-21
**هدف:** رسوندن پروژه به کامل‌ترین موتور نجومی برای AI agent ها — با تمرکز روی **پیشگویی (forecasting)**، **تحلیل چارت شخصی**، و **تحلیل رویدادها (mundane)**
**روش کار هر موج:** تحقیق از منبع → نوشتن قواعد در `references/` → پیاده‌سازی mode/داده → تست → commit
**دسترسی منابع:** آزاد — کتاب‌های کپی‌رایت‌دار هم مجاز (IA borrow، dokumen.pub، pdfcoffee و…)

> قانون طلایی: هیچ موجی بدون تست پاس‌شده و commit بسته نمی‌شه.
> وضعیت هر آیتم: ⬜ انجام‌نشده | 🔄 در حال کار | ✅ تمام‌شده

---

## 📊 نمای کلی موج‌ها

| # | موج | تمرکز | حجم تقریبی |
|---|-----|-------|-----------|
| ۰ | اصلاحات فوری | باگ‌ها + بدهی audit قبلی | کوچک |
| ۱ | پیشگویی غربی ⭐ | timeline, profections, firdaria, تفسیر ترانزیت | بزرگ |
| ۲ | ودیک پیشگویانه | Shadbala کامل، dasha عمیق، yogas، Tajika، Prashna | بزرگ |
| ۳ | Mundane / رویداد جهانی | ingress، خسوف جهانی، چرخه‌های بزرگ | متوسط-بزرگ |
| ۴ | سینستری و روابط | تفسیر inter-aspect، composite، guna milan | متوسط |
| ۵ | فارسی‌سازی دانش | نسخه فارسی همه رفرنس‌ها | متوسط |
| ۶ | اعتبارسنجی + انتشار v3.0 | Rodden charts، مقایسه astro.com، ریلیز | کوچک |

---

## موج ۰ — اصلاحات فوری ⬜

هدف: پاک‌کردن بدهی فنی قبل از تحقیق. هیچ تحقیق جدیدی لازم نیست.

- ⬜ **باگ mode های عمومی:** `weekly_calendar` و بقیه mode های بدون نیاز به تولد، قبل از dispatch به `to_utc()` می‌خورن و بدون داده تولد `KeyError` میدن (astro_engine.py:3500). Fix: dispatch mode های public قبل از `to_utc`.
- ⬜ **پاکسازی OCR** در `data/planet_in_house.json` — آلودگی‌های `--PAGE 317 --` و شماره صفحه.
- ⬜ **Mean node option** (G16b audit): پارامتر `node_type: "true"|"mean"` — پیش‌فرض true برای ودیک، mean برای غربی.
- ⬜ **Terms بطلمیوسی** (G17d audit): جدول Ptolemaic terms کنار Egyptian موجود.
- ⬜ **Shadbala تکمیل** (G7 audit): Cheshta bala + Naisargika bala + Drik bala → ۶/۶ بخش.
- ⬜ تست برای همه موارد بالا + bump به v2.7.2 + commit.

---

## موج ۱ — پیشگویی غربی ⭐ (اولویت اصلی) ⬜

هدف: موتور بتونه **تایم‌لاین روایی** بده — «از X تا Y فلان ترانزیت فعاله، فصل زندگی‌ات اینه، این ماه در پروفکشن خونه N هستی». این قلب درخواست‌های روزانه/ماهانه/سالانه‌ست.

### منابع (به ترتیب اهمیت)
| کتاب | نویسنده | چی می‌گیریم |
|------|---------|------------|
| **Planets in Transit** (~750pp) | Robert Hand | مرجع شماره ۱ تفسیر ترانزیت — هر سیاره × هر سیاره ناتال × هر جنبه |
| **Predictive Astrology: The Eagle and the Lark** | Bernadette Brady | متدولوژی پیشگویی، ترانزیت‌های ترکیبی، خسوف در پیشگویی، rectification |
| **Hellenistic Astrology** | Chris Brennan | Profections (سالانه/ماهانه)، Zodiacal Releasing، time-lord systems |
| **The Changing Sky** | Steven Forrest | progressions عملی + ترانزیت، روایت پیشگویی |
| **Planets in Composite** | Robert Hand | (موج ۴ هم استفاده می‌شه) |
| Skyscript / astro.com docs | وب | اعتبارسنجی قواعد |

### کارها
- ⬜ ۱.۱ — تحقیق: استخراج قواعد profection (سالانه: سن→خانه؛ ماهانه: ۱ ماه به‌ازای هر خانه) از Brennan.
- ⬜ ۱.۲ — پیاده‌سازی mode جدید `profections` → خروجی: profection سال جاری (حاکم خونه، تم سال)، profection ماه جاری، timeline سال آینده.
- ⬜ ۱.۳ — تحقیق: Firdaria (72 ساله، day/night chart) از Brennan + منابع هِلِنیستی.
- ⬜ ۱.۴ — پیاده‌سازی mode `firdaria` → دوره‌های فعلی + timeline.
- ⬜ ۱.۵ — تحقیق: تفسیر ترانزیت از Planets in Transit (Hand) — ساخت `data/transit_interpretations.json`: (سیاره ترانزیت‌کننده × سیاره ناتال × جنبه) → متن تفسیر. ~۹۰ سیاره‌جفت × ۵ جنبه اصلی.
- ⬜ ۱.۶ — اتصال تفسیرها به خروجی `transit` و `transit_natal_aspects`.
- ⬜ ۱.۷ — **mode جدید `timeline`** (مهم‌ترین خروجی موج): ورودی = بازه تاریخ (start/end، پیش‌فرض ۱۲ ماه آینده) → خروجی روایی مرتب‌شده:
  - ترانزیت‌های کلیدی (ورود سیاره کند به خانه ناتال، جنبه‌های tight، station ها) با تفسیر Hand
  - Profection سالانه/ماهانه فعال
  - Firdaria فعلی/تغییرها
  - (اگه ودیک فعال بود: dasha antardasha تغییرها)
  - خسوف/کسوف‌های روی محور ناتال
  - خروجی نهایی: لیست رویدادهای مرتب زمانی + روایت «فصل زندگی»
- ⬜ ۱.۸ — تفسیر progressions (خورشید/ماه progressed تغییر علامت، جنبه‌های progressed) از Forrest — غنی‌سازی mode `progressions`.
- ⬜ ۱.۹ — خسوف در پیشگویی: تفسیر eclipse روی درجه ناتال (Brady) → اضافه به خروجی `eclipses`.
- ⬜ ۱.۱۰ — بازنویسی/تفکیک `references/synastry-and-timing.md` → فایل جدید `references/forecasting.md` (مرجع تفسیر پیشگویی برای ایجنت).
- ⬜ ۱.۱۱ — تست + commit.

**معیار قبولی:** برای چارت تستی، `timeline` یک سال آینده رو با حداقل ۱۵ رویداد تفسیرشده و تاریخ دقیق بده.

---

## موج ۲ — ودیک پیشگویانه ⬜

هدف: عمق‌دادن به قوی‌ترین سیستم زمان‌بندی دنیا (dasha) و بستن بدهی‌های ودیک.

### منابع
| کتاب | نویسنده | چی می‌گیریم |
|------|---------|------------|
| **BPHS** جلد ۱–۲ (Santhanam) — ادامه | Parashara | Shadbala کامل، فصل‌های باقی‌مانده |
| **How to Judge a Horoscope** ج۱–۲ | B.V. Raman | قضاوت خانه‌به‌خانه — استاندارد طلایی |
| **Prashna Marga** ج۱–۲ | Kanakadhara (ترجمه B.V. Raman) | حوری ودیک کامل |
| **Tajika Neelakanti** | Neelakanta (ترجمه Raman) | ۱۶ Tajika yoga، sahams |
| **Muhurta Chintamani** | Ramacharya | انتخابال ودیک کامل |
| **Jataka Parijata** | Vaidyanatha | yogas و قضاوت |
| **300 Important Combinations** | B.V. Raman | کاتالوگ yoga |

### کارها
- ⬜ ۲.۱ — تحقیق: قاعده خواندن dasha (lord × خانه‌های حکومتی × خانه استقرار × dignity × yoga) از Raman → `references/vedic.md` بخش جدید.
- ⬜ ۲.۲ — پیاده‌سازی: تفسیر خودکار mahadasha/antardasha فعلی (متن روایی + تاریخ شروع/پایان) در خروجی vedic.
- ⬜ ۲.۳ — Shadbala ۶/۶ (اگه موج ۰ تموم نشده) + آستانه‌های تفسیری (قدرت نسبی، ishta/kashta phala).
- ⬜ ۲.۴ — گسترش yoga detection: Pancha Mahapurusha (5)، Dhana yogas، Raja yogas، Neecha Bhanga (تشخیص لغو debilitation) — از Raman + Jataka Parijata.
- ⬜ ۲.۵ — Tajika کامل: ۱۶ yogas تاجیکی (Ithasala, Ishrafa, …) + sahams — ارتقای mode `tajika`.
- ⬜ ۲.۶ — Prashna Marga: قواعد واقعی حوری ودیک (karakas بر اساس نوع سؤال، Tamasika/Jivasarpa و…) — ارتقای `prashna`.
- ⬜ ۲.۷ — Muhurta Chintamani: گسترش `muhurta` (چاندرا/تارا/یوگا/کارانا پنج‌عاملی کامل).
- ⬜ ۲.۸ — تست + commit.

**معیار قبولی:** خروجی vedic برای چارت تستی شامل تفسیر dasha فعلی + حداقل ۵ yoga تشخیص‌داده‌شده با منبع کلاسیک باشه.

---

## موج ۳ — Mundane / رویدادهای جهانی ⬜

هدف: «اتفاقات رو طبق ستاره‌شناسی تحلیل و پیش‌بینی کنه» — تحلیل رویدادهای جهانی (سیاسی/اقتصادی/طبیعی) و چارت کشورها.

### منابع
| کتاب | نویسنده | چی می‌گیریم |
|------|---------|------------|
| **Mundane Astrology** (The Ultimate Textbook) | Baigent, Campion, Harvey | مرجع کامل mundane مدرن |
| **The Book of World Horoscopes** | Nicholas Campion | چارت رسمی کشورها (داده) |
| Mundane Astrology (کلاسیک، public domain) | H.S. Green / Raphael | قواعد کلاسیک خانه‌ها/سیارات در mundane |
| **The Eagle and the Lark** (Brady — مشترک با موج ۱) | Brady | خسوف‌ها در mundane، Saros series |

### کارها
- ⬜ ۳.۱ — تحقیق: قواعد ingress (چارت ورود خورشید به برج حمل = سال کشور)، lunation (ماه نو/کامل به‌عنوان تم ماهانه)، خسوف جهانی، چرخه‌های بزرگ (Jupiter-Saturn ~20y، Saturn-Pluto، …).
- ⬜ ۳.۲ — `data/national_charts.json`: چارت ~۳۰ کشور کلیدی از Campion (ایران، آمریکا، چین، روسیه، اسرائیل، ترکیه، هند و…).
- ⬜ ۳.۳ — mode جدید `mundane_ingress`: چارت Aries ingress سال X برای کشور Y + تفسیر خانه‌به‌خانه.
- ⬜ ۳.۴ — mode جدید `eclipse_mundane`: خسوف/کسوف‌های پیش‌رو + سری Saros + تفسیر mundane (کجا دیده می‌شه → چه منطقه‌ای).
- ⬜ ۳.۵ — mode جدید `mundane_cycle`: وضعیت چرخه‌های بزرگ فعال (کجا هستیم در چرخه Jupiter-Saturn و…).
- ⬜ ۳.۶ — تلفیق: mode `mundane_report` = گزارش ماهانه جهانی (ingress ماهانه + lunation ها + خسوف + جنبه‌های آسمانی کلیدی) — سوخت پیش‌بینی‌های «اتفاقات».
- ⬜ ۳.۷ — `references/mundane.md` جدید: قواعد تفسیر برای ایجنت.
- ⬜ ۳.۸ — تست + commit.

**معیار قبولی:** `mundane_report` برای یک ماه آینده خروجی روایی با تاریخ‌های دقیق بده.

---

## موج ۴ — سینستری و روابط ⬜

هدف: عمق‌دادن به دومین درخواست پرسود (compatibility).

### منابع
| کتاب | نویسنده | چی می‌گیریم |
|------|---------|------------|
| **Aspects in Astrology** | Sue Tompkins | تفسیر جنبه (قبلاً مسدود بود — الان مجاز) |
| **Planets in Composite** | Robert Hand | تفسیر کامل composite |
| **Skymates: Love, Sex and Evolutionary Astrology** | Jodie & Steven Forrest | سینستری روایی |
| **The Astrology of Human Relationships** | Sakoian & Acker | inter-aspect interpretations |

### کارها
- ⬜ ۴.۱ — `data/synastry_interpretations.json`: (سیارهA × سیارهB × جنبه) → تفسیر — از Sakoian/Acker + Skymates.
- ⬜ ۴.۲ — اتصال به خروجی `synastry` و `compatibility` (تفسیر کنار هر inter-aspect).
- ⬜ ۴.۳ — تفسیر composite از Hand — اتصال به mode `composite`.
- ⬜ ۴.۴ — عمق Guna Milan: تفسیر هر koota جداگانه + راهکار (الان فقط امته).
- ⬜ ۴.۵ — `references/synastry-and-timing.md` بخش سینستری غنی‌سازی.
- ⬜ ۴.۶ — تست + commit.

---

## موج ۵ — فارسی‌سازی دانش ⬜

هدف: ایجنت فارسی‌زبان بدون ترجمه وسط-کار، مستقیم از رفرنس فارسی بخونه.

- ⬜ ۵.۱ — ساختار: `references/fa/` — نسخه فارسی هر فایل رفرنس (western, vedic, bazi, forecasting, mundane, synastry, health, consultation).
- ⬜ ۵.۲ — SKILL.md: قاعده انتخاب زبان رفرنس بر اساس زبان کاربر.
- ⬜ ۵.۳ — رشته‌های تفسیری data ها (transit_interpretations و…) — نسخه فارسی.
- ⬜ ۵.۴ — یکسان‌سازی اصطلاحات (واژه‌نامه فارسی-انگلیسی نجومی در `references/fa/glossary.md`).
- ⬜ ۵.۵ — تست: نمونه پاسخ فارسی با تمپلیت‌ها.

---

## موج ۶ — اعتبارسنجی و انتشار v3.0 ⬜

- ⬜ ۶.۱ — `tests/validation_charts.py`: چارت‌های Astro-Databank با رتبه AA (داده تولد معتبر) → مقایسه big-three/داشا با astro.com.
- ⬜ ۶.۲ — مقایسه خروجی ترانزیت/خسوف/ingress با Swiss Ephemeris خام.
- ⬜ ۶.۳ — به‌روزرسانی README + SKILL.md (نسخه ۳.۰، mode های جدید، مثال‌ها).
- ⬜ ۶.۴ — ریلیز v3.0 + تگ.

---

## 🔁 حلقه اجرای هر آیتم

```
تحقیق (استخراج قاعده از کتاب/سایت، ذخیره در references)
  → پیاده‌سازی (engine/data)
  → تست (unittest)
  → commit با پیام مشخص
  → تیک زدن در همین فایل
```

## 📌 تصمیمات ثابت

- هر تفسیر تولیدی باید **منبع** داشته باشه (نام کتاب/فصل) — در کامنت یا فیلد `source`.
- anti-Barnum: تفسیر Barnum-گونه (که به هر چارتی بخوره) ممنوع — قاعده موجود SKILL.md.
- هر mode جدید = حداقل ۲ تست.
- موج‌ها به ترتیب اجرا می‌شن؛ فقط موج ۰ می‌تونه وسط موج دیگه انجام بشه.
