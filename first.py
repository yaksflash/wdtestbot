import asyncio
import html
import os
import random
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Sequence

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, User
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ========== КОНФИГ ==========
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = [2014968485, 8711323474, 8408456955]

RESULTS_AUTO_DELETE_SECONDS = 30
SPIN_COST = 10
SPIN10_COST = 100
INITIAL_BALANCE = 100
BAN_DURATION_MINUTES = 2
BAN_CHANCE = 0.03
NOVICE_SPINS_THRESHOLD = 15
NOVICE_BALANCE_THRESHOLD = 80
NOVICE_WHITE_BONUS = 3
LUCK_BUFF_MINUTES = 5

DAILY_BONUS = 50
MAX_PROXIES_DEFAULT = 3
PROXY_QUOTA_UPGRADE_COST = 130
INCOME_INTERVAL = 60
RESET_LIMITS_HOUR = 0
SERVER_PURCHASE_BASE_COST = 70
SERVER_PURCHASE_SCALE_COST = 45
HOSTER_HOLD_MIN = 20
HOSTER_HOLD_MAX = 120
HOSTER_HOLD_SHARE = 0.25
VOID_SALE_MULTIPLIER = 0.35
IP_PROTECTION_COST_MULTIPLIER = 2.0
HOSTER_PROTECTION_MIN_COST = 120
RANDOM_EVENT_CHANCE = 0.11
RUSSIAN_ROULETTE_CHANCE = 0.012
SPIN_RANDOM_EVENT_CHANCE = 0.022
BACKGROUND_RANDOM_EVENT_CHANCE = 0.032
SERVER_PROTECTION_MIN_COST = 170
GOVERNMENT_IP_BASE_CHANCE = 0.0012
VPN_SERVICE_CREATE_COST = 320
VPN_DEFAULT_PRICE = 7
VPN_DEFAULT_MARKETING = 35
VPN_LEVEL_UPGRADE_BASE_COST = 180
MICROLOAN_RATE = 0.65
MICROLOAN_TERM_HOURS = 3
MICROLOAN_WARNING_MINUTES = 30

ROULETTE_GAMES: Dict[int, Dict[str, object]] = {}

HOSTER_CONFIGS = {
    "vk_cloud": {
        "label": "VK Cloud",
        "base_cost": 0,
        "ordinary_weight": 50,
        "white_bonus": 0,
        "jackpot_bonus": 0,
        "ban_modifier": 1.0,
    },
    "yandex_cloud": {
        "label": "Yandex Cloud",
        "base_cost": 0,
        "ordinary_weight": 50,
        "white_bonus": 0,
        "jackpot_bonus": 0,
        "ban_modifier": 0.96,
    },
    "ruvds": {
        "label": "RuVDS",
        "base_cost": 85,
        "ordinary_weight": 49,
        "white_bonus": 0,
        "jackpot_bonus": 0,
        "ban_modifier": 1.0,
    },
    "selectel": {
        "label": "Selectel",
        "base_cost": 145,
        "ordinary_weight": 46,
        "white_bonus": 2,
        "jackpot_bonus": 1,
        "ban_modifier": 0.35,
    },
    "majordomo": {
        "label": "Majordomo",
        "base_cost": 190,
        "ordinary_weight": 45,
        "white_bonus": 3,
        "jackpot_bonus": 1,
        "ban_modifier": 0.26,
    },
    "mws": {
        "label": "MWS",
        "base_cost": 250,
        "ordinary_weight": 43,
        "white_bonus": 4,
        "jackpot_bonus": 1,
        "ban_modifier": 0.18,
    },
    "timeweb": {
        "label": "Timeweb",
        "base_cost": 315,
        "ordinary_weight": 42,
        "white_bonus": 5,
        "jackpot_bonus": 2,
        "ban_modifier": 0.12,
    },
    "ihc": {
        "label": "IHC",
        "base_cost": 390,
        "ordinary_weight": 41,
        "white_bonus": 6,
        "jackpot_bonus": 2,
        "ban_modifier": 0.08,
    },
}

DEFAULT_HOSTERS = ("vk_cloud", "yandex_cloud")

IP_LIMITS_CONFIG = {
    "обычный": 10000,
    "белый_1": 500,
    "белый_2": 300,
    "белый_3": 150,
    "джекпот": 50,
    "гос_подсеть": 8,
}

IP_DROP_CONFIG = {
    "обычный": {
        "label": "Обычный IP",
        "description": "обычный IP (не белый)",
        "emoji": "🌐",
        "weight": 50,
        "marketable": False,
    },
    "белый_1": {
        "label": "Белый IP x1",
        "emoji": "📱",
        "weight": 10,
        "operators_count": 1,
        "marketable": True,
    },
    "белый_2": {
        "label": "Белый IP x2",
        "emoji": "📱",
        "weight": 4,
        "operators_count": 2,
        "marketable": True,
    },
    "белый_3": {
        "label": "Белый IP x3",
        "emoji": "📱",
        "weight": 1,
        "operators_count": 3,
        "marketable": True,
    },
    "джекпот": {
        "label": "Джекпот",
        "description": "ДЖЕКПОТ! Универсальный белый IP (все операторы)",
        "emoji": "🎰",
        "weight": 1,
        "marketable": True,
    },
    "гос_подсеть": {
        "label": "Гос. подсеть",
        "description": "очень редкий IP из государственной подсети",
        "emoji": "🏛",
        "weight": 0,
        "marketable": True,
    },
}

OPERATOR_CHOICES = {
    "mts": "МТС",
    "t2": "Т2",
    "megafon": "Мегафон",
    "beeline": "Билайн",
}

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

BULK_SELL_SELECTIONS: Dict[int, List[int]] = {}

# ========== БАЗА ДАННЫХ ==========
conn = sqlite3.connect("votes.db")
cursor = conn.cursor()


def ensure_column(table_name: str, column_name: str, definition: str):
    cursor.execute(f"PRAGMA table_info({table_name})")
    existing_columns = {row[1] for row in cursor.fetchall()}
    if column_name not in existing_columns:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS votes (
        vote_id INTEGER PRIMARY KEY AUTOINCREMENT,
        token TEXT UNIQUE,
        chat_id INTEGER,
        thread_id INTEGER,
        poll_message_id INTEGER,
        title TEXT,
        candidates TEXT,
        start_time TEXT,
        end_time TEXT,
        is_active INTEGER DEFAULT 1
    )
