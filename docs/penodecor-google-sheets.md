# PenodecorPro narx jadvali

Google Sheets narxlarning boshqaruv manbasi. Backend jadvalni o‘qiydi, yozmaydi.
Hisoblash har bir sahifada jadvalga chiqmaydi: u oxirgi tekshirilgan bazadagi
asl narxdan va alohida saqlangan umumiy foizdan foydalanadi.

Asl narx, tannarx va ishlab chiqarish xarajati foiz bilan qayta yozilmaydi.

```
yakuniy sotuv narxi = asl sotuv narxi × (1 + global_price_adjustment_percent / 100)
```

`+10` asl 500000 ni 550000 qiladi. `-10` 450000 qiladi. `0` asl narxni qaytaradi.
Foiz har safar asl narxdan qo‘llanadi. Qoplama koeffitsiyenti boshqa sozlama.

## Muhit o‘zgaruvchilari

Qiymatlarni repoga yozmang. Nomlari:

- `STORE_SHEETS_SPREADSHEET_ID` — jadval identifikatori
- `STORE_SHEETS_CREDENTIALS_FILE` — service account JSON faylining serverdagi yo‘li
- `STORE_SHEETS_SYNC_TOKEN` — qo‘lda sinxronlash uchun alohida kalit. Yuk tashish admin JWT ishlatilmaydi
- `STORE_SHEETS_SYNC_INTERVAL_SECONDS` — fon sinxroni. `0` bo‘lsa faqat qo‘lda. 60 dan kichik bo‘lsa ham kutish kamida 60 soniya
- `STORE_SHEETS_STALE_AFTER_SECONDS` — oxirgi muvaffaqiyatli sinxron bundan eski bo‘lsa, hisob eskirgan deb belgilanadi

Service account scope: `https://www.googleapis.com/auth/spreadsheets.readonly`.

Agar kalit yoki jadval sozlanmagan bo‘lsa, `/api/store/pricing/sync` va
`/api/store/pricing/sync-status` ochiq emas. Do‘kon hisobi bazadagi oxirgi
narx bilan davom etadi.

## Varaqlar

Birinchi qator ustun nomlari. Narxlar matn, o‘nlik nuqta `.`, valyutasiz.
Bo‘sh katak “narx yo‘q”. `0` va manfiy son rad etiladi. Ustun to‘plami aniq
mos kelishi kerak.

### Sozlamalar

`key`, `value`

- `global_price_adjustment_percent` — masalan `10`, `-10`, `0`, `+10%`
- `currency` — `UZS`
- `updated_at` — ISO vaqt, masalan `2026-10-02T10:00:00Z`

### Rom_Eshik

`product_slug`, `model`, `opening`, `size`, `cornice_price`, `jamb_price`,
`sill_price`, `extra_meter_cornice`, `extra_meter_jamb`, `extra_meter_sill`,
`addon_1_code`, `addon_1_price`, `addon_2_code`, `addon_2_price`, `is_active`

`opening`: `window` yoki `door`. `size`: `S`, `M`, `L`. Eshik qatorida podokonnik
bo‘lmaydi. Bir mahsulotning o‘lchamlari alohida qator.

### Pilastrlar

`product_slug`, `model`, `width_cm`, `thickness_cm`, `meter_price`,
`capital_model`, `capital_price`, `base_model`, `base_price`, `is_active`

En faqat 25, 30, 35, 40, 45, 50. Qalinlik faqat 3, 3.5, 4, 4.5, 5, 5.5, 6.
Ro‘yxatda yo‘q juftlik narxi taxmin qilinmaydi.

### Yumaloq_Ustunlar

`product_slug`, `model`, `meter_price`, `coating_multiplier`, `capital_model`,
`capital_min_diameter_cm`, `capital_max_diameter_cm`, `capital_price`,
`base_model`, `base_min_diameter_cm`, `base_max_diameter_cm`, `base_price`,
`is_active`

Diametr oralig‘i `[min, max)`. Oralig‘lar ustma-ust tushmasligi kerak.
Qoplama koeffitsiyenti umumiy foiz emas.

### Shift_Karnizlari

`product_slug`, `model`, `base_width_cm`, `base_meter_price`, `is_active`

`yangi metr narxi = tanlangan en / bazaviy en × bazaviy metr narxi`.
Qoplama koeffitsiyenti bu varaqda yo‘q.

### Shohona_Karnizlar

`product_slug`, `model`, `description`, `size_requirements`, `is_active`

Narx ustuni yo‘q. Sinxron va foiz individual narx yaratmaydi.

### Tayyor_Mahsulotlar

`product_slug`, `sku`, `selling_price`, `available_quantity`, `is_active`

`selling_price` asl sotuv narxi. Foizdan keyingi summa shu katakka yozilmaydi.
Sinxron tayyor mahsulotda faqat shu narxni yangilaydi. `available_quantity` va
mahsulotning `is_active` qiymati jadvaldan yozilmaydi. Narx qoidasining
`is_active` qiymati alohida va o‘z varag‘idagi konfiguratsiyaga mos yangilanadi.
Ustunlar baribir tekshiriladi: qoldiq `0` bo‘lishi mumkin, narx `0` bo‘lmaydi.
SKU do‘kondagi SKU bilan mos kelmasa butun sinxron to‘xtaydi.

Mahsulot identifikatori do‘kondagi `slug` bilan bir xil bo‘lishi kerak. Noma’lum
slug, takroriy qoida yoki yaroqsiz qator butun sinxronni to‘xtatadi. Oxirgi
muvaffaqiyatli narx saqlanadi. Jadvalda yo‘q mahsulotning narxi nolga
tushirilmaydi.

## Sinxronni tekshirish

1. Jadvalga yuqoridagi varaq va ustunlarni kiriting. Narxlarni o‘z asl
   raqamlaringiz bilan to‘ldiring.
2. Serverda uchta muhit o‘zgaruvchisini qo‘ying: jadval ID, credential fayl yo‘li,
   sinxron kaliti.
3. `POST /api/store/pricing/sync` so‘roviga `Authorization: Bearer <kalit>`
   yuboring.
4. `GET /api/store/pricing/sync-status` oxirgi muvaffaqiyat vaqtini ko‘rsatadi.
   Javobda kalit, credential va jadval ID bo‘lmaydi.
5. `POST /api/store/pricing/calculate` javobida `subtotal` asl sotuv jami,
   `total` foizdan keyingi jami. Komponent qatorlari asl narxda qoladi.
6. Shohona va narxi kiritilmagan kombinatsiya `total: null` qaytaradi.

Avtomatik testlar tarmoqqa chiqmaydi. Ular `MemorySheetSource` orqali shu
ustunlarni tekshiradi:

```bash
python3 -m pytest tests/test_store_sheet_sync.py tests/test_store_pricing.py
```
