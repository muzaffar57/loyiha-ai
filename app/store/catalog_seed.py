"""Boshlang‘ich katalog bo‘limlari.

Mahsulot, narx va qoldiq kiritilmaydi. Rustovka keyin administrator qo‘shadi.
"""
from sqlalchemy import text
from sqlalchemy.engine import Connection

SEED_CATEGORIES: list[dict] = [
    {
        "name": "Rom va eshik bezaklari",
        "slug": "rom-va-eshik",
        "description": "Deraza va eshik komplektlari, alohida elementlar va qo‘shimcha bezaklar. Qo‘shimcha uzunlik alohida hisoblanadi.",
        "sort_order": 10,
        "children": [
            {
                "name": "Deraza romlari",
                "slug": "deraza-romlari",
                "description": "Deraza atrofi uchun komplektlar.",
                "sort_order": 10,
            },
            {
                "name": "Eshik bezaklari",
                "slug": "eshik-bezaklari",
                "description": "Eshik uchun komplektlar.",
                "sort_order": 20,
            },
            {
                "name": "Alohida elementlar",
                "slug": "alohida-elementlar",
                "description": "Komplektga kirmaydigan qismlar va qo‘shimcha bezaklar.",
                "sort_order": 30,
            },
        ],
    },
    {
        "name": "Pilastrlar va ustunlar",
        "slug": "pilastrlar",
        "description": "Kapitel, tana va baza. Tana metr hisobida. En va qalinlik juftligining narxini administrator belgilaydi.",
        "sort_order": 20,
        "children": [
            {"name": "Kapitel", "slug": "pilastr-kapitel", "description": "Ustunning yuqori qismi.", "sort_order": 10},
            {"name": "Tana", "slug": "pilastr-tana", "description": "Tana metr hisobida sotiladi.", "sort_order": 20},
            {"name": "Baza", "slug": "pilastr-baza", "description": "Ustunning pastki qismi.", "sort_order": 30},
        ],
    },
    {
        "name": "Yumaloq ustunlar",
        "slug": "yumaloq-ustunlar",
        "description": "Mavjud quvur diametri yoki aylanasi va kerakli tashqi diametr bo‘yicha. Qoplama koeffitsiyenti administrator sozlaydi.",
        "sort_order": 30,
        "children": [
            {
                "name": "Tana",
                "slug": "yumaloq-ustun-tanasi",
                "description": "Balandlik va tashqi diametr bo‘yicha tana.",
                "sort_order": 10,
            },
            {
                "name": "Kapitel va baza",
                "slug": "yumaloq-kapitel-baza",
                "description": "Ixtiyoriy yuqori va pastki qismlar.",
                "sort_order": 20,
            },
        ],
    },
    {
        "name": "Shift karnizlari va belbog‘lar",
        "slug": "shift-karnizlari",
        "description": "Mijoz en va uzunlikni tanlaydi. Tayanch en va asosiy narx administratordan keladi.",
        "sort_order": 40,
        "children": [
            {
                "name": "Shift karnizi",
                "slug": "shift-karnizi",
                "description": "En va uzunlik bo‘yicha shift karnizi.",
                "sort_order": 10,
            },
            {
                "name": "Belbog‘",
                "slug": "belbog",
                "description": "En va uzunlik bo‘yicha belbog‘.",
                "sort_order": 20,
            },
        ],
    },
    {
        "name": "Shohona karnizlar",
        "slug": "shohona-karnizlar",
        "description": "Individual narx so‘rovi. Narxni administrator qo‘yadi, mijoz tasdiqlagach buyurtma yakunlanadi.",
        "sort_order": 50,
        "children": [],
    },
    {
        "name": "Tayyor mahsulotlar",
        "slug": "tayyor-mahsulotlar",
        "description": "Ombordagi tayyor bezaklar. SKU, o‘lcham, narx va qoldiq administrator kiritadi.",
        "sort_order": 60,
        "children": [],
    },
]


def seed_store_categories(connection: Connection) -> None:
    for root in SEED_CATEGORIES:
        root_id = _insert_category(connection, root, None)
        for child in root["children"]:
            _insert_category(connection, child, root_id)


def _insert_category(connection: Connection, row: dict, parent_id: int | None) -> int:
    existing = connection.execute(
        text("SELECT id FROM store_categories WHERE slug = :slug"),
        {"slug": row["slug"]},
    ).scalar_one_or_none()
    if existing is not None:
        return int(existing)
    inserted = connection.execute(
        text(
            """
            INSERT INTO store_categories
                (name, slug, description, image, is_active, sort_order, parent_id, created_at, updated_at)
            VALUES
                (:name, :slug, :description, NULL, :is_active, :sort_order, :parent_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
            """
        ),
        {
            "name": row["name"],
            "slug": row["slug"],
            "description": row["description"],
            "is_active": True,
            "sort_order": row["sort_order"],
            "parent_id": parent_id,
        },
    ).scalar_one()
    return int(inserted)
