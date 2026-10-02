# Yuk Tashish Platformasi — MVP (Backend + Telegram WebApp)

O'zbekiston bo'yicha yuk tashish (logistika) platformasi. Yuk beruvchilar
(shipper) yuk e'lonini joylashtiradi, tizim uni avtomatik ravishda Telegram
kanalga post qiladi, haydovchilar (driver) esa yo'nalish, mashina turi va
hajm bo'yicha filtrlab yuklarni ko'radi. Loyihada ikki qism bor:

- **`app/`** — FastAPI backend (API, baza, Telegram bot integratsiyasi)
- **`webapp/`** — Telegram Mini App (React frontend, foydalanuvchi shu orqali botni ochib ishlaydi)

## Texnologiyalar

- **Backend**: Python 3.12, FastAPI
- **Ma'lumotlar bazasi**: PostgreSQL + SQLAlchemy 2.0 (async) + Alembic (migratsiya)
- **Validatsiya**: Pydantic v2
- **Autentifikatsiya**: JWT (telefon raqami + parol)
- **Telegram**: Aiogram 3.x (yangi yuklarni kanalga avto-post qilish uchun)

## Loyiha strukturasi

```
app/
  core/       — sozlamalar (.env), xavfsizlik (parol xesh, JWT), Telegram initData tekshiruvi
  db/         — ma'lumotlar bazasiga ulanish
  models/     — SQLAlchemy modellari (User, Cargo, CargoPhoto, DriverOffer) va enum'lar
  schemas/    — Pydantic sxemalar (kirish/chiqish formatlari)
  crud/       — bazaga yozish/o'qish funksiyalari
  api/v1/     — API endpointlar (auth, cargos, driver-offers, admin)
  services/   — Telegram xizmati, masofa hisoblash xizmati
alembic/      — DB migratsiyalari
scripts/      — administrator yaratish skripti
media/        — yuklangan rasmlar shu yerda saqlanadi
webapp/       — Telegram Mini App (React + Vite frontend)
```

## Ishga tushirish — Docker orqali (tavsiya etiladi)

Bu usul eng oson: Python, PostgreSQL o'rnatish shart emas, hammasi Docker
ichida avtomatik ishlaydi. Kompyuterda faqat [Docker Desktop](https://www.docker.com/products/docker-desktop/)
o'rnatilgan bo'lishi kerak.

### 1. `.env` faylini tayyorlash

```bash
cp .env.example .env
```

Xohlasangiz, `.env` faylini ochib `SECRET_KEY`, `TELEGRAM_BOT_TOKEN`,
`TELEGRAM_CHANNEL_ID` qiymatlarini o'zgartiring (bo'lmasa ham ishlayveradi,
standart qiymatlar bilan).

### 2. Qurish va ishga tushirish

```bash
docker compose build
docker compose up -d
```

