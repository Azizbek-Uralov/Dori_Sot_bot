# DorSotBot

Sog'liqni saqlash vositalari va vitaminlar sotadigan Telegram bot (naqd pul bilan yetkazib berish) + buyurtmalarni boshqarish uchun veb-admin panel.

- **Bot**: aiogram 3.x (long polling)
- **Admin panel**: FastAPI + Jinja2 (server-rendered, SPA emas)
- **DB**: PostgreSQL + SQLAlchemy 2.0 (async, asyncpg) + Alembic
- **Til**: bot va admin bildirishnomalari o'zbek/rus tillarida (i18n)

Ikkala jarayon (`bot/` va `admin/`) bitta umumiy `app/` paketini (config, DB, modellar, servislar, i18n) ishlatadi va bitta Postgres bazasiga ulanadi.

## Talablar

- Docker + Docker Compose (tavsiya etiladi) **yoki** Python 3.12+ va [uv](https://docs.astral.sh/uv/)
- Real ishlatish uchun: Telegram bot tokeni ([@BotFather](https://t.me/BotFather)dan), marketing kanal va admin guruh

## Tezkor start (Docker Compose)

```bash
# 1. .env faylini tayyorlang
cp .env.example .env
# .env faylini oching va kerakli qiymatlarni to'ldiring (quyidagi "`.env` sozlamalari" bo'limiga qarang)

# 2. Bazani ko'taring
docker compose up -d db

# 3. Migratsiyalarni qo'llang (schema yaratiladi)
docker compose run --rm migrate

# 4. Birinchi adminni yarating
docker compose run --rm admin uv run python -m scripts.create_admin --username admin --password <parol>

# 5. Bot va admin panelni ishga tushiring
docker compose up -d bot admin
```

Admin panel: `http://localhost:8000/login` (yoki `.env`dagi `ADMIN_PORT`).

Loglarni ko'rish uchun: `docker compose logs -f bot admin`.

> **Eslatma:** `docker-compose.yml`dagi `db` xizmati host'ning 5432-portini band qiladi. Agar mashinangizda allaqachon boshqa Postgres shu portda ishlab tursa (masalan, tizim xizmati sifatida), `docker-compose.yml`da `db`ning port mappingini (masalan `"5433:5432"`) o'zgartiring va `DATABASE_URL`/`TEST_DATABASE_URL`dagi portni ham moslashtiring.

## `.env` sozlamalari

`.env.example`ni `.env`ga nusxalab, quyidagilarni to'ldiring:

| O'zgaruvchi | Nima uchun | Devda default bo'ladimi |
|---|---|---|
| `DATABASE_URL` | Bot va admin ishlatadigan asosiy baza | Ha — compose bilan ishlaydi |
| `TEST_DATABASE_URL` | Faqat `pytest` uchun, alohida baza | Bazani qo'lda yaratish kerak (pastga qarang) |
| `BOT_TOKEN` | @BotFather'dan olingan token | Placeholder — ilova ishga tushadi, lekin Telegram'ga hech narsa yubormaydi |
| `MARKETING_CHANNEL_ID` | Obuna majburiy bo'lgan reklama kanali | Real kanal kerak, aks holda obuna tekshiruvi doim rad etadi |
| `ADMIN_GROUP_CHAT_ID` | Yangi buyurtma haqida xabar boradigan guruh | Real guruh kerak |
| `SUPPORT_CONTACT` | Foydalanuvchiga ko'rsatiladigan yordam kontakti | Ixtiyoriy |
| `ADMIN_SESSION_SECRET` | Admin panel sessiya cookie'sini imzolash uchun | **Production'da albatta o'zgartiring** |
| `ADMIN_SESSION_MAX_AGE_SECONDS` | Admin sessiyasi muddati | 28800 (8 soat) |
| `ADMIN_HOST` / `ADMIN_PORT` | Admin panel qaysi host/portda ishlaydi | 0.0.0.0:8000 |
| `MIN_ORDER_TOTAL` | Minimal buyurtma summasi (so'mda) | 50000 |

`BOT_TOKEN` placeholder holida qolsa ham loyiha butunlay ishga tushadi (import xato bermaydi) — faqat Telegram'ga haqiqiy so'rov yuborilganda jim log yozib, hech narsa qilmaydi. Bu real token bo'lmasa ham admin panelni va biznes-logikani sinash imkonini beradi.

### Haqiqiy bot tokenini olish (@BotFather)

1. Telegram'da [@BotFather](https://t.me/BotFather)ga o'ting.
2. `/newbot` yuboring, botga nom va username bering (username `bot` bilan tugashi shart).
3. BotFather sizga `123456789:ABC-DEF...` ko'rinishidagi token beradi — uni `.env`dagi `BOT_TOKEN`ga qo'ying.
4. `docker compose restart bot` (yoki `admin` — ikkalasi ham shu tokenni ishlatadi) qiling.

### Marketing kanal va admin guruh ID'sini topish

- **`MARKETING_CHANNEL_ID`**: agar kanal public bo'lsa, `@kanal_username` shaklida yozsa bo'ladi. Private kanal uchun raqamli ID kerak (`-100` bilan boshlanadi) — buni [@userinfobot](https://t.me/userinfobot) yoki [@RawDataBot](https://t.me/RawDataBot)ga kanaldan xabar forward qilib olishingiz mumkin.
  - **Muhim**: bot obunani tekshira olishi uchun (`getChatMember`) u kanalga **administrator** sifatida qo'shilgan bo'lishi kerak.
- **`ADMIN_GROUP_CHAT_ID`**: botni guruhga qo'shing, guruhda biror xabar yozing, so'ng [@RawDataBot](https://t.me/RawDataBot) yordamida yoki `https://api.telegram.org/bot<TOKEN>/getUpdates` orqali guruh `chat.id`sini toping (odatda `-100...` bilan boshlanadi).

## Migratsiyalar (Alembic)

Schema `app/models/*.py`dagi SQLAlchemy modellaridan Alembic orqali boshqariladi.

```bash
# Mavjud migratsiyalarni qo'llash (yangi environment'da birinchi qadam)
uv run alembic upgrade head

# Modelga o'zgartirish kiritgandan so'ng yangi migratsiya yaratish
uv run alembic revision --autogenerate -m "nimadir o'zgardi"
# — avtogenerate qilingan faylni CHECK constraint va enum nomlari to'g'riligini
#   qo'lda tekshirib chiqing (autogenerate ba'zan ularni o'tkazib yuboradi), keyin:
uv run alembic upgrade head
```

Docker Compose ichida buning o'rniga `docker compose run --rm migrate` ishlatiladi (bir martalik `alembic upgrade head` xizmati).

## Birinchi adminni yaratish

Admin panelda o'z-o'zidan ro'yxatdan o'tish yo'q (atayin) — birinchi admin CLI orqali yaratiladi:

```bash
uv run python -m scripts.create_admin --username admin --password <kuchli-parol> --full-name "Ism Familiya"
```

Keyingi adminlarni admin panelning o'zidan (`/admins`) qo'shish mumkin.

## Docker'siz ishga tushirish (venv + systemd)

```bash
uv sync
cp .env.example .env   # va to'ldiring, DATABASE_URL'ni mahalliy Postgres'ga ko'rsating

uv run alembic upgrade head
uv run python -m scripts.create_admin --username admin --password <parol>

# Ikkita alohida jarayon sifatida ishga tushirish:
uv run python -m bot.main
uv run uvicorn admin.main:app --host 0.0.0.0 --port 8000
```

Doimiy ishlashi uchun `systemd` unit fayllari (`/etc/systemd/system/dorsotbot-bot.service` va `dorsotbot-admin.service`):

```ini
[Unit]
Description=DorSotBot Telegram bot
After=network.target postgresql.service

[Service]
WorkingDirectory=/opt/dorSotBot
EnvironmentFile=/opt/dorSotBot/.env
ExecStart=/opt/dorSotBot/.venv/bin/python -m bot.main
Restart=always
User=dorsotbot

[Install]
WantedBy=multi-user.target
```

Admin uchun xuddi shunday, faqat `ExecStart` o'rniga:
`/opt/dorSotBot/.venv/bin/uvicorn admin.main:app --host 0.0.0.0 --port 8000`

So'ng: `sudo systemctl enable --now dorsotbot-bot dorsotbot-admin`.

## Testlar

Testlar mocklangan baza emas, **haqiqiy Postgres**ga qarshi ishlaydi (`app/config.py`dagi `settings.test_database_url`, `.env`dagi `TEST_DATABASE_URL`).

```bash
# Bir martalik: test bazasini yarating (asosiy DB bilan bir xil Postgres instansiyasida)
psql "$DATABASE_URL" -c "CREATE DATABASE dorsotbot_test;"   # yoki docker exec orqali

uv run pytest tests/ -v
```

Test suite har bir test oldidan `TRUNCATE ... CASCADE` bilan bazani tozalaydi, shuning uchun testlarni istalgancha marta qayta ishga tushirish xavfsiz. Hozircha `order_service`, `cart_service`, `delivery_service`, `catalog_service` uchun biznes-logika testlari mavjud (29 ta test).

## Zaxira nusxa (pg_dump cron)

```cron
# Har kuni soat 03:00 da backup olish
0 3 * * * docker exec <db-konteyner-nomi> pg_dump -U dorsotbot dorsotbot | gzip > /backups/dorsotbot_$(date +\%F).sql.gz
```

Eski backuplarni tozalash uchun `find /backups -name '*.sql.gz' -mtime +30 -delete` kabi qo'shimcha qator qo'shing.

## Muammolarni bartaraf etish

**Bot hech qanday xabarga javob bermayapti**
- `BOT_TOKEN` haqiqiy va to'g'ri ekanini tekshiring (`.env`, keyin konteynerni qayta ishga tushiring).
- `docker compose logs -f bot` orqali xatolarni ko'ring.
- Bot boshqa joyda (masalan, ikkinchi nusxada) polling qilib turmaganiga ishonch hosil qiling — aiogram bitta tokenga bir vaqtda faqat bitta `getUpdates` polling'ni ruxsat beradi.

**Obuna tekshiruvi ("Obuna bo'ling") doim rad etyapti**
- Bot `MARKETING_CHANNEL_ID`dagi kanalga **administrator** sifatida qo'shilganini tekshiring — aks holda `getChatMember` xato qaytaradi va tizim xavfsizlik uchun "obuna emas" deb hisoblaydi (fail closed).
- `MARKETING_CHANNEL_ID` formatini tekshiring: public kanal uchun `@username`, private uchun `-100...` raqamli ID.

**Admin guruhga yangi buyurtma xabari kelmayapti**
- Bot `ADMIN_GROUP_CHAT_ID`dagi guruhga qo'shilganligini tekshiring.
- `ADMIN_GROUP_CHAT_ID` `-100` bilan boshlanishi kerak (oddiy guruh emas, supergroup ID formati).
- Bu funksiya best-effort — xatolik faqat log'ga yoziladi, buyurtma baribir yaratiladi. Log'larda `notify_service` xatolarini qidiring.

**Migratsiya `alembic upgrade head` hech narsa qilmayapti**
- `migrations/versions/` papkasida fayl bor-yo'qligini tekshiring — agar bo'sh bo'lsa, hali birorta migratsiya generatsiya qilinmagan (`alembic revision --autogenerate -m "..."` bilan yarating).

**`pytest` baza xatosi bilan yiqilyapti**
- `TEST_DATABASE_URL`dagi baza haqiqatan mavjudligini tekshiring (`CREATE DATABASE dorsotbot_test;`) — test suite jadvallarni o'zi yaratadi, lekin bazaning o'zini yaratmaydi.