"""
)

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS user_votes (
        vote_id INTEGER,
        user_id INTEGER,
        candidate_index INTEGER,
        PRIMARY KEY (vote_id, user_id)
    )
"""
)

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS fake_votes (
        vote_id INTEGER,
        candidate_index INTEGER,
        fake_count INTEGER DEFAULT 0,
        PRIMARY KEY (vote_id, candidate_index)
    )
"""
)

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS admin_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vote_id INTEGER,
        action TEXT,
        details TEXT,
        timestamp TEXT
    )
"""
)

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        balance INTEGER DEFAULT 100,
        ban_until TEXT,
        last_activity TEXT,
        last_daily_bonus TEXT,
        proxy_quota INTEGER DEFAULT 3,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        display_nick TEXT
    )
"""
)

ensure_column("users", "balance", "INTEGER DEFAULT 100")
ensure_column("users", "ban_until", "TEXT")
ensure_column("users", "last_activity", "TEXT")
ensure_column("users", "last_daily_bonus", "TEXT")
ensure_column("users", "proxy_quota", f"INTEGER DEFAULT {MAX_PROXIES_DEFAULT}")
ensure_column("users", "username", "TEXT")
ensure_column("users", "first_name", "TEXT")
ensure_column("users", "last_name", "TEXT")
ensure_column("users", "display_nick", "TEXT")
ensure_column("users", "hoster_hold_amount", "INTEGER DEFAULT 0")
ensure_column("users", "hoster_hold_until", "TEXT")
ensure_column("users", "selected_hoster_account_id", "INTEGER")
ensure_column("users", "spin_streak", "INTEGER DEFAULT 0")
ensure_column("users", "last_spin_date", "TEXT")
ensure_column("users", "total_spins", "INTEGER DEFAULT 0")
ensure_column("users", "luck_buff_until", "TEXT")

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        ip_type TEXT,
        acquired_at TEXT,
        is_sold INTEGER DEFAULT 0
    )
"""
)
ensure_column("inventory", "usable_state", "TEXT DEFAULT 'ok'")
ensure_column("inventory", "confiscation_protected", "INTEGER DEFAULT 0")

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS market (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        seller_id INTEGER,
        inventory_id INTEGER,
        price INTEGER,
        status TEXT DEFAULT 'active',
        listed_at TEXT
    )
"""
)

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS ip_limits (
        ip_type TEXT PRIMARY KEY,
        max_count INTEGER,
        current_count INTEGER
    )
"""
)

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS proxies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        server_name TEXT,
        operators TEXT,
        active INTEGER DEFAULT 1,
        created_at TEXT
    )
"""
)
ensure_column("proxies", "purchase_cost", "INTEGER DEFAULT 0")
ensure_column("proxies", "bound_inventory_id", "INTEGER")
ensure_column("proxies", "confiscated_at", "TEXT")
ensure_column("proxies", "confiscation_protected", "INTEGER DEFAULT 0")

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS balance_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount INTEGER,
        reason TEXT,
        timestamp TEXT
    )
"""
)

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS moderators (
        user_id INTEGER PRIMARY KEY
    )
"""
)

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS hoster_accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        provider_key TEXT,
        purchase_price INTEGER DEFAULT 0,
        status TEXT DEFAULT 'active',
        acquired_at TEXT,
        suspended_until TEXT
    )
"""
)
ensure_column("hoster_accounts", "confiscation_protected", "INTEGER DEFAULT 0")

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS hoster_market (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        seller_id INTEGER,
        account_id INTEGER,
        price INTEGER,
        status TEXT DEFAULT 'active',
        listed_at TEXT
    )
"""
)

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS daily_contracts (
        user_id INTEGER PRIMARY KEY,
        target_drop_type TEXT,
        reward INTEGER,
        expires_at TEXT,
        status TEXT DEFAULT 'active',
        created_at TEXT
    )
"""
)

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS vpn_services (
        user_id INTEGER PRIMARY KEY,
        service_name TEXT,
        service_price INTEGER DEFAULT 7,
        marketing_budget INTEGER DEFAULT 35,
        customer_count INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        created_at TEXT,
        last_tick_at TEXT
    )
"""
)
ensure_column("vpn_services", "service_price", f"INTEGER DEFAULT {VPN_DEFAULT_PRICE}")
ensure_column("vpn_services", "marketing_budget", f"INTEGER DEFAULT {VPN_DEFAULT_MARKETING}")
ensure_column("vpn_services", "customer_count", "INTEGER DEFAULT 0")
ensure_column("vpn_services", "is_active", "INTEGER DEFAULT 1")
ensure_column("vpn_services", "created_at", "TEXT")
ensure_column("vpn_services", "last_tick_at", "TEXT")
ensure_column("vpn_services", "demand_modifier", "REAL DEFAULT 1.0")
ensure_column("vpn_services", "expense_modifier", "REAL DEFAULT 1.0")
ensure_column("vpn_services", "capacity_modifier", "REAL DEFAULT 1.0")
ensure_column("vpn_services", "event_label", "TEXT")
ensure_column("vpn_services", "event_until", "TEXT")
ensure_column("vpn_services", "service_level", "INTEGER DEFAULT 1")

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS vpn_server_links (
        proxy_id INTEGER PRIMARY KEY,
        owner_user_id INTEGER,
        service_user_id INTEGER,
        mode TEXT,
        rent_price INTEGER DEFAULT 0,
        created_at TEXT
    )
"""
)

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS vpn_server_market (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        seller_id INTEGER,
        proxy_id INTEGER,
        price INTEGER,
        status TEXT DEFAULT 'active',
        listed_at TEXT
    )
"""
)

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS microloans (
        user_id INTEGER PRIMARY KEY,
        principal INTEGER,
        total_due INTEGER,
        issued_at TEXT,
        due_at TEXT,
        status TEXT DEFAULT 'active',
        warned INTEGER DEFAULT 0,
        warning_sent_at TEXT
    )
"""
)
ensure_column("microloans", "status", "TEXT DEFAULT 'active'")
ensure_column("microloans", "warned", "INTEGER DEFAULT 0")
ensure_column("microloans", "warning_sent_at", "TEXT")