Bu bitta buyruq bilan **PostgreSQL** va **backend serveri** ikkisi ham
ishga tushadi (birinchi marta bazani migratsiya qilib, keyin serverni
ko'taradi).

### 3. Tekshirish

```bash
docker compose ps          # ikkala konteyner ham "Up" bo'lishi kerak
docker compose logs -f api # server loglarini ko'rish (Ctrl+C bilan chiqish)
```

Brauzerda oching: **http://localhost:8742/docs**

### 4. To'xtatish / tozalash

```bash
docker compose down        # to'xtatish (ma'lumotlar saqlanadi)
docker compose down -v     # to'xtatish + bazani butunlay tozalash
```

### Birinchi administratorni yaratish (Docker orqali)

```bash
docker compose exec api python -m scripts.create_admin +998901234567
```

## Railway'ga joylashtirish

1. Railway'da yangi loyiha yaratib, shu repo'ni ulaymiz -- Railway avtomatik
   ravishda ildizdagi `Dockerfile`ni topib, undan foydalanadi (`docker-compose.yml`
   Railway'da ishlatilmaydi, chunki Railway har bir xizmatni alohida boshqaradi).
2. Railway'dan **"Add PostgreSQL"** orqali baza xizmatini qo'shamiz -- Railway
   avtomatik ravishda `DATABASE_URL` muhit o'zgaruvchisini beradi (kodimiz uni
   avtomatik to'g'ri formatga o'giradi, qo'lda o'zgartirish shart emas).
3. Backend xizmatiga quyidagi muhit o'zgaruvchilarini qo'shamiz: `SECRET_KEY`
   (uzun, tasodifiy qiymat), `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHANNEL_ID`.
4. Railway `PORT` o'zgaruvchisini o'zi avtomatik beradi -- `Dockerfile`
   ichidagi buyruq shuni hisobga oladi, qo'shimcha sozlash kerak emas.

## Mahalliy (local, Docker'siz) ishga tushirish

Agar Docker o'rnatilmagan bo'lsa, quyidagi usul bilan ham ishga tushirish mumkin:

### 1. Muhitni tayyorlash

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. `.env` faylini sozlash

`.env.example` faylidan nusxa oling va o'zingizning qiymatlaringizni kiriting:

```bash
cp .env.example .env
```

`DATABASE_URL` — PostgreSQL manzili. `TELEGRAM_BOT_TOKEN` va
`TELEGRAM_CHANNEL_ID` bo'lmasa ham tizim ishlayveradi (faqat Telegram'ga
xabar yubormaydi, log yozadi).

### 3. Ma'lumotlar bazasini tayyorlash

PostgreSQL o'rnatilgan va ishga tushirilgan bo'lishi kerak. Keyin:

```bash
alembic upgrade head
```

Bu buyruq kerakli jadvallarni (`users`, `cargos`, `cargo_photos`) yaratadi.

### 4. Serverni ishga tushirish

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8742
```

Server ishga tushgandan so'ng, brauzerda oching:

- **Interaktiv hujjat (Swagger)**: `http://localhost:8742/docs` — shu yerda
  har bir API'ni tugmalar orqali sinab ko'rish mumkin, kod yozish shart emas.
- **Health-check**: `http://localhost:8742/health`

### 5. Birinchi administratorni yaratish

Obunani boshqarish uchun kamida bitta admin kerak. Avval oddiy foydalanuvchi
sifatida `/api/v1/auth/register` orqali ro'yxatdan o'tib, so'ngra:

```bash
python -m scripts.create_admin +998901234567
```

## API qisqacha

| Method | Yo'l | Vazifa |
|---|---|---|
| POST | `/api/v1/auth/register` | Ro'yxatdan o'tish |
| POST | `/api/v1/auth/login` | Kirish (JWT token olish) |
| POST | `/api/v1/cargos/` | Yangi yuk yaratish + Telegram post (faqat shipper) |
| GET | `/api/v1/cargos/` | Yuklar ro'yxati (filtr + sahifalash) |
| GET | `/api/v1/cargos/{id}` | Bitta yuk tafsiloti |
| GET | `/api/v1/cargos/mine` | Mening yuklarim (barcha statuslar) |
| PATCH | `/api/v1/cargos/{id}/status` | Status o'zgartirish (faqat egasi) |
| POST | `/api/v1/cargos/{id}/photos` | Yukka rasm biriktirish (faqat egasi) |
| POST | `/api/v1/driver-offers/` | Bo'sh transport e'loni yaratish + Telegram post (faqat driver) |
| GET | `/api/v1/driver-offers/` | Bo'sh transportlar ro'yxati (filtr + sahifalash) |
| GET | `/api/v1/driver-offers/{id}` | Bitta e'lon tafsiloti |
| GET | `/api/v1/driver-offers/mine` | Mening bo'sh transport e'lonlarim (barcha statuslar) |
| PATCH | `/api/v1/driver-offers/{id}/status` | E'lon statusini o'zgartirish (faqat egasi) |
| POST | `/api/v1/admin/users/{id}/subscription/extend` | Obunani uzaytirish (faqat admin) |
| GET | `/api/v1/auth/me` | Joriy foydalanuvchi ma'lumoti (token orqali) |
| POST | `/api/v1/auth/telegram/login` | Telegram WebApp orqali avtomatik kirish |
| POST | `/api/v1/auth/telegram/register` | Telegram WebApp orqali birinchi ro'yxatdan o'tish |
| GET | `/health` | Server holatini tekshirish |

## "Lahtak/qisman yuk" va "Bo'sh transport" tizimi

Real logistikada ko'p uchraydigan holat: haydovchining mashinasida bo'sh joy
bor va u boshqa (kichik/qisman) yuklarni ham qo'shib olishni xohlaydi.
Buning uchun ikki tomonlama funksiya qo'shildi:

- **`Cargo.load_type`** — yuk beruvchi o'z yukini `toliq_mashina` (butun
  mashina kerak) yoki `qisman_yuk`/lahtak (boshqa yuk bilan bo'lishish
  mumkin) deb belgilaydi.
