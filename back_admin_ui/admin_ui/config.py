import os
import httpx

# ручка /objects требует user_id, используем тестового «админа»
ADMIN_ID = 1


API_BASE_URL = os.getenv("API_BASE_URL", "http://backend:8000")  # в compose уже передан
DEFAULT_TIMEOUT = httpx.Timeout(10.0, read=30.0)  # коннект/писать/читать


ROLE_LABELS = {
    "admin": "Админ",
    "inspector": "Инспектор",
    "contractor": "Подрядчик",
}
ROLE_VALUES = ["admin", "inspector", "contractor"]  # как в RoleEnum

STATUS_ENUM = [
    "Выполнено",
    "В работе",
    "Не начато",
    "Приостановлено",
]

MENU = [
    ("users", "👷🏻‍♂️ Пользователи"),
    ("objects", "🏗️ Объекты"),
    ("checks", " 🔎 Проверки и инциденты"),
    ("reports", " 📄 Отчеты"),
    ("tools", "🛠️ Служебное"),
]
PAGES = {
    "users": {"icon": "👷🏻‍♂️", "label": "Пользователи"},
    "objects": {"icon": "🏗️", "label": "Объекты"},
    "checks": {"icon": "🔎", "label": "Проверки и инциденты"},
    "reports": {"icon": "📄", "label": "Очеты"},
    "tools": {"icon": "🛠️", "label": "Служебное"},
}