for admin_id in ADMIN_IDS:
    cursor.execute("INSERT OR IGNORE INTO moderators (user_id) VALUES (?)", (admin_id,))

for ip_type, max_count in IP_LIMITS_CONFIG.items():
    cursor.execute(
        """
        INSERT OR IGNORE INTO ip_limits (ip_type, max_count, current_count)
        VALUES (?, ?, ?)
    """,
        (ip_type, max_count, max_count),
    )

conn.commit()

active_votes: Dict[str, dict] = {}


# ========== FSM ==========
class AddProxyFSM(StatesGroup):
    waiting_name = State()


class VPNSetupFSM(StatesGroup):
    waiting_name = State()


class SellFSM(StatesGroup):
    waiting_price = State()


class BulkSellFSM(StatesGroup):
    waiting_ids = State()


class HosterSellFSM(StatesGroup):
    waiting_price = State()


class AdminUserFSM(StatesGroup):
    waiting_target = State()
    waiting_amount = State()
    waiting_ban_minutes = State()
    waiting_quota = State()
    waiting_nick = State()


# ========== ОБЩИЕ ХЕЛПЕРЫ ==========
def escape(value: object) -> str:
    return html.escape(str(value))


def format_dt(value: Optional[str]) -> str:
    if not value:
        return "неизвестно"
    return datetime.fromisoformat(value).strftime("%d.%m.%Y %H:%M")


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def is_moderator(user_id: int) -> bool:
    cursor.execute("SELECT 1 FROM moderators WHERE user_id=?", (user_id,))
    return cursor.fetchone() is not None


def log_admin_action(vote_id: int, action: str, details: str):
    cursor.execute(
        "INSERT INTO admin_log (vote_id, action, details, timestamp) VALUES (?, ?, ?, ?)",
        (vote_id, action, details, datetime.now().isoformat()),
    )
    conn.commit()


def ensure_user(user: User):
    now = datetime.now().isoformat()
    cursor.execute("SELECT 1 FROM users WHERE user_id=?", (user.id,))
    exists = cursor.fetchone() is not None

    if not exists:
        cursor.execute(
            """
            INSERT INTO users (
                user_id, balance, ban_until, last_activity, last_daily_bonus,
                proxy_quota, username, first_name, last_name, display_nick
            ) VALUES (?, ?, NULL, ?, NULL, ?, ?, ?, ?, NULL)
        """,
            (
                user.id,
                INITIAL_BALANCE,
                now,
                MAX_PROXIES_DEFAULT,
                user.username,
                user.first_name,
                user.last_name,
            ),
        )
    else:
        cursor.execute(
            """
            UPDATE users
            SET username=?, first_name=?, last_name=?, last_activity=?
            WHERE user_id=?
        """,
            (user.username, user.first_name, user.last_name, now, user.id),
        )

    conn.commit()
    ensure_default_hosters(user.id)
    grant_daily_bonus_if_available(user.id)


def get_user(user_id: int):
    cursor.execute(
        """
        SELECT balance, ban_until, last_activity, last_daily_bonus, proxy_quota
        FROM users
        WHERE user_id=?
    """,
        (user_id,),
    )
    row = cursor.fetchone()
    if row is None:
        now = datetime.now().isoformat()
        cursor.execute(
            """
            INSERT INTO users (
                user_id, balance, ban_until, last_activity, last_daily_bonus,
                proxy_quota, username, first_name, last_name, display_nick
            ) VALUES (?, ?, NULL, ?, NULL, ?, NULL, NULL, NULL, NULL)
        """,
            (user_id, INITIAL_BALANCE, now, MAX_PROXIES_DEFAULT),
        )
        conn.commit()
        ensure_default_hosters(user_id)
        return INITIAL_BALANCE, None, now, None, MAX_PROXIES_DEFAULT
    return row