- **`DriverOffer`** — haydovchi o'zi "bo'sh transport" e'lon qiladi: qayerdan
  qayerga ketayotgani (manzil ixtiyoriy — bo'sh qoldirilsa "istalgan
  yo'nalish" degani), mashinasida qancha bo'sh joy (kg/m3) borligi, qachon
  jo'nayotgani. Bu e'lon ham avtomatik Telegram kanalga
  "🚛 BO'SH TRANSPORT (LAHTAK)" belgisi bilan post qilinadi. Yuk beruvchilar
  shu ro'yxatni ko'rib, o'ziga mos haydovchini topadi.

## Muhim texnik qarorlar

- **Masofa (km)** — navigator dagi aniq yo'l (Yandex/Google API) pullik.
  Ikkala joyga ham GPS ulansa, pinlar orasidagi taxminiy yo'l km hisoblanadi;
  GPS bo'lmasa viloyat markazlari ishlatiladi (`app/services/distance.py`).
- **Telegram post** — ortish va tushirish GPS bo'lsa, postga Yandex Xaritalar
  havolalari qo'shiladi. Mini App yuk sahifasida ham xarita ochiladi.
- **Monetizatsiya** — `User.subscription_expires_at` maydoni tayyor, lekin
  hozircha barcha foydalanuvchilar cheksiz/bepul. Kelajakda faqat
  haydovchilar uchun obuna yoqiladi (yuk beruvchilar doim bepul qoladi).
- **Admin huquqi** hech qachon ochiq API orqali berilmaydi, faqat
  `scripts/create_admin.py` skripti orqali (server ichida) beriladi.

## Telegram WebApp (frontend) — `webapp/`

Bu foydalanuvchi ko'radigan qism — Telegram bot ichida ochiladigan Mini App.
Stack: **Vite + React + TypeScript + Tailwind CSS v4**, rasmiy
[Telegram WebApp JS SDK](https://core.telegram.org/bots/webapps) orqali.

### Auth qanday ishlaydi

1. Foydalanuvchi Telegram'da botni ochadi (Menu Button orqali WebApp ochiladi).
2. Telegram avtomatik `initData` (foydalanuvchi Telegram ID, ismi va h.k.,
   bot tokeni bilan raqamli imzolangan) beradi.
3. Frontend shu `initData`ni `/api/v1/auth/telegram/login`ga yuboradi.
   Backend imzoni (`HMAC-SHA256`) tekshiradi va agar bu Telegram ID avval
   ro'yxatdan o'tgan bo'lsa — darhol JWT token qaytaradi (parol so'ralmaydi).
4. Agar birinchi marta kirsa — foydalanuvchidan ism, telefon (Telegram'ning
   rasmiy "Contact Sharing" tugmasi orqali avtomatik olinadi) va rolini
   (yuk beruvchi/haydovchi) so'rab, `/api/v1/auth/telegram/register`ga
   yuboradi.
5. Olingan JWT token `localStorage`da saqlanadi va keyingi barcha so'rovlarga
   `Authorization: Bearer <token>` sifatida qo'shiladi.

### Lokal ishga tushirish

```bash
cd webapp
npm install
npm run dev
```

Server `http://localhost:5842` da ochiladi. `.env.development` faylida
`VITE_API_URL=http://localhost:8742` ko'rsatilgan (lokal backend'ga ulanadi).

**Muhim**: Telegram tashqarisida (oddiy brauzerda) ochilganda, ilova
avtomatik "test rejimi"ga o'tadi — bu holatda `TELEGRAM_MOCK_AUTH_ENABLED=true`
qilib qo'yilgan backend kerak bo'ladi (`.env` faylida), aks holda ro'yxatdan
o'tish ishlamaydi. **Production'da bu bayroq albatta `false` (yoki umuman
yo'q) bo'lishi kerak** — aks holda tekshiruvsiz kirish imkoni qoladi.

### Production build va joylashtirish

```bash
cd webapp
npm run build   # natija: webapp/dist/
```

`webapp/dist/` — statik fayllar, istalgan statik hosting'ga (Vercel, Netlify,
Railway static site) joylashtiriladi. Deploy qilishdan oldin
`.env.production` faylidagi `VITE_API_URL`ni haqiqiy backend manzilingizga
(Railway URL) moslashtiring.

### Yukni yopish

Faqat e'lonni joylagan odam Mini App'da **Yukni yopish** tugmasini bosadi.
Yopilgandan keyin:

- ilovada **YUK YOPILDI** tamg'asi chiqadi;
- telefon raqami yashiriladi (qo'ng'iroq tugmasi yo'qoladi);
- Telegram kanaldagi shu post avtomatik tahrirlanadi: **YUK YOPILDI**,
  raqam o'rniga «Mijoz raqami yashirilgan».

Eski e'lonlar (post ID saqlanmagan) kanalda tahrirlanmaydi — faqat yangi
e'lonlar uchun ishlaydi. Haydovchi e'lonlari uchun xuddi shu qoida:
**Transportni yopish**.

Ilova tayyor bo'lgandan keyin, [@BotFather](https://t.me/BotFather) orqali
botingizga Menu Button (`/setmenubutton`) qo'shib, WebApp URL'ini kiriting —
shundan keyin foydalanuvchilar botni ochganda to'g'ridan-to'g'ri ilova ochiladi.

## PenodecorPro do‘koni — `penodecor/`

Fasad bezaklari uchun alohida mijoz sayti (Vite + React + Tailwind). Yuk tashish
API va Telegram Mini App bilan aralashmaydi. Do‘kon API: `/api/store/`.
Ishga tushirish: `penodecor/README.md`. Port: `http://localhost:5852`.
