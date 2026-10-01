# Penoplast profili — loy sarfi

DXF kesim chizmasidan penoplast (ko'pik) profiliga ketadigan loy (qoplama) massasini hisoblaydigan Streamlit dastur.

Bu papka alohida asbob. Logistika platformasi (`app/`, `webapp/`, Docker) ga tegmaydi.

## O'rnatish va ishga tushirish

```bash
cd loy-kalkulyator
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Test:

```bash
cd loy-kalkulyator
python -m pytest
```

Namuna DXF fayllar `samples/` da. Qayta yozish: `python -m src.samples`.

## Uch yuz qoidasi

Qoplama faqat **uchta yuzga** surtiladi: tepa va ikki yon. Devorga yopishadigan pastki tekis yuz qoplanmaydi.

1. Kontur `ezdxf` bilan o'qiladi. Yoy (bulge) uzunligi vatar emas — `ezdxf.path` egri chizig'i bo'yicha.
2. **Yopiq** kontur (yopiq polyline yoki yopiq yo'l): eng past gorizontal to'g'ri chiziq topiladi va umumiy perimetrdan ayiriladi.

   P_faol = P_jami − L_pastki

   L_pastki — Y_min dagi gorizontal to'g'ri kesmalar yig'indisi. Pastki yuz bir necha bo'lakka bo'lingan bo'lsa, ular qo'shiladi. Yoy va qiya qirra ayirilmaydi: pastki yoy — qoplanadigan geometriya.
3. **Ochiq** kontur: chizuvchi faqat qoplanadigan yo'lni chizgan. P_faol shu yo'l uzunligi, hech narsa ayirilmaydi.

Agar yopiq konturda Y_min da gorizontal kesma bo'lmasa, dastur taxmin qilmaydi: L_pastki = 0, P_jami ko'rinadi va ogohlantirish chiqadi — «pastki gorizontal chiziq topilmadi».

Tolerans taxminan **0.05 mm** (dag'al, juda baland chizmada bbox balandligining kichik ulushi, lekin 0.25 mm dan oshmaydi). Ozgina qiyalagan yuz jimgina pastki deb olinmaydi. Devor yuzi chizmada **eng past** (min Y) gorizontal qirra bo'lishi kerak.

Birlik: `$INSUNITS` millimetrga o'tkaziladi. Kod 0 (birliksiz) bo'lsa, millimetr deb qabul qilinadi va bu interfeysda yoziladi.

Detal nomi — yuklangan fayl nomi, kengaytmasiz.

## Formula

P_faol va d millimetrda. Detal uzunligi L = 2 m. Zichlik ρ = 1.95 kg/l. Texnik chiqindi 5%.

```
M_1 = (P_faol * d * 2 / 1000) * 1.95
M_jami = M_1 * N * 1.05
```

M_1 — bitta 2 metrlik detal uchun loy, kg. `(P * d * 2 / 1000)` — litr.

Qalinlik faqat **3.0**, **3.5** yoki **4.0** mm. Zichlik, uzunlik va 5% foydalanuvchi o'zgartira olmaydi.

### To'rtburchak misol

Yopiq to'rtburchak, eni 100 mm, bo'yi 50 mm.

- P_jami = 300 mm
- pastki qirra L_pastki = 100 mm
- P_faol = 200 mm
- d = 3.0 mm, N = 1
- M_1 = (200 * 3.0 * 2 / 1000) * 1.95 = **2.34 kg**
- M_jami = 2.34 * 1.05 = **2.457 kg**

Ochiq polyline 250 mm bo'lsa, P_faol = 250 mm, L_pastki = 0.

## Hisobot

Excel (`.xlsx`) va PDF dastur ichidan yuklab olinadi. Ikkisida ham detal qatorlari, jami va formula bor.