def ensure_default_hosters(user_id: int):
    cursor.execute("SELECT COUNT(*) FROM hoster_accounts WHERE user_id=?", (user_id,))
    count = cursor.fetchone()[0]
    if count == 0:
        now = datetime.now().isoformat()
        for provider_key in DEFAULT_HOSTERS:
            cursor.execute(
                """
                INSERT INTO hoster_accounts (
                    user_id, provider_key, purchase_price, status, acquired_at, suspended_until
                ) VALUES (?, ?, 0, 'active', ?, NULL)
            """,
                (user_id, provider_key, now),
            )
        conn.commit()
    cursor.execute("SELECT selected_hoster_account_id FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    selected_id = row[0] if row else None
    if not selected_id:
        cursor.execute(
            """
            SELECT id
            FROM hoster_accounts
            WHERE user_id=? AND status='active'
            ORDER BY id ASC
            LIMIT 1
        """,
            (user_id,),
        )
        first = cursor.fetchone()
        if first:
            cursor.execute(
                "UPDATE users SET selected_hoster_account_id=? WHERE user_id=?",
                (first[0], user_id),
            )
            conn.commit()


def get_hoster_account(account_id: int):
    cursor.execute(
        """
        SELECT id, user_id, provider_key, purchase_price, status, acquired_at, suspended_until
        FROM hoster_accounts
        WHERE id=?
    """,
        (account_id,),
    )
    row = cursor.fetchone()
    if not row:
        return None
    suspended_until = row[6]
    if suspended_until and datetime.fromisoformat(suspended_until) <= datetime.now():
        cursor.execute(
            "UPDATE hoster_accounts SET status='active', suspended_until=NULL WHERE id=?",
            (account_id,),
        )
        conn.commit()
        row = (row[0], row[1], row[2], row[3], "active", row[5], None)
    return row


def get_user_hoster_accounts(user_id: int, active_only: bool = False):
    query = """
        SELECT id, user_id, provider_key, purchase_price, status, acquired_at, suspended_until
        FROM hoster_accounts
        WHERE user_id=?
    """
    if active_only:
        query += " AND status='active'"
    query += " ORDER BY id ASC"
    cursor.execute(query, (user_id,))
    rows = cursor.fetchall()
    return [get_hoster_account(row[0]) or row for row in rows]


def get_selected_hoster_account(user_id: int):
    ensure_default_hosters(user_id)
    cursor.execute("SELECT selected_hoster_account_id FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if not row or not row[0]:
        return None
    account = get_hoster_account(row[0])
    if account and account[1] == user_id and account[4] == "active":
        return account
    return None


def select_hoster_account(user_id: int, account_id: int) -> bool:
    account = get_hoster_account(account_id)
    if not account or account[1] != user_id or account[4] != "active":
        return False
    cursor.execute(
        "UPDATE users SET selected_hoster_account_id=? WHERE user_id=?",
        (account_id, user_id),
    )
    conn.commit()
    return True


def get_hoster_label(provider_key: str) -> str:
    return HOSTER_CONFIGS.get(provider_key, {}).get("label", provider_key)


def is_government_ip_type(ip_type: str) -> bool:
    return "государственной подсети" in ip_type.lower() or "гос." in ip_type.lower()


def is_special_ip_type(ip_type: str) -> bool:
    ip_lower = ip_type.lower()
    return "белый" in ip_lower or "джекпот" in ip_lower or is_government_ip_type(ip_type)


def get_hoster_buff_summary(provider_key: str) -> List[str]:
    config = HOSTER_CONFIGS[provider_key]
    parts = [f"обычные: {config['ordinary_weight']}"]
    if config["white_bonus"] > 0:
        parts.append(f"белые +{config['white_bonus']}")
    if config["jackpot_bonus"] > 0:
        parts.append(f"джекпот +{config['jackpot_bonus']}")
    if config["ban_modifier"] != 1.0:
        delta = round((config["ban_modifier"] - 1.0) * 100)
        sign = "+" if delta >= 0 else ""
        parts.append(f"риск бана {sign}{delta}%")
    if provider_key in {"mws", "timeweb", "ihc"}:
        parts.append("шанс гос-IP выше")
    return parts


def suspend_hoster_account(account_id: int, minutes: int):
    until = datetime.now() + timedelta(minutes=minutes)
    cursor.execute(
        "UPDATE hoster_accounts SET status='suspended', suspended_until=? WHERE id=?",
        (until.isoformat(), account_id),
    )
    conn.commit()


def get_weighted_spin_pool(provider_key: str):
    config = HOSTER_CONFIGS[provider_key]
    limits = get_ip_limits()
    weights = {
        "обычный": config["ordinary_weight"],
        "белый_1": IP_DROP_CONFIG["белый_1"]["weight"] + config["white_bonus"],
        "белый_2": IP_DROP_CONFIG["белый_2"]["weight"] + config["white_bonus"],
        "белый_3": IP_DROP_CONFIG["белый_3"]["weight"] + config["white_bonus"],
        "джекпот": IP_DROP_CONFIG["джекпот"]["weight"] + config["jackpot_bonus"],
    }
    available = []
    for ip_type, weight in weights.items():
        if limits.get(ip_type, 0) > 0:
            available.append((ip_type, limits[ip_type], max(1, weight)))
    return available


def get_weighted_spin_pool_for_user(provider_key: str, user_id: int):
    config = HOSTER_CONFIGS[provider_key]
    limits = get_ip_limits()
    white_bonus = config["white_bonus"]
    ordinary_weight = config["ordinary_weight"]
    jackpot_bonus = config["jackpot_bonus"]
    total_spins = get_total_spins(user_id)
    available_balance = get_available_balance(user_id)

    if total_spins < NOVICE_SPINS_THRESHOLD or available_balance <= NOVICE_BALANCE_THRESHOLD:
        white_bonus += NOVICE_WHITE_BONUS
        ordinary_weight = max(22, ordinary_weight - 4)

    if get_luck_buff_until(user_id):
        white_bonus += 2
        jackpot_bonus += 1
        ordinary_weight = max(20, ordinary_weight - 4)

    weights = {
        "обычный": ordinary_weight,
        "белый_1": IP_DROP_CONFIG["белый_1"]["weight"] + white_bonus,
        "белый_2": IP_DROP_CONFIG["белый_2"]["weight"] + white_bonus,
        "белый_3": IP_DROP_CONFIG["белый_3"]["weight"] + white_bonus,
        "джекпот": IP_DROP_CONFIG["джекпот"]["weight"] + jackpot_bonus,
    }
    available = []
    for ip_type, weight in weights.items():
        if limits.get(ip_type, 0) > 0:
            available.append((ip_type, limits[ip_type], max(1, weight)))
    return available


def create_hoster_account(user_id: int, provider_key: str, purchase_price: int) -> int:
    cursor.execute(
        """
        INSERT INTO hoster_accounts (
            user_id, provider_key, purchase_price, status, acquired_at, suspended_until
        ) VALUES (?, ?, ?, 'active', ?, NULL)
    """,
        (user_id, provider_key, purchase_price, datetime.now().isoformat()),
    )
    conn.commit()
    account_id = cursor.lastrowid
    if not get_selected_hoster_account(user_id):
        select_hoster_account(user_id, account_id)
    return account_id


def attempt_buy_hoster_account(user_id: int, provider_key: str, haggle: bool = False) -> Dict[str, object]:
    config = HOSTER_CONFIGS[provider_key]
    price = config["base_cost"]
    if haggle and price > 0:
        if random.random() < 0.55:
            price = max(1, round(price * random.uniform(0.82, 0.92)))
            outcome = "success"
        else:
            price = round(price * random.uniform(1.03, 1.12))
            outcome = "fail"
    else:
        outcome = "direct"

    available_balance = get_available_balance(user_id)
    if available_balance < price:
        return {"ok": False, "price": price, "outcome": outcome}

    add_balance(user_id, -price, f"Покупка аккаунта {get_hoster_label(provider_key)}")
    account_id = create_hoster_account(user_id, provider_key, price)
    return {"ok": True, "price": price, "outcome": outcome, "account_id": account_id}


def get_hoster_market_listings():
    cursor.execute(
        """
        SELECT m.id, m.seller_id, m.account_id, m.price, a.provider_key
        FROM hoster_market m
        JOIN hoster_accounts a ON a.id = m.account_id
        WHERE m.status='active'
        ORDER BY m.listed_at DESC, m.id DESC
    """
    )
    return cursor.fetchall()


def has_active_hoster_listing(account_id: int) -> bool:
    cursor.execute(
        "SELECT 1 FROM hoster_market WHERE account_id=? AND status='active'",
        (account_id,),
    )
    return cursor.fetchone() is not None


def create_hoster_market_listing(user_id: int, account_id: int, price: int) -> int:
    cursor.execute(
        """
        INSERT INTO hoster_market (seller_id, account_id, price, status, listed_at)
        VALUES (?, ?, ?, 'active', ?)
    """,
        (user_id, account_id, price, datetime.now().isoformat()),
    )
    conn.commit()
    return cursor.lastrowid


def get_hoster_market_item(listing_id: int):
    cursor.execute(
        "SELECT seller_id, account_id, price, status FROM hoster_market WHERE id=?",
        (listing_id,),
    )
    return cursor.fetchone()


def close_hoster_market_listing(listing_id: int, status: str = "sold"):
    cursor.execute("UPDATE hoster_market SET status=? WHERE id=?", (status, listing_id))
    conn.commit()


def delete_hoster_account(account_id: int):
    cursor.execute("DELETE FROM hoster_accounts WHERE id=?", (account_id,))
    conn.commit()


def get_vpn_service(user_id: int):
    cursor.execute(
        """
        SELECT user_id, service_name, service_price, marketing_budget, customer_count, is_active, created_at, last_tick_at,
               demand_modifier, expense_modifier, capacity_modifier, event_label, event_until, service_level
        FROM vpn_services
        WHERE user_id=?
    """,
        (user_id,),
    )
    return cursor.fetchone()


def create_vpn_service(user_id: int, service_name: str) -> bool:
    if get_vpn_service(user_id):
        return False
    if get_available_balance(user_id) < VPN_SERVICE_CREATE_COST:
        return False
    now = datetime.now().isoformat()
    add_balance(user_id, -VPN_SERVICE_CREATE_COST, f"Запуск VPN-сервиса {service_name}")
    cursor.execute(
        """
        INSERT INTO vpn_services (
            user_id, service_name, service_price, marketing_budget, customer_count, is_active, created_at, last_tick_at,
            demand_modifier, expense_modifier, capacity_modifier, event_label, event_until, service_level
        ) VALUES (?, ?, ?, ?, 0, 1, ?, ?, 1.0, 1.0, 1.0, NULL, NULL, 1)
    """,
        (user_id, service_name, VPN_DEFAULT_PRICE, VPN_DEFAULT_MARKETING, now, now),
    )
    conn.commit()
    return True


def update_vpn_service_settings(user_id: int, *, price: Optional[int] = None, marketing: Optional[int] = None, is_active: Optional[bool] = None):
    service = get_vpn_service(user_id)
    if not service:
        return
    service_price = max(3, min(18, int(price if price is not None else service[2])))
    marketing_budget = max(0, min(120, int(marketing if marketing is not None else service[3])))
    active_flag = int(is_active if is_active is not None else bool(service[5]))
    cursor.execute(
        """
        UPDATE vpn_services
        SET service_price=?, marketing_budget=?, is_active=?
        WHERE user_id=?
    """,
        (service_price, marketing_budget, active_flag, user_id),
    )
    conn.commit()


def get_vpn_level(service) -> int:
    if not service:
        return 0
    return int(service[13] or 1) if len(service) > 13 else 1


def get_vpn_level_upgrade_cost(level: int) -> int:
    return VPN_LEVEL_UPGRADE_BASE_COST + max(0, level - 1) * 140


def upgrade_vpn_level(user_id: int) -> bool:
    service = get_vpn_service(user_id)
    if not service:
        return False
    current_level = get_vpn_level(service)
    capacity = get_vpn_capacity(user_id)
    if capacity < current_level * 3:
        return False
    cost = get_vpn_level_upgrade_cost(current_level)
    if get_available_balance(user_id) < cost:
        return False
    add_balance(user_id, -cost, f"Улучшение уровня VPN до {current_level + 1}")
    cursor.execute(
        "UPDATE vpn_services SET service_level=COALESCE(service_level, 1)+1 WHERE user_id=?",
        (user_id,),
    )
    conn.commit()
    return True


def get_vpn_hourly_profit(user_id: int) -> int:
    service = get_vpn_service(user_id)
    if not service:
        return 0
    metrics = get_vpn_service_metrics(user_id, service)
    return int(metrics["hourly_profit"])


def get_vpn_event_state(user_id: int) -> Dict[str, object]:
    service = get_vpn_service(user_id)
    if not service:
        return {"demand_modifier": 1.0, "expense_modifier": 1.0, "capacity_modifier": 1.0, "event_label": None, "event_until": None}
    event_until = datetime.fromisoformat(service[12]) if service[12] else None
    if event_until and event_until <= datetime.now():
        cursor.execute(
            """
            UPDATE vpn_services
            SET demand_modifier=1.0, expense_modifier=1.0, capacity_modifier=1.0, event_label=NULL, event_until=NULL
            WHERE user_id=?
        """,
            (user_id,),
        )
        conn.commit()
        return {"demand_modifier": 1.0, "expense_modifier": 1.0, "capacity_modifier": 1.0, "event_label": None, "event_until": None}
    return {
        "demand_modifier": float(service[8] or 1.0),
        "expense_modifier": float(service[9] or 1.0),
        "capacity_modifier": float(service[10] or 1.0),
        "event_label": service[11],
        "event_until": event_until,
    }


def set_vpn_event_state(user_id: int, label: str, hours: int, demand_modifier: float = 1.0, expense_modifier: float = 1.0, capacity_modifier: float = 1.0):
    until = datetime.now() + timedelta(hours=hours)
    cursor.execute(
        """
        UPDATE vpn_services
        SET demand_modifier=?, expense_modifier=?, capacity_modifier=?, event_label=?, event_until=?
        WHERE user_id=?
    """,
        (demand_modifier, expense_modifier, capacity_modifier, label, until.isoformat(), user_id),
    )
    conn.commit()


def get_vpn_server_link(proxy_id: int):
    cursor.execute(
        """
        SELECT proxy_id, owner_user_id, service_user_id, mode, rent_price, created_at
        FROM vpn_server_links
        WHERE proxy_id=?
    """,
        (proxy_id,),
    )
    return cursor.fetchone()


def is_proxy_committed_to_vpn(proxy_id: int) -> bool:
    return get_vpn_server_link(proxy_id) is not None


def get_vpn_server_capacity_from_proxy(proxy_id: int) -> int:
    cursor.execute(
        "SELECT active, bound_inventory_id FROM proxies WHERE id=?",
        (proxy_id,),
    )
    row = cursor.fetchone()
    if not row or not row[0] or not row[1] or not is_inventory_usable_on_server(row[1]):
        return 0
    item = get_inventory_item(row[1])
    if not item:
        return 0
    ip_type = item[1]
    ip_lower = ip_type.lower()
    if is_government_ip_type(ip_type):
        return 10
    if "джекпот" in ip_lower:
        return 6
    operators = len(get_inventory_operators(ip_type))
    if operators >= 3:
        return 4
    if operators == 2:
        return 2
    if operators == 1:
        return 1
    return 0


def get_vpn_service_server_links(user_id: int):
    cursor.execute(
        """
        SELECT proxy_id, owner_user_id, service_user_id, mode, rent_price, created_at
        FROM vpn_server_links
        WHERE service_user_id=?
        ORDER BY proxy_id DESC
    """,
        (user_id,),
    )
    return cursor.fetchall()


def get_vpn_outgoing_server_links(user_id: int):
    cursor.execute(
        """
        SELECT proxy_id, owner_user_id, service_user_id, mode, rent_price, created_at
        FROM vpn_server_links
        WHERE owner_user_id=? AND service_user_id!=owner_user_id
        ORDER BY proxy_id DESC
    """,
        (user_id,),
    )
    return cursor.fetchall()


def get_vpn_server_rental_income_per_hour(user_id: int) -> int:
    total = 0
    for proxy_id, _, _, _, rent_price, _ in get_vpn_outgoing_server_links(user_id):
        if get_vpn_server_capacity_from_proxy(proxy_id) > 0:
            total += rent_price
    return total


def has_active_vpn_server_listing(proxy_id: int) -> bool:
    cursor.execute(
        "SELECT 1 FROM vpn_server_market WHERE proxy_id=? AND status='active'",
        (proxy_id,),
    )
    return cursor.fetchone() is not None


def get_active_vpn_server_listing(proxy_id: int):
    cursor.execute(
        """
        SELECT id, seller_id, proxy_id, price, status, listed_at
        FROM vpn_server_market
        WHERE proxy_id=? AND status='active'
        ORDER BY listed_at DESC, id DESC
        LIMIT 1
    """,
        (proxy_id,),
    )
    return cursor.fetchone()


def get_vpn_server_market_listings():
    cursor.execute(
        """
        SELECT m.id, m.seller_id, m.proxy_id, m.price, p.server_name
        FROM vpn_server_market m
        JOIN proxies p ON p.id = m.proxy_id
        WHERE m.status='active' AND p.active=1 AND p.bound_inventory_id IS NOT NULL
        ORDER BY m.listed_at DESC, m.id DESC
    """
    )
    return cursor.fetchall()


def get_vpn_server_market_item(listing_id: int):
    cursor.execute(
        """
        SELECT m.id, m.seller_id, m.proxy_id, m.price, m.status, p.server_name, p.bound_inventory_id
        FROM vpn_server_market m
        JOIN proxies p ON p.id = m.proxy_id
        WHERE m.id=?
    """,
        (listing_id,),
    )
    return cursor.fetchone()


def create_vpn_server_market_listing(user_id: int, proxy_id: int, price: int) -> int:
    cursor.execute(
        """
        INSERT INTO vpn_server_market (seller_id, proxy_id, price, status, listed_at)
        VALUES (?, ?, ?, 'active', ?)
    """,
        (user_id, proxy_id, price, datetime.now().isoformat()),
    )
    conn.commit()
    return cursor.lastrowid


def close_vpn_server_market_listing(listing_id: int, status: str = "leased"):
    cursor.execute("UPDATE vpn_server_market SET status=? WHERE id=?", (status, listing_id))
    conn.commit()


def get_vpn_server_suggested_rent(proxy_id: int) -> int:
    capacity = get_vpn_server_capacity_from_proxy(proxy_id)
    return max(3, 2 + capacity * 2)


def assign_proxy_to_vpn(user_id: int, proxy_id: int, mode: str) -> bool:
    service = get_vpn_service(user_id)
    proxy = next((item for item in get_user_proxies(user_id, active_only=True) if item[0] == proxy_id), None)
    if not service or not proxy or not proxy[6]:
        return False
    if has_active_vpn_server_listing(proxy_id):
        return False
    link = get_vpn_server_link(proxy_id)
    if link and not (link[1] == user_id and link[2] == user_id):
        return False
    if link:
        cursor.execute("UPDATE vpn_server_links SET mode=? WHERE proxy_id=?", (mode, proxy_id))
    else:
        cursor.execute(
            """
            INSERT INTO vpn_server_links (proxy_id, owner_user_id, service_user_id, mode, rent_price, created_at)
            VALUES (?, ?, ?, ?, 0, ?)
        """,
            (proxy_id, user_id, user_id, mode, datetime.now().isoformat()),
        )
    conn.commit()
    return True


def delete_vpn_service(user_id: int) -> bool:
    service = get_vpn_service(user_id)
    if not service:
        return False
    cursor.execute(
        """
        DELETE FROM vpn_server_links
        WHERE service_user_id=? AND (owner_user_id=? OR owner_user_id!=service_user_id)
    """,
        (user_id, user_id),
    )
    cursor.execute("DELETE FROM vpn_services WHERE user_id=?", (user_id,))
    conn.commit()
    return True


def remove_proxy_from_vpn(user_id: int, proxy_id: int) -> bool:
    cursor.execute(
        """
        DELETE FROM vpn_server_links
        WHERE proxy_id=? AND owner_user_id=? AND service_user_id=? 
    """,
        (proxy_id, user_id, user_id),
    )
    changed = cursor.rowcount > 0
    conn.commit()
    return changed


def lease_server_to_vpn(renter_id: int, listing_id: int) -> Optional[Dict[str, int]]:
    service = get_vpn_service(renter_id)
    item = get_vpn_server_market_item(listing_id)
    if not service or not item:
        return None
    _, seller_id, proxy_id, price, status, _, bound_inventory_id = item
    if seller_id == renter_id or status != "active" or not bound_inventory_id:
        return None
    if get_vpn_server_link(proxy_id):
        close_vpn_server_market_listing(listing_id, "cancelled")
        return None
    cursor.execute(
        """
        INSERT INTO vpn_server_links (proxy_id, owner_user_id, service_user_id, mode, rent_price, created_at)
        VALUES (?, ?, ?, 'leased_in', ?, ?)
    """,
        (proxy_id, seller_id, renter_id, price, datetime.now().isoformat()),
    )
    conn.commit()
    close_vpn_server_market_listing(listing_id, "leased")
    return {"seller_id": seller_id, "proxy_id": proxy_id, "price": price}


def release_leased_server(renter_id: int, proxy_id: int) -> bool:
    cursor.execute(
        """
        DELETE FROM vpn_server_links
        WHERE proxy_id=? AND service_user_id=? AND owner_user_id!=service_user_id
    """,
        (proxy_id, renter_id),
    )
    changed = cursor.rowcount > 0
    conn.commit()
    return changed


def get_vpn_capacity(user_id: int) -> int:
    capacity = 0
    event_state = get_vpn_event_state(user_id)
    for proxy_id, _, _, mode, _, _ in get_vpn_service_server_links(user_id):
        if mode not in {"service", "leased_in", "retail", "virtual"}:
            continue
        capacity += get_vpn_server_capacity_from_proxy(proxy_id)
    return max(0, round(capacity * float(event_state["capacity_modifier"])))


def get_vpn_service_metrics(user_id: int, service=None) -> Dict[str, int]:
    service = service or get_vpn_service(user_id)
    if not service:
        return {
            "capacity": 0,
            "target_customers": 0,
            "hourly_income": 0,
            "hourly_expenses": 0,
            "hourly_profit": 0,
            "leased_out_income": 0,
            "service_servers": 0,
            "leased_in_servers": 0,
            "level": 0,
            "level_upgrade_cost": get_vpn_level_upgrade_cost(1),
        }
    capacity = get_vpn_capacity(user_id)
    price = int(service[2])
    marketing = int(service[3])
    level = get_vpn_level(service)
    links = get_vpn_service_server_links(user_id)
    event_state = get_vpn_event_state(user_id)
    service_servers = sum(1 for _, owner_id, service_id, mode, _, _ in links if owner_id == service_id == user_id and mode in {"service", "retail", "virtual"})
    leased_in_servers = sum(1 for _, owner_id, service_id, mode, _, _ in links if owner_id != service_id and service_id == user_id and mode == "leased_in")
    marketing_pressure = min(0.34, marketing / 300) + min(0.12, max(0, marketing - 70) / 220)
    premium_penalty = max(0, price - 9) * 0.08 + max(0, price - 12) * 0.04
    cheap_penalty = max(0, 6 - price) * 0.03
    demand = 0.61 + marketing_pressure - premium_penalty - cheap_penalty
    demand += min(0.18, level * 0.022)
    demand *= float(event_state["demand_modifier"])
    demand = max(0.06, min(1.0, demand))
    target_customers = min(capacity, max(0, round(capacity * demand)))
    leased_out_income = get_vpn_server_rental_income_per_hour(user_id)
    infra_load = service_servers + leased_in_servers
    base_expenses = 7 + infra_load * (3 + max(0, level - 1)) + marketing // 9 + max(0, marketing - 95) // 6 + level * 4
    hourly_expenses = round(base_expenses * float(event_state["expense_modifier"]))
    hourly_income = target_customers * price if service[5] else 0
    return {
        "capacity": capacity,
        "target_customers": target_customers,
        "hourly_income": hourly_income,
        "hourly_expenses": hourly_expenses,
        "hourly_profit": hourly_income - hourly_expenses + leased_out_income if service[5] else -hourly_expenses + leased_out_income,
        "leased_out_income": leased_out_income,
        "service_servers": service_servers,
        "leased_in_servers": leased_in_servers,
        "level": level,
        "level_upgrade_cost": get_vpn_level_upgrade_cost(level),
    }


def settle_vpn_service(user_id: int) -> int:
    service = get_vpn_service(user_id)
    if not service:
        return 0
    last_tick = datetime.fromisoformat(service[7]) if service[7] else datetime.now()
    now = datetime.now()
    elapsed_hours = int((now - last_tick).total_seconds() // 3600)
    if elapsed_hours <= 0:
        return 0
    customer_count = int(service[4] or 0)
    total_delta = 0
    for _ in range(elapsed_hours):
        current_service = get_vpn_service(user_id)
        metrics = get_vpn_service_metrics(user_id, current_service)
        target = metrics["target_customers"]
        if current_service[5]:
            if customer_count < target:
                customer_count += min(max(1, metrics["capacity"] // 6), target - customer_count)
            elif customer_count > target:
                customer_count -= min(max(1, metrics["capacity"] // 5), customer_count - target)
            hourly_income = customer_count * int(current_service[2]) + metrics["leased_out_income"]
            hourly_expenses = metrics["hourly_expenses"]
        else:
            customer_count = max(0, customer_count - 1)
            hourly_income = metrics["leased_out_income"]
            hourly_expenses = max(3, metrics["hourly_expenses"] // 2)
        delta = hourly_income - hourly_expenses
        if delta != 0:
            add_balance(user_id, delta, f"Работа VPN-сервиса {current_service[1]}")
        total_delta += delta
    cursor.execute(
        "UPDATE vpn_services SET customer_count=?, last_tick_at=? WHERE user_id=?",
        (customer_count, now.isoformat(), user_id),
    )
    conn.commit()
    return total_delta


def apply_vpn_random_event(user_id: int) -> Optional[str]:
    service = get_vpn_service(user_id)
    if not service:
        return None
    event_state = get_vpn_event_state(user_id)
    if event_state["event_label"] or random.random() >= 0.014:
        return None
    roll = random.random()
    if roll < 0.22:
        set_vpn_event_state(user_id, "Сбой в платежной системе", 2, demand_modifier=0.86, expense_modifier=1.03, capacity_modifier=1.0)
        return "💳 Платежный шлюз лег: часть новых оплат не проходит, спрос немного просел."
    if roll < 0.40:
        set_vpn_event_state(user_id, "Потеря БД на мастер-сервере", 3, demand_modifier=0.74, expense_modifier=1.09, capacity_modifier=0.88)
        return "💾 На мастер-сервере потеряли часть базы: сервис просел, а восстановление требует денег."
    if roll < 0.60:
        set_vpn_event_state(user_id, "Обновление ТСПУ", 4, demand_modifier=0.84, expense_modifier=1.12, capacity_modifier=0.84)
        return "🧱 После обновления ТСПУ часть трафика режется сильнее обычного."
    if roll < 0.82:
        set_vpn_event_state(user_id, "Бойкот пользователей", 3, demand_modifier=0.68, expense_modifier=1.0, capacity_modifier=1.0)
        return "🚪 Пользователи устроили бойкот: отток есть, но без полного развала сервиса."
    if roll < 0.92:
        set_vpn_event_state(user_id, "Удачная интеграция оплаты", 2, demand_modifier=1.08, expense_modifier=0.96, capacity_modifier=1.0)
        return "🟢 Подключилась удачная платежная интеграция: оплачивать стало проще, маржа слегка выросла."
    set_vpn_event_state(user_id, "Хороший отзыв в канале", 2, demand_modifier=1.12, expense_modifier=1.0, capacity_modifier=1.0)
    return "📣 О вашем VPN внезапно хорошо отозвались в тематическом канале: пришел небольшой приток клиентов."

def get_drop_type_title(drop_type: str) -> str:
    mapping = {
        "белый_1": "Белый IP x1",
        "белый_2": "Белый IP x2",
        "белый_3": "Белый IP x3",
        "джекпот": "Джекпот",
        "гос_подсеть": "Гос. подсеть",
    }
    return mapping.get(drop_type, drop_type)


def get_or_create_daily_contract(user_id: int) -> Dict[str, object]:
    cursor.execute(
        """
        SELECT target_drop_type, reward, expires_at, status
        FROM daily_contracts
        WHERE user_id=?
    """,
        (user_id,),
    )
    row = cursor.fetchone()
    now = datetime.now()
    if row:
        target_drop_type, reward, expires_at, status = row
        expires_at_dt = datetime.fromisoformat(expires_at)
        if expires_at_dt > now:
            return {
                "target_drop_type": target_drop_type,
                "reward": reward,
                "expires_at": expires_at_dt,
                "status": status,
            }

    choices = [
        ("белый_1", 22),
        ("белый_2", 38),
        ("белый_3", 60),
        ("джекпот", 100),
    ]
    target_drop_type, reward = random.choice(choices)
    expires_at = (now + timedelta(days=1)).isoformat()
    cursor.execute(
        """
        INSERT OR REPLACE INTO daily_contracts (
            user_id, target_drop_type, reward, expires_at, status, created_at
        ) VALUES (?, ?, ?, ?, 'active', ?)
    """,
        (user_id, target_drop_type, reward, expires_at, now.isoformat()),
    )
    conn.commit()
    return {
        "target_drop_type": target_drop_type,
        "reward": reward,
        "expires_at": datetime.fromisoformat(expires_at),
        "status": "active",
    }


def complete_daily_contract(user_id: int) -> Optional[int]:
    contract = get_or_create_daily_contract(user_id)
    if contract.get("status") != "active":
        return 0
    cursor.execute(
        "UPDATE daily_contracts SET status='completed' WHERE user_id=?",
        (user_id,),
    )
    conn.commit()
    return contract["reward"]


def update_spin_streak(user_id: int) -> Dict[str, int]:
    cursor.execute("SELECT spin_streak, last_spin_date FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    streak = row[0] or 0
    last_spin_date = datetime.fromisoformat(row[1]).date() if row and row[1] else None
    today = datetime.now().date()
    if last_spin_date == today:
        return {"streak": streak, "bonus": 0}
    if last_spin_date == today - timedelta(days=1):
        streak += 1
    else:
        streak = 1

    bonus = 0
    if streak in (3, 7, 14):
        bonus = 20 if streak == 3 else 45 if streak == 7 else 90
        add_balance(user_id, bonus, f"Бонус за серию круток ({streak} дней)")

    cursor.execute(
        "UPDATE users SET spin_streak=?, last_spin_date=? WHERE user_id=?",
        (streak, datetime.now().isoformat(), user_id),
    )
    conn.commit()
    return {"streak": streak, "bonus": bonus}


def get_balance(user_id: int) -> int:
    balance, _, _, _, _ = get_user(user_id)
    return balance


def get_hoster_hold(user_id: int) -> Dict[str, Optional[object]]:
    cursor.execute(
        "SELECT hoster_hold_amount, hoster_hold_until FROM users WHERE user_id=?",
        (user_id,),
    )
    row = cursor.fetchone()
    if not row:
        return {"amount": 0, "until": None}
    amount, until_str = row
    if until_str:
        until = datetime.fromisoformat(until_str)
        if until <= datetime.now():
            cursor.execute(
                "UPDATE users SET hoster_hold_amount=0, hoster_hold_until=NULL WHERE user_id=?",
                (user_id,),
            )
            conn.commit()
            return {"amount": 0, "until": None}
        return {"amount": amount or 0, "until": until}
    return {"amount": amount or 0, "until": None}


def get_available_balance(user_id: int) -> int:
    hold = get_hoster_hold(user_id)
    return max(0, get_balance(user_id) - int(hold["amount"] or 0))


def set_balance(user_id: int, new_balance: int):
    cursor.execute("UPDATE users SET balance=? WHERE user_id=?", (new_balance, user_id))
    conn.commit()


def add_balance(user_id: int, amount: int, reason: str = "") -> int:
    new_balance = get_balance(user_id) + amount
    set_balance(user_id, new_balance)
    cursor.execute(
        """
        INSERT INTO balance_history (user_id, amount, reason, timestamp)
        VALUES (?, ?, ?, ?)
    """,
        (user_id, amount, reason, datetime.now().isoformat()),
    )
    conn.commit()
    return new_balance
