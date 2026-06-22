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


def get_active_microloan(user_id: int):
    cursor.execute(
        """
        SELECT user_id, principal, total_due, issued_at, due_at, status, warned, warning_sent_at
        FROM microloans
        WHERE user_id=? AND status='active'
    """,
        (user_id,),
    )
    return cursor.fetchone()


def get_microloan_offer(amount: int) -> Dict[str, object]:
    amount = max(50, min(600, int(amount)))
    total_due = max(amount + 1, round(amount * (1 + MICROLOAN_RATE)))
    due_at = datetime.now() + timedelta(hours=MICROLOAN_TERM_HOURS)
    return {"amount": amount, "total_due": total_due, "due_at": due_at}


def issue_microloan(user_id: int, amount: int) -> Optional[Dict[str, object]]:
    if get_active_microloan(user_id):
        return None
    offer = get_microloan_offer(amount)
    cursor.execute(
        """
        INSERT OR REPLACE INTO microloans (
            user_id, principal, total_due, issued_at, due_at, status, warned, warning_sent_at
        ) VALUES (?, ?, ?, ?, ?, 'active', 0, NULL)
    """,
        (user_id, offer["amount"], offer["total_due"], datetime.now().isoformat(), offer["due_at"].isoformat()),
    )
    conn.commit()
    add_balance(user_id, offer["amount"], f"Микрозайм на {offer['amount']} монет")
    return offer


def repay_microloan(user_id: int) -> Optional[int]:
    loan = get_active_microloan(user_id)
    if not loan:
        return None
    total_due = int(loan[2])
    if get_available_balance(user_id) < total_due:
        return -1
    balance = add_balance(user_id, -total_due, f"Погашение микрозайма ({total_due} монет)")
    cursor.execute("UPDATE microloans SET status='repaid' WHERE user_id=?", (user_id,))
    conn.commit()
    return balance


def wipe_user_assets_for_microloan(user_id: int):
    cursor.execute("UPDATE market SET status='cancelled' WHERE seller_id=? AND status='active'", (user_id,))
    cursor.execute("UPDATE hoster_market SET status='cancelled' WHERE seller_id=? AND status='active'", (user_id,))
    cursor.execute("UPDATE vpn_server_market SET status='cancelled' WHERE seller_id=? AND status='active'", (user_id,))
    cursor.execute("UPDATE inventory SET usable_state='confiscated', is_sold=1 WHERE user_id=? AND is_sold=0", (user_id,))
    cursor.execute(
        "UPDATE proxies SET active=0, bound_inventory_id=NULL, confiscated_at=? WHERE user_id=? AND active=1",
        (datetime.now().isoformat(), user_id),
    )
    cursor.execute(
        "UPDATE hoster_accounts SET status='confiscated', suspended_until=NULL WHERE user_id=? AND status!='confiscated'",
        (user_id,),
    )
    cursor.execute("DELETE FROM vpn_server_links WHERE owner_user_id=? OR service_user_id=?", (user_id, user_id))
    cursor.execute("DELETE FROM vpn_services WHERE user_id=?", (user_id,))
    conn.commit()
    current_balance = get_balance(user_id)
    if current_balance > 0:
        add_balance(user_id, -current_balance, "Полное взыскание по просроченному микрозайму")
    elif current_balance < 0:
        set_balance(user_id, 0)
    cursor.execute("UPDATE users SET hoster_hold_amount=0, hoster_hold_until=NULL WHERE user_id=?", (user_id,))
    cursor.execute("UPDATE microloans SET status='defaulted' WHERE user_id=?", (user_id,))
    conn.commit()


def confiscate_all_user_assets(user_id: int, reason: str = "Полная конфискация администратором"):
    cursor.execute("UPDATE market SET status='cancelled' WHERE seller_id=? AND status='active'", (user_id,))
    cursor.execute("UPDATE hoster_market SET status='cancelled' WHERE seller_id=? AND status='active'", (user_id,))
    cursor.execute("UPDATE vpn_server_market SET status='cancelled' WHERE seller_id=? AND status='active'", (user_id,))
    cursor.execute("UPDATE inventory SET usable_state='confiscated', is_sold=1 WHERE user_id=? AND is_sold=0", (user_id,))
    cursor.execute(
        "UPDATE proxies SET active=0, bound_inventory_id=NULL, confiscated_at=? WHERE user_id=? AND active=1",
        (datetime.now().isoformat(), user_id),
    )
    cursor.execute(
        "UPDATE hoster_accounts SET status='confiscated', suspended_until=NULL WHERE user_id=? AND status!='confiscated'",
        (user_id,),
    )
    cursor.execute("DELETE FROM vpn_server_links WHERE owner_user_id=? OR service_user_id=?", (user_id, user_id))
    cursor.execute("DELETE FROM vpn_services WHERE user_id=?", (user_id,))
    cursor.execute("UPDATE users SET hoster_hold_amount=0, hoster_hold_until=NULL WHERE user_id=?", (user_id,))
    conn.commit()
    current_balance = get_balance(user_id)
    if current_balance > 0:
        add_balance(user_id, -current_balance, reason)
    elif current_balance < 0:
        set_balance(user_id, 0)
    conn.commit()


def build_balance_actions_menu(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    loan = get_active_microloan(user_id)
    if loan:
        builder.add(InlineKeyboardButton(text=f"💳 Погасить займ • {loan[2]}", callback_data="microloan_repay"))
    else:
        for amount in (100, 250, 500):
            builder.add(InlineKeyboardButton(text=f"⚠️ Микрозайм {amount}", callback_data=f"microloan_offer_{amount}"))
    builder.add(InlineKeyboardButton(text="◀️ Назад", callback_data="menu_main"))
    builder.adjust(1)
    return builder.as_markup()


async def notify_user(user_id: int, text: str, reply_markup: Optional[InlineKeyboardMarkup] = None):
    try:
        await bot.send_message(user_id, text, parse_mode="HTML", reply_markup=reply_markup)
    except Exception:
        return


def get_total_spins(user_id: int) -> int:
    cursor.execute("SELECT total_spins FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    return int(row[0] or 0) if row else 0


def increment_total_spins(user_id: int, amount: int = 1):
    cursor.execute(
        "UPDATE users SET total_spins=COALESCE(total_spins, 0)+? WHERE user_id=?",
        (amount, user_id),
    )
    conn.commit()


def get_luck_buff_until(user_id: int) -> Optional[datetime]:
    cursor.execute("SELECT luck_buff_until FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if not row or not row[0]:
        return None
    until = datetime.fromisoformat(row[0])
    if until <= datetime.now():
        cursor.execute("UPDATE users SET luck_buff_until=NULL WHERE user_id=?", (user_id,))
        conn.commit()
        return None
    return until


def apply_luck_buff(user_id: int, minutes: int = LUCK_BUFF_MINUTES):
    until = datetime.now() + timedelta(minutes=minutes)
    cursor.execute("UPDATE users SET luck_buff_until=? WHERE user_id=?", (until.isoformat(), user_id))
    conn.commit()


def get_inventory_state_label(usable_state: str) -> str:
    mapping = {
        "ok": "рабочий",
        "rkn_banned": "забанен РКН",
        "whitelist_revoked": "вылетел из белых списков",
        "confiscated": "конфискован",
    }
    return mapping.get(usable_state, usable_state)


def get_inventory_operators(ip_type: str) -> List[str]:
    ip_lower = ip_type.lower()
    if "джекпот" in ip_lower or is_government_ip_type(ip_type):
        return list(OPERATOR_CHOICES.values())
    return [operator for operator in OPERATOR_CHOICES.values() if operator.lower() in ip_lower]


def get_inventory_usable_state(inventory_id: int) -> str:
    cursor.execute("SELECT usable_state FROM inventory WHERE id=?", (inventory_id,))
    row = cursor.fetchone()
    return row[0] if row and row[0] else "ok"


def is_inventory_usable_on_server(inventory_id: int) -> bool:
    return get_inventory_usable_state(inventory_id) == "ok"


def set_inventory_usable_state(inventory_id: int, usable_state: str):
    cursor.execute("UPDATE inventory SET usable_state=? WHERE id=?", (usable_state, inventory_id))
    conn.commit()


def is_inventory_protected(inventory_id: int) -> bool:
    cursor.execute("SELECT confiscation_protected FROM inventory WHERE id=?", (inventory_id,))
    row = cursor.fetchone()
    return bool(row and row[0])


def protect_inventory_item(inventory_id: int):
    cursor.execute("UPDATE inventory SET confiscation_protected=1 WHERE id=?", (inventory_id,))
    conn.commit()


def is_hoster_account_protected(account_id: int) -> bool:
    cursor.execute("SELECT confiscation_protected FROM hoster_accounts WHERE id=?", (account_id,))
    row = cursor.fetchone()
    return bool(row and row[0])


def protect_hoster_account(account_id: int):
    cursor.execute("UPDATE hoster_accounts SET confiscation_protected=1 WHERE id=?", (account_id,))
    conn.commit()


def is_proxy_protected(proxy_id: int) -> bool:
    cursor.execute("SELECT confiscation_protected FROM proxies WHERE id=?", (proxy_id,))
    row = cursor.fetchone()
    return bool(row and row[0])


def protect_proxy(proxy_id: int):
    cursor.execute("UPDATE proxies SET confiscation_protected=1 WHERE id=?", (proxy_id,))
    conn.commit()


def get_ip_protection_cost(ip_type: str) -> int:
    return max(70, round(estimate_ip_base_price(ip_type) * IP_PROTECTION_COST_MULTIPLIER))


def get_hoster_protection_cost(account_id: int) -> int:
    account = get_hoster_account(account_id)
    if not account:
        return HOSTER_PROTECTION_MIN_COST
    return max(HOSTER_PROTECTION_MIN_COST, round(max(60, account[3]) * 1.8))


def get_proxy_protection_cost(proxy_id: int) -> int:
    cursor.execute("SELECT purchase_cost FROM proxies WHERE id=?", (proxy_id,))
    row = cursor.fetchone()
    paid_cost = row[0] if row and row[0] else 0
    return max(SERVER_PROTECTION_MIN_COST, round(max(90, paid_cost) * 1.9))


def transfer_balance(from_user_id: int, to_user_id: int, amount: int) -> bool:
    if amount <= 0 or from_user_id == to_user_id:
        return False
    if get_available_balance(from_user_id) < amount:
        return False
    add_balance(from_user_id, -amount, f"Перевод пользователю {get_user_display(to_user_id)}")
    add_balance(to_user_id, amount, f"Перевод от {get_user_display(from_user_id)}")
    return True


def update_activity(user_id: int):
    cursor.execute(
        "UPDATE users SET last_activity=? WHERE user_id=?",
        (datetime.now().isoformat(), user_id),
    )
    conn.commit()


def get_user_display(user_id: int) -> str:
    cursor.execute(
        "SELECT display_nick, username, first_name, last_name FROM users WHERE user_id=?",
        (user_id,),
    )
    row = cursor.fetchone()
    if not row:
        return str(user_id)
    display_nick, username, first_name, last_name = row
    if display_nick:
        return display_nick
    if username:
        return f"@{username}"
    if first_name:
        suffix = f" {last_name}" if last_name else ""
        return f"{first_name}{suffix}"
    return str(user_id)


def set_user_nick(user_id: int, nick: str):
    cursor.execute("UPDATE users SET display_nick=? WHERE user_id=?", (nick, user_id))
    conn.commit()


def find_user_id_by_handle(raw_handle: str) -> Optional[int]:
    handle = raw_handle.strip()
    if not handle:
        return None
    if handle.startswith("@"):
        handle = handle[1:]
    cursor.execute(
        """
        SELECT user_id
        FROM users
        WHERE LOWER(username)=LOWER(?) OR LOWER(display_nick)=LOWER(?)
        ORDER BY user_id ASC
        LIMIT 1
    """,
        (handle, handle),
    )
    row = cursor.fetchone()
    return row[0] if row else None


def is_user_active_last_week(user_id: int) -> bool:
    cursor.execute("SELECT last_activity FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if not row or not row[0]:
        return False
    return datetime.now() - datetime.fromisoformat(row[0]) <= timedelta(days=7)


def parse_user_lookup(raw_value: str) -> Optional[int]:
    value = raw_value.strip()
    if not value:
        return None
    if value.isdigit():
        return int(value)
    return find_user_id_by_handle(value)


def get_total_users_count() -> int:
    cursor.execute("SELECT COUNT(*) FROM users")
    return cursor.fetchone()[0]


def get_recent_users(limit: int = 10):
    cursor.execute(
        """
        SELECT user_id, username, first_name, last_name, balance, last_activity
        FROM users
        ORDER BY COALESCE(last_activity, '') DESC, user_id DESC
        LIMIT ?
    """,
        (limit,),
    )
    return cursor.fetchall()


def get_admin_stats() -> Dict[str, int]:
    cursor.execute("SELECT COUNT(*) FROM inventory WHERE is_sold=0")
    inventory_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM market WHERE status='active'")
    market_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM proxies WHERE active=1")
    proxy_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE ban_until IS NOT NULL AND ban_until > ?", (datetime.now().isoformat(),))
    banned_count = cursor.fetchone()[0]
    cursor.execute("SELECT COALESCE(SUM(balance), 0) FROM users")
    total_balance = cursor.fetchone()[0] or 0
    return {
        "users": get_total_users_count(),
        "inventory": inventory_count,
        "market": market_count,
        "proxies": proxy_count,
        "banned": banned_count,
        "balance": total_balance,
    }


def clear_user_ban(user_id: int):
    cursor.execute(
        """
        UPDATE users
        SET ban_until=NULL, hoster_hold_amount=0, hoster_hold_until=NULL
        WHERE user_id=?
    """,
        (user_id,),
    )
    conn.commit()


def set_user_ban_minutes(user_id: int, minutes: int):
    if minutes <= 0:
        clear_user_ban(user_id)
        return
    until = datetime.now() + timedelta(minutes=minutes)
    cursor.execute(
        "UPDATE users SET ban_until=?, hoster_hold_amount=0, hoster_hold_until=NULL WHERE user_id=?",
        (until.isoformat(), user_id),
    )
    conn.commit()


def set_user_proxy_quota(user_id: int, quota: int):
    cursor.execute("UPDATE users SET proxy_quota=? WHERE user_id=?", (max(0, quota), user_id))
    conn.commit()


def get_user_admin_snapshot(user_id: int) -> Optional[Dict[str, object]]:
    cursor.execute(
        """
        SELECT balance, ban_until, last_activity, last_daily_bonus, proxy_quota,
               username, first_name, last_name, display_nick,
               hoster_hold_amount, hoster_hold_until
        FROM users
        WHERE user_id=?
    """,
        (user_id,),
    )
    row = cursor.fetchone()
    if not row:
        return None
    balance, ban_until, last_activity, last_daily_bonus, proxy_quota, username, first_name, last_name, display_nick, hold_amount, hold_until = row
    cursor.execute("SELECT COUNT(*) FROM inventory WHERE user_id=? AND is_sold=0", (user_id,))
    inventory_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM proxies WHERE user_id=? AND active=1", (user_id,))
    proxies_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM market WHERE seller_id=? AND status='active'", (user_id,))
    market_count = cursor.fetchone()[0]
    return {
        "user_id": user_id,
        "balance": balance,
        "available_balance": get_available_balance(user_id),
        "ban_until": ban_until,
        "last_activity": last_activity,
        "last_daily_bonus": last_daily_bonus,
        "proxy_quota": proxy_quota,
        "username": username,
        "first_name": first_name,
        "last_name": last_name,
        "display_nick": display_nick,
        "hold_amount": hold_amount or 0,
        "hold_until": hold_until,
        "inventory_count": inventory_count,
        "proxies_count": proxies_count,
        "market_count": market_count,
    }


def can_receive_daily_bonus(user_id: int) -> bool:
    cursor.execute("SELECT last_daily_bonus FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if not row or not row[0]:
        return True
    return datetime.now() - datetime.fromisoformat(row[0]) >= timedelta(days=1)


def mark_daily_bonus_received(user_id: int):
    cursor.execute(
        "UPDATE users SET last_daily_bonus=? WHERE user_id=?",
        (datetime.now().isoformat(), user_id),
    )
    conn.commit()


def grant_daily_bonus_if_available(user_id: int) -> int:
    if not can_receive_daily_bonus(user_id):
        return 0
    add_balance(user_id, DAILY_BONUS, f"Ежедневный бонус {DAILY_BONUS} монет")
    mark_daily_bonus_received(user_id)
    return DAILY_BONUS


def is_banned(user_id: int) -> Optional[datetime]:
    _, ban_until_str, _, _, _ = get_user(user_id)
    if not ban_until_str:
        return None
    ban_until = datetime.fromisoformat(ban_until_str)
    if ban_until > datetime.now():
        return ban_until
    cursor.execute("UPDATE users SET ban_until=NULL WHERE user_id=?", (user_id,))
    conn.commit()
    return None


def ban_user(user_id: int, minutes: int):
    until = datetime.now() + timedelta(minutes=minutes)
    cursor.execute("UPDATE users SET ban_until=? WHERE user_id=?", (until.isoformat(), user_id))
    conn.commit()
    apply_hoster_hold(user_id, until)


def apply_hoster_hold(user_id: int, hold_until: datetime):
    current_balance = get_balance(user_id)
    hold_amount = max(HOSTER_HOLD_MIN, round(current_balance * HOSTER_HOLD_SHARE))
    hold_amount = min(hold_amount, HOSTER_HOLD_MAX, current_balance)
    cursor.execute(
        """
        UPDATE users
        SET hoster_hold_amount=?, hoster_hold_until=?
        WHERE user_id=?
    """,
        (hold_amount, hold_until.isoformat(), user_id),
    )
    conn.commit()


def get_ip_limits() -> Dict[str, int]:
    cursor.execute("SELECT ip_type, current_count FROM ip_limits")
    return {row[0]: row[1] for row in cursor.fetchall()}


def decrement_ip_limit(ip_type: str):
    cursor.execute(
        "UPDATE ip_limits SET current_count=current_count-1 WHERE ip_type=? AND current_count>0",
        (ip_type,),
    )
    conn.commit()


def reset_ip_limits():
    for ip_type, max_count in IP_LIMITS_CONFIG.items():
        cursor.execute(
            "UPDATE ip_limits SET current_count=? WHERE ip_type=?",
            (max_count, ip_type),
        )
    conn.commit()


def add_inventory(user_id: int, ip_type: str, usable_state: str = "ok") -> int:
    cursor.execute(
        """
        INSERT INTO inventory (user_id, ip_type, acquired_at, is_sold, usable_state, confiscation_protected)
        VALUES (?, ?, ?, 0, ?, 0)
    """,
        (user_id, ip_type, datetime.now().isoformat(), usable_state),
    )
    conn.commit()
    return cursor.lastrowid


def get_user_inventory(user_id: int, only_unsold: bool = True):
    query = """
        SELECT id, ip_type, acquired_at, is_sold, usable_state, confiscation_protected
        FROM inventory
        WHERE user_id=?
    """
    if only_unsold:
        query += " AND is_sold=0"
    query += " ORDER BY id DESC"
    cursor.execute(query, (user_id,))
    return cursor.fetchall()


def get_inventory_item(inventory_id: int):
    cursor.execute(
        """
        SELECT user_id, ip_type, is_sold, acquired_at, usable_state, confiscation_protected
        FROM inventory
        WHERE id=?
    """,
        (inventory_id,),
    )
    return cursor.fetchone()


def mark_inventory_sold(inventory_id: int):
    cursor.execute("UPDATE inventory SET is_sold=1 WHERE id=?", (inventory_id,))
    conn.commit()


def delete_inventory_item(inventory_id: int, user_id: int) -> bool:
    cursor.execute(
        """
        DELETE FROM inventory
        WHERE id=? AND user_id=? AND is_sold=0
    """,
        (inventory_id, user_id),
    )
    deleted = cursor.rowcount > 0
    conn.commit()
    return deleted


def get_ip_state_value_multiplier(usable_state: str) -> float:
    if usable_state == "ok":
        return 1.0
    if usable_state in {"rkn_banned", "whitelist_revoked"}:
        return 0.28
    return 0.0


def get_void_sale_price(ip_type: str, usable_state: str = "ok") -> int:
    value = estimate_ip_base_price(ip_type) * get_ip_state_value_multiplier(usable_state)
    return max(2, round(value * VOID_SALE_MULTIPLIER))


def sell_inventory_to_system(inventory_id: int, user_id: int) -> int:
    item = get_inventory_item(inventory_id)
    if not item:
        return 0
    owner_id, ip_type, is_sold, _, usable_state, _ = item
    if owner_id != user_id or is_sold:
        return 0
    if usable_state == "confiscated":
        return 0
    if has_active_listing(inventory_id) or get_server_bound_to_inventory(inventory_id):
        return 0
    payout = get_void_sale_price(ip_type, usable_state)
    mark_inventory_sold(inventory_id)
    add_balance(user_id, payout, f"Продажа IP #{inventory_id} системе")
    return payout


def create_market_listing(seller_id: int, inventory_id: int, price: int) -> int:
    cursor.execute(
        """
        INSERT INTO market (seller_id, inventory_id, price, status, listed_at)
        VALUES (?, ?, ?, 'active', ?)
    """,
        (seller_id, inventory_id, price, datetime.now().isoformat()),
    )
    conn.commit()
    return cursor.lastrowid


def get_active_market_listings():
    cursor.execute(
        """
        SELECT m.id, m.seller_id, m.inventory_id, m.price, i.ip_type
        FROM market m
        JOIN inventory i ON i.id = m.inventory_id
        WHERE m.status='active'
        ORDER BY m.listed_at DESC, m.id DESC
    """
    )
    return cursor.fetchall()


def get_user_market_listings(user_id: int):
    cursor.execute(
        """
        SELECT m.id, m.seller_id, m.inventory_id, m.price, i.ip_type
        FROM market m
        JOIN inventory i ON i.id = m.inventory_id
        WHERE m.status='active' AND m.seller_id=?
        ORDER BY m.listed_at DESC, m.id DESC
    """,
        (user_id,),
    )
    return cursor.fetchall()


def get_market_item(market_id: int):
    cursor.execute(
        """
        SELECT seller_id, inventory_id, price, status
        FROM market
        WHERE id=?
    """,
        (market_id,),
    )
    return cursor.fetchone()


def get_market_item_details(market_id: int):
    cursor.execute(
        """
        SELECT m.id, m.seller_id, m.inventory_id, m.price, m.status, i.ip_type, i.acquired_at, i.usable_state
        FROM market m
        JOIN inventory i ON i.id = m.inventory_id
        WHERE m.id=?
    """,
        (market_id,),
    )
    return cursor.fetchone()


def close_market_listing(market_id: int):
    cursor.execute("UPDATE market SET status='sold' WHERE id=?", (market_id,))
    conn.commit()


def cancel_market_listing(market_id: int, seller_id: int) -> bool:
    cursor.execute(
        """
        UPDATE market
        SET status='cancelled'
        WHERE id=? AND seller_id=? AND status='active'
    """,
        (market_id, seller_id),
    )
    updated = cursor.rowcount > 0
    conn.commit()
    return updated


def has_active_listing(inventory_id: int) -> bool:
    cursor.execute(
        "SELECT 1 FROM market WHERE inventory_id=? AND status='active'",
        (inventory_id,),
    )
    return cursor.fetchone() is not None


def get_proxy_quota(user_id: int) -> int:
    _, _, _, _, quota = get_user(user_id)
    return quota


def get_proxy_quota_upgrade_cost(user_id: int) -> int:
    extra_slots = max(0, get_proxy_quota(user_id) - MAX_PROXIES_DEFAULT)
    return PROXY_QUOTA_UPGRADE_COST + extra_slots * 75


def get_server_purchase_cost(user_id: int) -> int:
    servers_count = len(get_user_proxies(user_id, active_only=True))
    return SERVER_PURCHASE_BASE_COST + servers_count * SERVER_PURCHASE_SCALE_COST


def upgrade_proxy_quota(user_id: int) -> bool:
    upgrade_cost = get_proxy_quota_upgrade_cost(user_id)
    balance = get_available_balance(user_id)
    if balance < upgrade_cost:
        return False
    new_quota = get_proxy_quota(user_id) + 1
    add_balance(user_id, -upgrade_cost, f"Повышение квоты серверов до {new_quota}")
    cursor.execute("UPDATE users SET proxy_quota=? WHERE user_id=?", (new_quota, user_id))
    conn.commit()
    return True


def get_user_proxies(user_id: int, active_only: bool = True):
    query = """
        SELECT id, server_name, operators, active, created_at, purchase_cost, bound_inventory_id
        FROM proxies
        WHERE user_id=?
    """
    if active_only:
        query += " AND active=1"
    query += " ORDER BY id DESC"
    cursor.execute(query, (user_id,))
    return cursor.fetchall()


def add_proxy(user_id: int, server_name: str, operators: str) -> int:
    purchase_cost = get_server_purchase_cost(user_id)
    available_balance = get_available_balance(user_id)
    if available_balance < purchase_cost:
        return 0
    add_balance(user_id, -purchase_cost, f"Покупка сервера {server_name}")
    cursor.execute(
        """
        INSERT INTO proxies (user_id, server_name, operators, active, created_at, purchase_cost, bound_inventory_id)
        VALUES (?, ?, ?, 1, ?, ?, NULL)
    """,
        (user_id, server_name, operators, datetime.now().isoformat(), purchase_cost),
    )
    conn.commit()
    return cursor.lastrowid


def get_proxy_void_sale_price(purchase_cost: int) -> int:
    return max(10, round(purchase_cost * 0.28))


def remove_proxy(proxy_id: int, user_id: int) -> int:
    cursor.execute(
        """
        SELECT purchase_cost
        FROM proxies
        WHERE id=? AND user_id=? AND bound_inventory_id IS NULL
    """,
        (proxy_id, user_id),
    )
    row = cursor.fetchone()
    if not row:
        return 0
    payout = get_proxy_void_sale_price(row[0] or 0)
    cursor.execute(
        "DELETE FROM proxies WHERE id=? AND user_id=? AND (bound_inventory_id IS NULL)",
        (proxy_id, user_id),
    )
    deleted = cursor.rowcount > 0
    if deleted:
        add_balance(user_id, payout, f"Продажа сервера #{proxy_id} системе")
    conn.commit()
    return payout if deleted else 0


def get_server_bound_to_inventory(inventory_id: int):
    cursor.execute(
        """
        SELECT id, user_id, server_name
        FROM proxies
        WHERE bound_inventory_id=?
    """,
        (inventory_id,),
    )
    return cursor.fetchone()


def get_bindable_inventory(user_id: int):
    items = []
    for item_id, ip_type, acquired_at, is_sold, usable_state, _ in get_user_inventory(user_id, only_unsold=True):
        if not is_special_ip_type(ip_type):
            continue
        if usable_state != "ok":
            continue
        if has_active_listing(item_id):
            continue
        if get_server_bound_to_inventory(item_id):
            continue
        items.append((item_id, ip_type, acquired_at, is_sold, usable_state))
    return items


def bind_ip_to_server(proxy_id: int, user_id: int, inventory_id: int) -> bool:
    server = next((item for item in get_user_proxies(user_id, active_only=True) if item[0] == proxy_id), None)
    if not server or server[6]:
        return False
    item = get_inventory_item(inventory_id)
    if not item:
        return False
    owner_id, ip_type, is_sold, _, usable_state, _ = item
    if owner_id != user_id or is_sold:
        return False
    if not is_special_ip_type(ip_type):
        return False
    if usable_state != "ok":
        return False
    if has_active_listing(inventory_id) or get_server_bound_to_inventory(inventory_id):
        return False
    cursor.execute(
        "UPDATE proxies SET bound_inventory_id=? WHERE id=? AND user_id=?",
        (inventory_id, proxy_id, user_id),
    )
    changed = cursor.rowcount > 0
    conn.commit()
    return changed


def unbind_ip_from_server(proxy_id: int, user_id: int) -> bool:
    cursor.execute(
        """
        UPDATE proxies
        SET bound_inventory_id=NULL
        WHERE id=? AND user_id=? AND bound_inventory_id IS NOT NULL
    """,
        (proxy_id, user_id),
    )
    changed = cursor.rowcount > 0
    conn.commit()
    return changed


def calculate_income_for_ip(ip_type: str) -> int:
    ip_lower = ip_type.lower()
    if is_government_ip_type(ip_type):
        return 18
    if "джекпот" in ip_lower:
        return 11
    operators = sum(1 for operator in OPERATOR_CHOICES.values() if operator.lower() in ip_lower)
    if operators >= 3:
        return 7
    if operators == 2:
        return 5
    if operators == 1:
        return 3
    return 0


def calculate_income_for_proxy(bound_inventory_id: Optional[int]) -> int:
    if not bound_inventory_id:
        return 0
    if not is_inventory_usable_on_server(bound_inventory_id):
        return 0
    item = get_inventory_item(bound_inventory_id)
    if not item:
        return 0
    return calculate_income_for_ip(item[1])


def get_proxy_income_per_hour(user_id: int) -> int:
    total = 0
    for item in get_user_proxies(user_id, active_only=True):
        if is_proxy_committed_to_vpn(item[0]):
            continue
        total += calculate_income_for_proxy(item[6])
    return total


def get_total_income_per_hour(user_id: int) -> int:
    total = get_proxy_income_per_hour(user_id)
    if get_vpn_service(user_id):
        total += get_vpn_hourly_profit(user_id)
    else:
        total += get_vpn_server_rental_income_per_hour(user_id)
    return total


def get_inventory_stats(user_id: int) -> Dict[str, int]:
    items = get_user_inventory(user_id, only_unsold=True)
    stats = {"total": len(items), "white": 0, "ordinary": 0, "broken": 0}
    for _, ip_type, _, _, usable_state, _ in items:
        if is_special_ip_type(ip_type):
            stats["white"] += 1
        else:
            stats["ordinary"] += 1
        if usable_state != "ok":
            stats["broken"] += 1
    return stats


def estimate_ip_base_price(ip_type: str) -> int:
    ip_lower = ip_type.lower()
    if is_government_ip_type(ip_type):
        return 260
    if "джекпот" in ip_lower:
        return 110
    operators_count = sum(1 for name in OPERATOR_CHOICES.values() if name.lower() in ip_lower)
    if operators_count >= 3:
        return 72
    if operators_count == 2:
        return 45
    if operators_count == 1:
        return 26
    return 20


def get_market_price_stats(ip_type: str) -> Dict[str, Optional[int]]:
    cursor.execute(
        """
        SELECT price
        FROM market m
        JOIN inventory i ON i.id = m.inventory_id
        WHERE m.status='active' AND i.ip_type=?
        ORDER BY price ASC
    """,
        (ip_type,),
    )
    prices = [row[0] for row in cursor.fetchall()]
    if not prices:
        return {"count": 0, "min": None, "max": None, "avg": None}
    avg_price = round(sum(prices) / len(prices))
    return {"count": len(prices), "min": prices[0], "max": prices[-1], "avg": avg_price}


def get_sell_price_suggestion(ip_type: str, usable_state: str = "ok") -> Dict[str, int]:
    market_stats = get_market_price_stats(ip_type)
    base_price = max(1, round(estimate_ip_base_price(ip_type) * get_ip_state_value_multiplier(usable_state)))
    market_avg = market_stats["avg"] or 0
    if usable_state != "ok":
        market_avg = round(market_avg * 0.35) if market_avg else 0
    if market_avg:
        recommended = round(base_price * 0.4 + market_avg * 0.6)
    else:
        recommended = base_price
    minimum = max(1, round(recommended * 0.75))
    maximum = max(minimum + 1, round(recommended * 1.1))
    return {
        "base": base_price,
        "recommended": recommended,
        "minimum": minimum,
        "maximum": maximum,
        "market_count": market_stats["count"] or 0,
        "market_min": market_stats["min"] or 0,
        "market_max": market_stats["max"] or 0,
    }


def build_spin_result_text(result: Dict[str, object]) -> str:
    lines = [
        f"{result['emoji']} <b>Результат крутки</b>",
        "",
        f"Аккаунт хостера: <b>{escape(result['hoster_label'])}</b>",
        f"IP: <b>{escape(result['display'])}</b>",
    ]
    if result["stored"]:
        lines.append(f"ID в инвентаре: <b>{result['inventory_id']}</b>")
    else:
        lines.append("В инвентарь не сохранен, так как IP не белый.")
    if result["contract_reward"]:
        lines.append(f"Контракт хостера выполнен: <b>+{result['contract_reward']}</b> монет")
    if result["streak_bonus"]:
        lines.append(f"Бонус за серию: <b>+{result['streak_bonus']}</b> монет")
    lines.append(f"Серия ежедневных круток: <b>{result['streak']}</b>")
    for event in result["events"]:
        lines.append(event)
    lines.append(f"Баланс после крутки: <b>{result['balance']}</b>")
    return "\n".join(lines)


def build_spin_ten_result_text(result: Dict[str, object]) -> str:
    lines = [
        "🎛 <b>Пакетная крутка x10</b>",
        "",
        f"Аккаунт хостера: <b>{escape(result['hoster_label'])}</b>",
    ]
    for index, item in enumerate(result["results"], start=1):
        line = f"{index}. {item['emoji']} {escape(item['display'])}"
        if item["stored"]:
            line += f" <b>[ID {item['inventory_id']}]</b>"
        lines.append(line)
    if result["contract_reward"]:
        lines.append(f"Контракт хостера выполнен: <b>+{result['contract_reward']}</b> монет")
    if result["streak_bonus"]:
        lines.append(f"Бонус за серию: <b>+{result['streak_bonus']}</b> монет")
    if result["events"]:
        lines.append("")
        lines.append("<b>События</b>")
        lines.extend(result["events"][:12])
    lines.append("")
    lines.append(f"Серия ежедневных круток: <b>{result['streak']}</b>")
    lines.append(f"Баланс после крутки: <b>{result['balance']}</b>")
    return "\n".join(lines)


def build_sell_prompt_text(inventory_id: int, ip_type: str, suggestion: Dict[str, int]) -> str:
    market_line = (
        f"Сейчас на маркете {suggestion['market_count']} похожих лотов: "
        f"{suggestion['market_min']} - {suggestion['market_max']} монет."
        if suggestion["market_count"]
        else "Похожих лотов на маркете сейчас нет."
    )
    lines = [
        f"<b>Выставление IP ID {inventory_id} на маркет</b>",
        "",
        f"Тип: <b>{escape(ip_type)}</b>",
        f"База для такого IP: <b>{suggestion['base']}</b>",
        f"Рекомендованная цена: <b>{suggestion['recommended']}</b>",
        f"Комфортный диапазон: <b>{suggestion['minimum']} - {suggestion['maximum']}</b>",
        market_line,
        "",
        "Можно нажать готовую цену ниже или отправить свою одним числом.",
        "Для отмены используйте /cancel.",
    ]
    return "\n".join(lines)


def build_inventory_item_text(item_id: int, ip_type: str, acquired_at: str) -> str:
    item = get_inventory_item(item_id)
    usable_state = item[4] if item else "ok"
    protected = bool(item[5]) if item else False
    listed = has_active_listing(item_id)
    bound_server = get_server_bound_to_inventory(item_id)
    system_price = get_void_sale_price(ip_type, usable_state)
    if listed:
        status = "уже выставлен на маркет"
    elif bound_server:
        status = f"привязан к серверу ID {bound_server[0]} {bound_server[2]}"
    else:
        status = "свободен"
    if usable_state != "ok":
        status = f"{status}; {get_inventory_state_label(usable_state)}"

    lines = [
        f"<b>IP ID {item_id}</b>",
        "",
        f"Тип: <b>{escape(ip_type)}</b>",
        f"Получен: <b>{format_dt(acquired_at)}</b>",
        f"Статус: <b>{escape(status)}</b>",
        f"Защита РКН: <b>{'есть' if protected else 'нет'}</b>",
        f"Продажа системе: <b>{system_price}</b> монет",
    ]
    if not listed and not bound_server and is_special_ip_type(ip_type):
        suggestion = get_sell_price_suggestion(ip_type, usable_state)
        lines.append(f"Маркет-рекомендация: <b>{suggestion['recommended']}</b> монет")
    return "\n".join(lines)


def get_available_spin_pool():
    limits = get_ip_limits()
    available = []
    for ip_type, config in IP_DROP_CONFIG.items():
        remaining = limits.get(ip_type, 0)
        if remaining > 0:
            available.append((ip_type, remaining, config["weight"]))
    return available


def render_drop_display(drop_type: str) -> str:
    config = IP_DROP_CONFIG[drop_type]
    if "description" in config:
        return config["description"]
    operators = random.sample(list(OPERATOR_CHOICES.values()), config["operators_count"])
    return f"белый IP ({', '.join(operators)})"


def roll_government_ip(provider_key: str) -> bool:
    limits = get_ip_limits()
    if limits.get("гос_подсеть", 0) <= 0:
        return False
    provider_multiplier = {
        "vk_cloud": 0.75,
        "yandex_cloud": 0.9,
        "ruvds": 1.0,
        "selectel": 1.15,
        "majordomo": 1.2,
        "mws": 1.35,
        "timeweb": 1.5,
        "ihc": 1.7,
    }.get(provider_key, 1.0)
    return random.random() < GOVERNMENT_IP_BASE_CHANCE * provider_multiplier


def get_random_unprotected_inventory(user_id: int) -> Optional[tuple]:
    cursor.execute(
        """
        SELECT id, ip_type, acquired_at, is_sold, usable_state, confiscation_protected
        FROM inventory
        WHERE user_id=? AND is_sold=0 AND COALESCE(confiscation_protected, 0)=0
        ORDER BY RANDOM()
        LIMIT 1
    """,
        (user_id,),
    )
    return cursor.fetchone()


def get_random_unprotected_hoster_account(user_id: int) -> Optional[tuple]:
    cursor.execute(
        """
        SELECT id, user_id, provider_key, purchase_price, status, acquired_at, suspended_until
        FROM hoster_accounts
        WHERE user_id=? AND status='active' AND COALESCE(confiscation_protected, 0)=0
        ORDER BY RANDOM()
        LIMIT 1
    """,
        (user_id,),
    )
    return cursor.fetchone()


def get_random_active_proxy(user_id: int) -> Optional[tuple]:
    cursor.execute(
        """
        SELECT id, server_name, operators, active, created_at, purchase_cost, bound_inventory_id, confiscation_protected
        FROM proxies
        WHERE user_id=? AND active=1
        ORDER BY RANDOM()
        LIMIT 1
    """,
        (user_id,),
    )
    return cursor.fetchone()


def get_random_unprotected_proxy(user_id: int) -> Optional[tuple]:
    cursor.execute(
        """
        SELECT id, server_name, operators, active, created_at, purchase_cost, bound_inventory_id, confiscation_protected
        FROM proxies
        WHERE user_id=? AND active=1 AND COALESCE(confiscation_protected, 0)=0
        ORDER BY RANDOM()
        LIMIT 1
    """,
        (user_id,),
    )
    return cursor.fetchone()


def confiscate_inventory_item(inventory_id: int):
    if has_active_listing(inventory_id):
        cursor.execute("UPDATE market SET status='cancelled' WHERE inventory_id=? AND status='active'", (inventory_id,))
    cursor.execute("UPDATE proxies SET bound_inventory_id=NULL WHERE bound_inventory_id=?", (inventory_id,))
    cursor.execute(
        "UPDATE inventory SET usable_state='confiscated', is_sold=1 WHERE id=?",
        (inventory_id,),
    )
    conn.commit()


def confiscate_hoster_account(account_id: int):
    cursor.execute(
        "UPDATE hoster_accounts SET status='confiscated', suspended_until=NULL WHERE id=?",
        (account_id,),
    )
    conn.commit()


def confiscate_proxy(proxy_id: int):
    cursor.execute(
        "UPDATE proxies SET active=0, bound_inventory_id=NULL, confiscated_at=? WHERE id=?",
        (datetime.now().isoformat(), proxy_id),
    )
    conn.commit()


def get_server_confiscation_modifier(user_id: int) -> float:
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM hoster_accounts
        WHERE user_id=? AND status='active' AND COALESCE(confiscation_protected, 0)=1
    """,
        (user_id,),
    )
    protected_accounts = cursor.fetchone()[0] or 0
    return max(0.55, 1.0 - protected_accounts * 0.12)


def start_roulette_game(user_id: int) -> None:
    loaded = random.randint(1, 6)
    ROULETTE_GAMES[user_id] = {
        "loaded": loaded,
        "expires_at": datetime.now() + timedelta(minutes=5),
    }


def apply_random_event(user_id: int, provider_label: str, trigger_chance: float) -> List[str]:
    if random.random() >= trigger_chance:
        return []
    if random.random() < RUSSIAN_ROULETTE_CHANCE:
        start_roulette_game(user_id)
        return ["🎲 Полицейский притащил вас в русскую рулетку. Игра ждёт в панели: откройте раздел рулетки и выберите камеру."]

    roll = random.random()
    if roll < 0.24:
        item = get_random_unprotected_inventory(user_id)
        if item:
            confiscate_inventory_item(item[0])
            return [f"🚨 Конфискация IP. Потерян IP ID {item[0]}: {escape(item[1])}."]
        return ["🚨 РКН хотел конфисковать IP, но не нашел незащищенных."]
    server_threshold = 0.24 + (0.18 * get_server_confiscation_modifier(user_id))
    if roll < server_threshold:
        proxy = get_random_unprotected_proxy(user_id)
        if proxy:
            confiscate_proxy(proxy[0])
            return [f"🚨 Конфискация сервера. Сервер ID {proxy[0]} {escape(proxy[1])} изъят."]
        return ["🚨 Конфискация сервера сорвалась: защищённых или доступных серверов нет."]
    if roll < 0.68:
        item = get_random_unprotected_inventory(user_id)
        if item and item[4] == "ok":
            set_inventory_usable_state(item[0], "rkn_banned")
            return [f"📵 РКН забанил IP ID {item[0]}: {escape(item[1])}. Продавать можно, но на сервере он бесполезен."]
        return []
    if roll < 0.92:
        item = get_random_unprotected_inventory(user_id)
        if item and item[4] == "ok" and not is_government_ip_type(item[1]):
            set_inventory_usable_state(item[0], "whitelist_revoked")
            return [f"📉 IP ID {item[0]}: {escape(item[1])} вылетел из белых списков. Продавать можно, но на сервере он бесполезен."]
        return []

    seize = min(get_available_balance(user_id), random.randint(10, 35))
    if seize > 0:
        add_balance(user_id, -seize, f"Штраф от {provider_label}")
        return [f"💸 {provider_label} списал <b>{seize}</b> монет за подозрительную активность."]
    return []


def perform_spin_once(user_id: int, hoster_account_id: int, provider_key: str) -> Dict[str, object]:
    provider_label = get_hoster_label(provider_key)
    provider_config = HOSTER_CONFIGS[provider_key]

    if random.random() < BAN_CHANCE * provider_config["ban_modifier"]:
        suspend_hoster_account(hoster_account_id, BAN_DURATION_MINUTES)
        apply_hoster_hold(user_id, datetime.now() + timedelta(minutes=BAN_DURATION_MINUTES))
        return {
            "ok": False,
            "error": f"{provider_label} заблокировал только свой аккаунт на {BAN_DURATION_MINUTES} мин. Монеты не списаны, часть средств заморожена у хостера.",
        }

    pool = get_weighted_spin_pool_for_user(provider_key, user_id)
    if not pool:
        return {
            "ok": False,
            "error": "Лимиты IP исчерпаны. Дождитесь следующего сброса.",
        }

    if roll_government_ip(provider_key):
        chosen = "гос_подсеть"
    else:
        drop_types = [item[0] for item in pool]
        weights = [item[2] for item in pool]
        chosen = random.choices(drop_types, weights=weights, k=1)[0]
    display = render_drop_display(chosen)
    emoji = IP_DROP_CONFIG[chosen]["emoji"]
    should_store = bool(IP_DROP_CONFIG[chosen].get("marketable"))
    decrement_ip_limit(chosen)
    increment_total_spins(user_id, 1)
    inventory_id = add_inventory(user_id, display) if should_store else None

    contract_reward = 0
    contract = get_or_create_daily_contract(user_id)
    if contract.get("status") == "active" and chosen == contract["target_drop_type"]:
        contract_reward = complete_daily_contract(user_id) or 0
        if contract_reward:
            add_balance(user_id, contract_reward, "Выполнение ежедневного контракта хостера")

    return {
        "ok": True,
        "drop_type": chosen,
        "display": display,
        "emoji": emoji,
        "inventory_id": inventory_id,
        "stored": should_store,
        "hoster_label": provider_label,
        "contract_reward": contract_reward,
        "events": [],
    }


def spin_ip_for_user(user_id: int) -> Dict[str, object]:
    selected_hoster = get_selected_hoster_account(user_id)
    if not selected_hoster:
        return {"ok": False, "error": "Сначала выберите активный аккаунт хостера в меню хостеров."}

    ban_until = is_banned(user_id)
    if ban_until:
        return {"ok": False, "error": f"Хостинг-провайдер заблокировал крутки до {ban_until.strftime('%H:%M:%S')}."}

    balance = get_available_balance(user_id)
    if balance < SPIN_COST:
        return {"ok": False, "error": f"Недостаточно монет: нужно {SPIN_COST}, у вас {balance}."}

    new_balance = add_balance(user_id, -SPIN_COST, f"Крутка IP ({SPIN_COST} монет)")
    update_activity(user_id)
    spin_result = perform_spin_once(user_id, selected_hoster[0], selected_hoster[2])
    if not spin_result["ok"]:
        add_balance(user_id, SPIN_COST, "Возврат за неудавшуюся крутку")
        return spin_result
    spin_result["events"].extend(apply_random_event(user_id, spin_result["hoster_label"], SPIN_RANDOM_EVENT_CHANCE))

    streak_info = update_spin_streak(user_id)
    new_balance = get_balance(user_id)
    if random.random() < 0.04:
        bonus = random.randint(10, 24)
        new_balance = add_balance(user_id, bonus, f"Партнерский бонус от {spin_result['hoster_label']}")
        spin_result["events"].append(f"{spin_result['hoster_label']} выдал партнерский бонус: <b>+{bonus}</b> монет.")
    elif random.random() < 0.03:
        suspend_hoster_account(selected_hoster[0], 30)
        spin_result["events"].append(f"Аккаунт {spin_result['hoster_label']} ушел на проверку на 30 минут. Выберите другой аккаунт.")

    spin_result.update({
        "balance": new_balance,
        "streak": streak_info["streak"],
        "streak_bonus": streak_info["bonus"],
    })
    return spin_result


def spin_ten_for_user(user_id: int) -> Dict[str, object]:
    selected_hoster = get_selected_hoster_account(user_id)
    if not selected_hoster:
        return {"ok": False, "error": "Сначала выберите активный аккаунт хостера в меню хостеров."}
    ban_until = is_banned(user_id)
    if ban_until:
        return {"ok": False, "error": f"Хостинг-провайдер заблокировал крутки до {ban_until.strftime('%H:%M:%S')}."}
    if get_available_balance(user_id) < SPIN10_COST:
        return {"ok": False, "error": f"Недостаточно монет: нужно {SPIN10_COST}, у вас {get_available_balance(user_id)}."}

    add_balance(user_id, -SPIN10_COST, f"Пакетная крутка IP ({SPIN10_COST} монет)")
    update_activity(user_id)

    results = []
    total_contract_reward = 0
    for _ in range(10):
        result = perform_spin_once(user_id, selected_hoster[0], selected_hoster[2])
        if not result["ok"]:
            add_balance(user_id, SPIN10_COST, "Возврат за неудавшуюся крутку x10")
            return result
        results.append(result)
        total_contract_reward += int(result["contract_reward"])
    all_events = apply_random_event(user_id, get_hoster_label(selected_hoster[2]), SPIN_RANDOM_EVENT_CHANCE)

    streak_info = update_spin_streak(user_id)
    return {
        "ok": True,
        "hoster_label": get_hoster_label(selected_hoster[2]),
        "results": results,
        "contract_reward": total_contract_reward,
        "events": all_events,
        "streak": streak_info["streak"],
        "streak_bonus": streak_info["bonus"],
        "balance": get_balance(user_id),
    }


# ========== ГОЛОСОВАНИЯ ==========
def generate_token(vote_id: int) -> str:
    return str(vote_id)


def save_vote(
    vote_id: int,
    token: str,
    chat_id: int,
    thread_id: int,
    poll_message_id: int,
    title: str,
    candidates: List[str],
    end_time: datetime,
):
    cursor.execute(
        """
        INSERT INTO votes (
            vote_id, token, chat_id, thread_id, poll_message_id,
            title, candidates, end_time, is_active
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
    """,
        (vote_id, token, chat_id, thread_id, poll_message_id, title, ",".join(candidates), end_time.isoformat()),
    )
    for idx in range(len(candidates)):
        cursor.execute(
            "INSERT OR IGNORE INTO fake_votes (vote_id, candidate_index, fake_count) VALUES (?, ?, 0)",
            (vote_id, idx),
        )
    conn.commit()


def load_active_votes():
    cursor.execute(
        """
        SELECT vote_id, token, chat_id, thread_id, poll_message_id, title, candidates, end_time
        FROM votes
        WHERE is_active=1
    """
    )
    for row in cursor.fetchall():
        vote_id, token, chat_id, thread_id, poll_message_id, title, candidates, end_time_str = row
        end_time = datetime.fromisoformat(end_time_str)
        if end_time > datetime.now():
            active_votes[token] = {
                "vote_id": vote_id,
                "chat_id": chat_id,
                "thread_id": thread_id,
                "poll_message_id": poll_message_id,
                "title": title,
                "candidates": candidates.split(","),
                "end_time": end_time,
            }


def get_fake_votes(vote_id: int) -> Dict[int, int]:
    cursor.execute("SELECT candidate_index, fake_count FROM fake_votes WHERE vote_id=?", (vote_id,))
    return {row[0]: row[1] for row in cursor.fetchall()}


def set_fake_vote(vote_id: int, candidate_index: int, new_count: int):
    cursor.execute(
        """
        INSERT OR REPLACE INTO fake_votes (vote_id, candidate_index, fake_count)
        VALUES (?, ?, ?)
    """,
        (vote_id, candidate_index, max(0, new_count)),
    )
    conn.commit()


def get_user_vote(vote_id: int, user_id: int) -> Optional[int]:
    cursor.execute("SELECT candidate_index FROM user_votes WHERE vote_id=? AND user_id=?", (vote_id, user_id))
    row = cursor.fetchone()
    return row[0] if row else None


def set_user_vote(vote_id: int, user_id: int, candidate_index: int):
    cursor.execute(
        "INSERT OR REPLACE INTO user_votes (vote_id, user_id, candidate_index) VALUES (?, ?, ?)",
        (vote_id, user_id, candidate_index),
    )
    conn.commit()


def delete_user_vote(vote_id: int, user_id: int):
    cursor.execute("DELETE FROM user_votes WHERE vote_id=? AND user_id=?", (vote_id, user_id))
    conn.commit()


def get_total_votes(vote_id: int) -> List[dict]:
    cursor.execute(
        "SELECT candidate_index, COUNT(*) FROM user_votes WHERE vote_id=? GROUP BY candidate_index",
        (vote_id,),
    )
    real_counts = {row[0]: row[1] for row in cursor.fetchall()}
    fake_counts = get_fake_votes(vote_id)
    token = next((item for item, data in active_votes.items() if data["vote_id"] == vote_id), None)
    if not token:
        return []
    candidates = active_votes[token]["candidates"]
    results = []
    for idx, candidate in enumerate(candidates):
        results.append(
            {
                "candidate": candidate,
                "votes": real_counts.get(idx, 0) + fake_counts.get(idx, 0),
            }
        )
    return results


def get_vote_keyboard(vote_id: int, candidates: Sequence[str], user_id: int, token: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    current_vote = get_user_vote(vote_id, user_id)
    for idx, candidate in enumerate(candidates):
        prefix = "✅ " if current_vote == idx else ""
        builder.add(InlineKeyboardButton(text=f"{prefix}{candidate}", callback_data=f"vote_{token}_{idx}"))
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="📊 Результаты", callback_data=f"results_{token}"))
    return builder.as_markup()


def get_results_text(vote_id: int, title: str) -> str:
    results = get_total_votes(vote_id)
    if not results:
        return "Нет голосов."
    total = sum(item["votes"] for item in results)
    lines = [f"<b>{escape(title)}</b>", ""]
    for item in results:
        percent = (item["votes"] / total * 100) if total else 0
        lines.append(f"• {escape(item['candidate'])}: {item['votes']} гол. ({percent:.1f}%)")
    lines.append("")
    lines.append(f"Всего: {total}")
    return "\n".join(lines)


async def delete_message_after(chat_id: int, message_id: int, delay: int):
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        return


# ========== UI ==========
def build_back_button(target: str = "menu_main") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="◀️ Назад", callback_data=target))
    return builder.as_markup()


async def render_message(
    chat_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup,
    message_id: Optional[int] = None,
):
    if message_id:
        await bot.edit_message_text(
            text=text,
            chat_id=chat_id,
            message_id=message_id,
            parse_mode="HTML",
            reply_markup=reply_markup,
        )
    else:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
            reply_markup=reply_markup,
        )


def build_main_menu(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="💰 Баланс", callback_data="menu_balance"))
    builder.add(InlineKeyboardButton(text="📦 Мои IP", callback_data="menu_inventory"))
    builder.add(InlineKeyboardButton(text="☁️ Хостеры", callback_data="menu_hosters"))
    builder.add(InlineKeyboardButton(text="🖥 Серверы", callback_data="menu_proxies"))
    builder.add(InlineKeyboardButton(text="🏪 Маркет", callback_data="menu_market"))
    builder.add(InlineKeyboardButton(text="📡 VPN", callback_data="menu_vpn"))
    if user_id in ROULETTE_GAMES:
        builder.add(InlineKeyboardButton(text="🎲 Рулетка", callback_data="menu_roulette"))
    if is_admin(user_id):
        builder.add(InlineKeyboardButton(text="🛠 Админ", callback_data="menu_admin"))
    if is_moderator(user_id):
        builder.add(InlineKeyboardButton(text="🗳 Голосования", callback_data="menu_votes"))
    builder.adjust(2, 2, 2, 1)
    return builder.as_markup()


def build_inventory_menu(items) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for item_id, ip_type, _, _, _, _ in items:
        short_type = ip_type if len(ip_type) <= 28 else f"{ip_type[:25]}..."
        builder.add(
            InlineKeyboardButton(
                text=f"ID {item_id} • {short_type}",
                callback_data=f"inventory_view_{item_id}",
            )
        )
    builder.add(InlineKeyboardButton(text="🧹 Продать несколько", callback_data="inventory_bulk_sell"))
    builder.add(InlineKeyboardButton(text="🏪 Маркет", callback_data="menu_market"))
    builder.add(InlineKeyboardButton(text="🔄 Обновить", callback_data="menu_inventory"))
    builder.add(InlineKeyboardButton(text="◀️ Назад", callback_data="menu_main"))
    builder.adjust(*([1] * len(items)), 1, 2, 1)
    return builder.as_markup()


def build_inventory_item_menu(inventory_id: int, ip_type: str, is_listed: bool, is_bound: bool, is_protected: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    is_marketable = is_special_ip_type(ip_type)
    if is_marketable and not is_listed and not is_bound:
        builder.add(
            InlineKeyboardButton(
                text="🏪 Выставить на маркет",
                callback_data=f"inventory_sell_{inventory_id}",
            )
        )
    if not is_listed and not is_bound:
        builder.add(
            InlineKeyboardButton(
                text="💸 Продать системе",
                callback_data=f"inventory_delete_{inventory_id}",
            )
        )
    if not is_protected:
        builder.add(
            InlineKeyboardButton(
                text=f"🛡 Защита • {get_ip_protection_cost(ip_type)}",
                callback_data=f"inventory_protect_ask_{inventory_id}",
            )
        )
    builder.add(InlineKeyboardButton(text="📦 К списку IP", callback_data="menu_inventory"))
    builder.add(InlineKeyboardButton(text="◀️ Главное меню", callback_data="menu_main"))
    builder.adjust(1, 1, 1, 2)
    return builder.as_markup()


def build_sell_price_menu(inventory_id: int, suggestion: Dict[str, int]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(
            text=f"Быстро: {suggestion['minimum']}",
            callback_data=f"sellquick_{inventory_id}_{suggestion['minimum']}",
        )
    )
    builder.add(
        InlineKeyboardButton(
            text=f"Рекомендовано: {suggestion['recommended']}",
            callback_data=f"sellquick_{inventory_id}_{suggestion['recommended']}",
        )
    )
    builder.add(
        InlineKeyboardButton(
            text=f"Дороже: {suggestion['maximum']}",
            callback_data=f"sellquick_{inventory_id}_{suggestion['maximum']}",
        )
    )
    builder.add(InlineKeyboardButton(text="◀️ Назад к IP", callback_data="menu_inventory"))
    builder.adjust(1)
    return builder.as_markup()


def build_market_menu(listings, user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for lot_id, seller_id, _, price, ip_type in listings[:18]:
        short_type = ip_type if len(ip_type) <= 24 else f"{ip_type[:21]}..."
        prefix = "•" if seller_id == user_id else ""
        builder.add(InlineKeyboardButton(text=f"{prefix}{short_type} • {price}", callback_data=f"market_view_{lot_id}"))
    for lot_id, seller_id, _, price, provider_key in get_hoster_market_listings()[:12]:
        label = get_hoster_label(provider_key)
        prefix = "•" if seller_id == user_id else ""
        builder.add(InlineKeyboardButton(text=f"{prefix}{label} • {price}", callback_data=f"hoster_market_view_{lot_id}"))
    builder.add(InlineKeyboardButton(text="📌 Мои лоты", callback_data="menu_my_lots"))
    builder.add(InlineKeyboardButton(text="📦 Мои IP", callback_data="menu_inventory"))
    builder.add(InlineKeyboardButton(text="☁️ Хостеры", callback_data="menu_hosters"))
    builder.add(InlineKeyboardButton(text="🔄 Обновить", callback_data="menu_market"))
    builder.add(InlineKeyboardButton(text="◀️ Назад", callback_data="menu_main"))
    builder.adjust(*([1] * (min(len(listings), 18) + min(len(get_hoster_market_listings()), 12))), 1, 2, 1, 1)
    return builder.as_markup()


def build_proxies_menu(proxies) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for proxy_id, server_name, _, _, _, _, bound_inventory_id in proxies[:12]:
        lock = "🔒 " if is_proxy_protected(proxy_id) else ""
        state = " • без IP" if not bound_inventory_id else ""
        builder.add(InlineKeyboardButton(text=f"{lock}ID {proxy_id} • {server_name}{state}", callback_data=f"proxy_view_{proxy_id}"))
    builder.add(InlineKeyboardButton(text="🖥 Купить сервер", callback_data="proxy_add_start"))
    builder.add(InlineKeyboardButton(text="⬆️ Квота", callback_data="proxy_upgrade_ask"))
    builder.add(InlineKeyboardButton(text="🔄 Обновить", callback_data="menu_proxies"))
    builder.add(InlineKeyboardButton(text="◀️ Назад", callback_data="menu_main"))
    builder.adjust(1, 2, 1, 1)
    return builder.as_markup()


def build_server_bind_menu(proxy_id: int, items) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for item_id, ip_type, _, _, _ in items:
        builder.add(
            InlineKeyboardButton(
                text=f"IP ID {item_id}: {ip_type}",
                callback_data=f"proxybind_{proxy_id}_{item_id}",
            )
        )
    builder.add(InlineKeyboardButton(text="◀️ Назад", callback_data="menu_proxies"))
    builder.adjust(1)
    return builder.as_markup()


def build_hoster_menu(accounts, user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    selected = get_selected_hoster_account(user_id)
    selected_id = selected[0] if selected else None
    for account_id, _, provider_key, _, status, _, _ in accounts[:12]:
        label = get_hoster_label(provider_key)
        prefix = "✅ " if account_id == selected_id else ""
        suffix = " ⏳" if status != "active" else ""
        builder.add(InlineKeyboardButton(text=f"{prefix}{label} ID {account_id}{suffix}", callback_data=f"hoster_view_{account_id}"))
    for provider_key in HOSTER_CONFIGS:
        if HOSTER_CONFIGS[provider_key]["base_cost"] > 0:
            builder.add(
                InlineKeyboardButton(
                    text=f"{get_hoster_label(provider_key)} • {HOSTER_CONFIGS[provider_key]['base_cost']}",
                    callback_data=f"hoster_shop_view_{provider_key}",
                )
            )
    builder.add(InlineKeyboardButton(text="🏪 Маркет", callback_data="menu_market"))
    builder.add(InlineKeyboardButton(text="🔄 Обновить", callback_data="menu_hosters"))
    builder.add(InlineKeyboardButton(text="◀️ Назад", callback_data="menu_main"))
    builder.adjust(1, 1, 1, 2, 1)
    return builder.as_markup()


def build_admin_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"))
    builder.add(InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users"))
    builder.add(InlineKeyboardButton(text="🔎 Найти пользователя", callback_data="admin_find_user"))
    builder.add(InlineKeyboardButton(text="♻️ Сбросить лимиты IP", callback_data="admin_reset_limits"))
    builder.add(InlineKeyboardButton(text="🗳 Голосования", callback_data="menu_votes"))
    builder.add(InlineKeyboardButton(text="◀️ Назад", callback_data="menu_main"))
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()


def build_admin_users_menu(users) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for user_id, username, first_name, last_name, _, _ in users:
        label = f"@{username}" if username else (first_name or str(user_id))
        if last_name and not username and first_name:
            label = f"{first_name} {last_name}"
        short_label = label if len(label) <= 24 else f"{label[:21]}..."
        builder.add(
            InlineKeyboardButton(
                text=f"{short_label} [{user_id}]",
                callback_data=f"admin_user_{user_id}",
            )
        )
    builder.add(InlineKeyboardButton(text="🔎 Найти по ID/@username", callback_data="admin_find_user"))
    builder.add(InlineKeyboardButton(text="◀️ Назад", callback_data="menu_admin"))
    builder.adjust(1)
    return builder.as_markup()


def build_admin_user_menu(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="➕ Выдать 100", callback_data=f"admin_grant_{user_id}_100"))
    builder.add(InlineKeyboardButton(text="➕ Выдать сумму", callback_data=f"admin_prompt_balance_add_{user_id}"))
    builder.add(InlineKeyboardButton(text="💳 Установить баланс", callback_data=f"admin_prompt_balance_set_{user_id}"))
    builder.add(InlineKeyboardButton(text="⛔ Забанить", callback_data=f"admin_prompt_ban_{user_id}"))
    builder.add(InlineKeyboardButton(text="✅ Разбанить", callback_data=f"admin_unban_{user_id}"))
    builder.add(InlineKeyboardButton(text="🧹 Снять холд", callback_data=f"admin_clear_hold_{user_id}"))
    builder.add(InlineKeyboardButton(text="🖥 Квота серверов", callback_data=f"admin_prompt_quota_{user_id}"))
    builder.add(InlineKeyboardButton(text="🏷 Сменить ник", callback_data=f"admin_prompt_nick_{user_id}"))
    builder.add(InlineKeyboardButton(text="🚨 Конфисковать всё", callback_data=f"admin_confiscate_{user_id}"))
    builder.add(InlineKeyboardButton(text="🔄 Обновить", callback_data=f"admin_user_{user_id}"))
    builder.add(InlineKeyboardButton(text="◀️ К списку", callback_data="admin_users"))
    builder.adjust(2)
    return builder.as_markup()


def build_admin_confiscation_menu(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🚨 Да, конфисковать всё", callback_data=f"admin_confiscate_confirm_{user_id}"))
    builder.add(InlineKeyboardButton(text="◀️ Назад", callback_data=f"admin_user_{user_id}"))
    builder.adjust(1)
    return builder.as_markup()


def build_market_item_menu(listing_id: int, seller_id: int, user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if seller_id == user_id:
        builder.add(InlineKeyboardButton(text="🧹 Снять с маркета", callback_data=f"market_cancel_{listing_id}"))
    else:
        builder.add(InlineKeyboardButton(text="💰 Купить лот", callback_data=f"market_buy_{listing_id}"))
    builder.add(InlineKeyboardButton(text="◀️ К маркету", callback_data="menu_market"))
    builder.adjust(1)
    return builder.as_markup()


def build_hoster_market_item_menu(listing_id: int, seller_id: int, user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if seller_id == user_id:
        builder.add(InlineKeyboardButton(text="🧹 Снять с маркета", callback_data=f"hoster_cancel_{listing_id}"))
    else:
        builder.add(InlineKeyboardButton(text="💰 Купить аккаунт", callback_data=f"hoster_buy_{listing_id}"))
    builder.add(InlineKeyboardButton(text="◀️ К маркету", callback_data="menu_market"))
    builder.adjust(1)
    return builder.as_markup()


def build_hoster_item_menu(account_id: int, is_active: bool, is_selected: bool, is_protected: bool, is_listed: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if is_active and not is_selected:
        builder.add(InlineKeyboardButton(text="✅ Сделать активным", callback_data=f"hoster_select_{account_id}"))
    if is_active and not is_listed:
        builder.add(InlineKeyboardButton(text="🏪 Продать на маркете", callback_data=f"hoster_sell_{account_id}"))
    if is_active and not is_protected:
        builder.add(InlineKeyboardButton(text=f"🛡 Купить защиту", callback_data=f"hoster_protect_ask_{account_id}"))
    builder.add(InlineKeyboardButton(text="◀️ К хостерам", callback_data="menu_hosters"))
    builder.adjust(1)
    return builder.as_markup()


def build_hoster_shop_view_menu(provider_key: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="💰 Купить", callback_data=f"hoster_shop_{provider_key}"))
    builder.add(InlineKeyboardButton(text="🤝 Торговаться", callback_data=f"hoster_haggle_{provider_key}"))
    builder.add(InlineKeyboardButton(text="◀️ К хостерам", callback_data="menu_hosters"))
    builder.adjust(1)
    return builder.as_markup()


def build_proxy_item_menu(user_id: int, proxy_id: int, has_binding: bool, is_protected: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    link = get_vpn_server_link(proxy_id)
    service = get_vpn_service(user_id)
    listing = get_active_vpn_server_listing(proxy_id)
    if has_binding:
        builder.add(InlineKeyboardButton(text="🔌 Отвязать IP", callback_data=f"proxy_unbind_{proxy_id}"))
    else:
        builder.add(InlineKeyboardButton(text="🔗 Привязать IP", callback_data=f"proxy_bind_{proxy_id}"))
    if listing:
        builder.add(InlineKeyboardButton(text="🧹 Снять с VPN-рынка", callback_data=f"vpnproxy_unlist_{proxy_id}"))
    elif has_binding:
        if link and link[1] == user_id and link[2] == user_id:
            if service:
                builder.add(InlineKeyboardButton(text="📡 Убрать из VPN", callback_data=f"vpnproxy_remove_{proxy_id}"))
        elif link and link[1] != link[2] and link[1] == user_id:
            builder.add(InlineKeyboardButton(text="💼 Сдан в аренду VPN", callback_data="vpn_noop"))
        elif link and link[2] == user_id and link[1] != user_id:
            if service:
                builder.add(InlineKeyboardButton(text="↩️ Вернуть арендованный сервер", callback_data=f"vpnlease_release_{proxy_id}"))
        elif not link:
            if service:
                builder.add(InlineKeyboardButton(text="📡 Подключить к VPN", callback_data=f"vpnproxy_service_{proxy_id}"))
            builder.add(InlineKeyboardButton(text=f"🏷 Сдать в VPN • {get_vpn_server_suggested_rent(proxy_id)}/ч", callback_data=f"vpnproxy_list_{proxy_id}"))
    if not is_protected:
        builder.add(InlineKeyboardButton(text="🛡 Купить защиту", callback_data=f"proxy_protect_ask_{proxy_id}"))
    builder.add(InlineKeyboardButton(text="💸 Продать серверу системе", callback_data=f"proxy_remove_{proxy_id}"))
    builder.add(InlineKeyboardButton(text="◀️ К серверам", callback_data="menu_proxies"))
    builder.adjust(1)
    return builder.as_markup()


def build_roulette_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for chamber in range(1, 7):
        builder.add(InlineKeyboardButton(text=f"Камера {chamber}", callback_data=f"roulette_pick_{chamber}"))
    builder.add(InlineKeyboardButton(text="◀️ Назад", callback_data="menu_main"))
    builder.adjust(2, 2, 2, 1)
    return builder.as_markup()


def build_vpn_menu(user_id: int, service) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if not service:
        builder.add(InlineKeyboardButton(text=f"📡 Запустить сервис • {VPN_SERVICE_CREATE_COST}", callback_data="vpn_create_start"))
    else:
        price = int(service[2])
        marketing = int(service[3])
        is_active = bool(service[5])
        level = get_vpn_level(service)
        builder.add(InlineKeyboardButton(text="➖ Цена", callback_data="vpn_price_down"))
        builder.add(InlineKeyboardButton(text=f"Цена {price}", callback_data="vpn_noop"))
        builder.add(InlineKeyboardButton(text="➕ Цена", callback_data="vpn_price_up"))
        builder.add(InlineKeyboardButton(text="➖ Реклама", callback_data="vpn_marketing_down"))
        builder.add(InlineKeyboardButton(text=f"Реклама {marketing}", callback_data="vpn_noop"))
        builder.add(InlineKeyboardButton(text="➕ Реклама", callback_data="vpn_marketing_up"))
        builder.add(InlineKeyboardButton(text=f"⬆️ Уровень {level}", callback_data="vpn_level_up"))
        builder.add(InlineKeyboardButton(text="🛒 Арендовать сервер", callback_data="vpn_market_open"))
        builder.add(InlineKeyboardButton(text="🖥 Открыть свои серверы", callback_data="menu_proxies"))
        builder.add(InlineKeyboardButton(text="⏸ Пауза" if is_active else "▶️ Запустить", callback_data="vpn_toggle"))
        builder.add(InlineKeyboardButton(text="🔄 Обновить", callback_data="menu_vpn"))
        builder.add(InlineKeyboardButton(text="🗑 Удалить VPN", callback_data="vpn_delete_ask"))
        for proxy_id, owner_id, _, _, rent_price, _ in get_vpn_service_server_links(user_id)[:4]:
            if owner_id != user_id:
                builder.add(InlineKeyboardButton(text=f"↩️ Аренда ID {proxy_id} • {rent_price}/ч", callback_data=f"vpnlease_release_{proxy_id}"))
    builder.add(InlineKeyboardButton(text="◀️ Назад", callback_data="menu_main"))
    builder.adjust(3, 3, 3, 2, *([1] * min(4, len(get_vpn_service_server_links(user_id)) if service else 0)), 1)
    return builder.as_markup()


def build_vpn_market_menu(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for listing_id, seller_id, proxy_id, price, server_name in get_vpn_server_market_listings()[:16]:
        prefix = "•" if seller_id == user_id else ""
        builder.add(InlineKeyboardButton(text=f"{prefix}ID {proxy_id} • {server_name} • {price}/ч", callback_data=f"vpnmarket_view_{listing_id}"))
    builder.add(InlineKeyboardButton(text="◀️ К VPN", callback_data="menu_vpn"))
    builder.adjust(*([1] * min(16, len(get_vpn_server_market_listings()))), 1)
    return builder.as_markup()


def build_vpn_market_item_menu(user_id: int, listing_id: int, seller_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if seller_id == user_id:
        builder.add(InlineKeyboardButton(text="🧹 Снять лот", callback_data=f"vpnmarket_cancel_{listing_id}"))
    else:
        builder.add(InlineKeyboardButton(text="💰 Арендовать", callback_data=f"vpnmarket_buy_{listing_id}"))
    builder.add(InlineKeyboardButton(text="◀️ К рынку", callback_data="vpn_market_open"))
    builder.adjust(1)
    return builder.as_markup()


def build_bulk_sell_menu(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    items = [
        item for item in get_inventory_for_display(user_id)
        if not get_server_bound_to_inventory(item[0]) and item[4] != "confiscated"
    ]
    selected = set(BULK_SELL_SELECTIONS.get(user_id, []))
    for item_id, ip_type, _, _, usable_state, _ in items[:20]:
        mark = "✅ " if item_id in selected else ""
        price = get_void_sale_price(ip_type, usable_state)
        short_type = ip_type if len(ip_type) <= 18 else f"{ip_type[:15]}..."
        builder.add(
            InlineKeyboardButton(
                text=f"{mark}ID {item_id} • {short_type} • {price}",
                callback_data=f"bulk_toggle_{item_id}",
            )
        )
    builder.add(InlineKeyboardButton(text="💸 Продать отмеченные", callback_data="bulk_sell_confirm"))
    builder.add(InlineKeyboardButton(text="🧹 Очистить выбор", callback_data="bulk_sell_clear"))
    builder.add(InlineKeyboardButton(text="◀️ К IP", callback_data="menu_inventory"))
    builder.adjust(*([1] * min(len(items), 20)), 1, 2)
    return builder.as_markup()


def build_my_lots_menu(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for lot_id, _, _, price, ip_type in get_user_market_listings(user_id)[:20]:
        short_type = ip_type if len(ip_type) <= 20 else f"{ip_type[:17]}..."
        builder.add(InlineKeyboardButton(text=f"{short_type} • {price}", callback_data=f"market_view_{lot_id}"))
    for lot_id, _, _, price, provider_key in get_hoster_market_listings()[:20]:
        # filter user-owned hoster listings inline
        item = get_hoster_market_item(lot_id)
        if not item or item[0] != user_id:
            continue
        builder.add(InlineKeyboardButton(text=f"{get_hoster_label(provider_key)} • {price}", callback_data=f"hoster_market_view_{lot_id}"))
    builder.add(InlineKeyboardButton(text="◀️ К маркету", callback_data="menu_market"))
    builder.adjust(1)
    return builder.as_markup()


def get_inventory_for_display(user_id: int):
    items = []
    for item in get_user_inventory(user_id, only_unsold=True):
        if has_active_listing(item[0]):
            continue
        if get_server_bound_to_inventory(item[0]):
            continue
        items.append(item)
    return items


async def show_main_panel(user_id: int, message_id: Optional[int] = None):
    snapshot = get_user_admin_snapshot(user_id)
    vpn_service = get_vpn_service(user_id)
    text = (
        "<b>Панель</b>\n\n"
        f"Монеты: <b>{snapshot['balance']}</b> | Доступно: <b>{snapshot['available_balance']}</b>\n"
        f"IP: <b>{snapshot['inventory_count']}</b> | Лоты: <b>{snapshot['market_count']}</b> | Серверы: <b>{snapshot['proxies_count']}</b>\n"
        f"Доход: <b>{get_total_income_per_hour(user_id)}/ч</b>\n"
        f"VPN: <b>{escape(vpn_service[1]) if vpn_service else 'не запущен'}</b>\n"
        "Крутки: <code>/крутить</code> и <code>/крутить10</code>"
    )
    await render_message(user_id, text, build_main_menu(user_id), message_id=message_id)


async def show_balance_menu(user_id: int, message_id: Optional[int] = None):
    balance = get_balance(user_id)
    available_balance = get_available_balance(user_id)
    quota = get_proxy_quota(user_id)
    income = get_total_income_per_hour(user_id)
    vpn_income = get_vpn_hourly_profit(user_id) if get_vpn_service(user_id) else get_vpn_server_rental_income_per_hour(user_id)
    ban_until = is_banned(user_id)
    hold = get_hoster_hold(user_id)
    loan = get_active_microloan(user_id)
    bonus_text = "доступен" if can_receive_daily_bonus(user_id) else "пока недоступен"
    ban_text = ban_until.strftime("%H:%M:%S") if ban_until else "нет"
    hold_text = (
        f"{hold['amount']} до {hold['until'].strftime('%H:%M:%S')}"
        if hold["until"]
        else "нет"
    )
    loan_text = "нет"
    if loan:
        due_at = datetime.fromisoformat(loan[4]).strftime("%H:%M")
        warning = " | предупреждение уже было" if loan[6] else ""
        loan_text = f"{loan[2]} до {due_at}{warning}"
    text = (
        "<b>Баланс</b>\n\n"
        f"Всего: <b>{balance}</b>\n"
        f"Доступно: <b>{available_balance}</b>\n"
        f"Доход: <b>{income}/ч</b>\n"
        f"Из них VPN: <b>{vpn_income}/ч</b>\n"
        f"Квота серверов: <b>{quota}</b>\n"
        f"Следующий слот: <b>{get_proxy_quota_upgrade_cost(user_id)}</b>\n"
        f"Ежедневный бонус: <b>{bonus_text}</b>\n"
        f"Бан крутки: <b>{ban_text}</b>\n"
        f"Холд хостера: <b>{hold_text}</b>\n"
        f"Микрозайм: <b>{loan_text}</b>\n"
        f"Бафф шансов: <b>{'активен' if get_luck_buff_until(user_id) else 'нет'}</b>"
    )
    await render_message(user_id, text, build_balance_actions_menu(user_id), message_id=message_id)


async def show_inventory_menu(user_id: int, message_id: Optional[int] = None):
    items = get_inventory_for_display(user_id)
    stats = {"total": len(items), "white": 0, "ordinary": 0, "broken": 0}
    for _, ip_type, _, _, usable_state, _ in items:
        if is_special_ip_type(ip_type):
            stats["white"] += 1
        else:
            stats["ordinary"] += 1
        if usable_state != "ok":
            stats["broken"] += 1
    lines = [
        "<b>Мои IP</b>",
        "",
        f"Всего: <b>{stats['total']}</b> | Белых: <b>{stats['white']}</b> | Нерабочих: <b>{stats['broken']}</b>",
    ]
    if not items:
        lines.append("Свободных IP сейчас нет.")
    else:
        lines.append("Нажмите на нужный IP в кнопках ниже.")

    await render_message(user_id, "\n".join(lines), build_inventory_menu(items), message_id=message_id)


async def show_inventory_item_menu(user_id: int, inventory_id: int, message_id: Optional[int] = None):
    item = get_inventory_item(inventory_id)
    if not item:
        await render_message(
            user_id,
            "<b>IP не найден</b>\n\nВозможно, он уже продан или удален.",
            build_back_button("menu_inventory"),
            message_id=message_id,
        )
        return

    owner_id, ip_type, is_sold, acquired_at, _, is_protected = item
    if owner_id != user_id or is_sold:
        await render_message(
            user_id,
            "<b>IP недоступен</b>\n\nОн больше не находится в вашем инвентаре.",
            build_back_button("menu_inventory"),
            message_id=message_id,
        )
        return

    listed = has_active_listing(inventory_id)
    is_bound = get_server_bound_to_inventory(inventory_id) is not None
    await render_message(
        user_id,
        build_inventory_item_text(inventory_id, ip_type, acquired_at),
        build_inventory_item_menu(inventory_id, ip_type, listed, is_bound, bool(is_protected)),
        message_id=message_id,
    )


async def show_market_menu(user_id: int, message_id: Optional[int] = None):
    listings = get_active_market_listings()
    hoster_listings = get_hoster_market_listings()
    own_lots = sum(1 for _, seller_id, _, _, _ in listings if seller_id == user_id)
    lines = [
        "<b>Маркет</b>",
        "",
        f"IP-лоты: <b>{len(listings)}</b> | Ваших: <b>{own_lots}</b>",
        f"Аккаунты хостеров: <b>{len(hoster_listings)}</b>",
        "Откройте карточку лота кнопкой ниже."
    ]
    await render_message(user_id, "\n".join(lines), build_market_menu(listings, user_id), message_id=message_id)


async def show_hosters_menu(user_id: int, message_id: Optional[int] = None):
    accounts = get_user_hoster_accounts(user_id)
    selected = get_selected_hoster_account(user_id)
    contract = get_or_create_daily_contract(user_id)
    lines = [
        "<b>Хостеры</b>",
        "",
        f"Активный: <b>{escape(get_hoster_label(selected[2])) if selected else 'не выбран'}</b>",
        f"Контракт дня: <b>{get_drop_type_title(contract['target_drop_type'])}</b> за <b>{contract['reward']}</b> ({'активен' if contract.get('status') == 'active' else 'закрыт до обновления'})",
    ]
    if accounts:
        lines.append(f"Ваших аккаунтов: <b>{len(accounts)}</b>")
    else:
        lines.append("У вас пока нет платных аккаунтов.")
    lines.append("Снизу: сначала ваши аккаунты, потом магазин с баффами.")
    await render_message(user_id, "\n".join(lines), build_hoster_menu(accounts, user_id), message_id=message_id)


async def show_proxies_menu(user_id: int, message_id: Optional[int] = None):
    quota = get_proxy_quota(user_id)
    proxies = get_user_proxies(user_id, active_only=True)
    income = get_total_income_per_hour(user_id)
    purchase_cost = get_server_purchase_cost(user_id)
    lines = [
        "<b>Серверы</b>",
        "",
        f"Активно: <b>{len(proxies)}</b> / {quota}",
        f"Доход: <b>{income}/ч</b>",
        f"Следующий сервер: <b>{purchase_cost}</b>",
    ]
    if not proxies:
        lines.append("У вас нет активных серверов.")
    else:
        lines.append("🔒 = защита, без IP = сервер пока пустой.")
    await render_message(user_id, "\n".join(lines), build_proxies_menu(proxies), message_id=message_id)


async def show_bulk_sell_menu(user_id: int, message_id: Optional[int] = None):
    items = [
        item for item in get_inventory_for_display(user_id)
        if not get_server_bound_to_inventory(item[0]) and item[4] != "confiscated"
    ]
    selected_ids = BULK_SELL_SELECTIONS.get(user_id, [])
    selected_total = 0
    for item_id in selected_ids:
        item = get_inventory_item(item_id)
        if item and item[0] == user_id and not item[2]:
            selected_total += get_void_sale_price(item[1], item[4])
    lines = [
        "<b>Массовая продажа</b>",
        "",
        f"Доступно IP: <b>{len(items)}</b>",
        f"Отмечено: <b>{len(selected_ids)}</b>",
        f"Сумма продажи: <b>{selected_total}</b>",
        "Нажимайте по IP внизу, потом подтвердите продажу."
    ]
    await render_message(user_id, "\n".join(lines), build_bulk_sell_menu(user_id), message_id=message_id)


async def show_my_lots_menu(user_id: int, message_id: Optional[int] = None):
    ip_lots = get_user_market_listings(user_id)
    hoster_lots = [row for row in get_hoster_market_listings() if row[1] == user_id]
    lines = [
        "<b>Мои лоты</b>",
        "",
        f"IP-лоты: <b>{len(ip_lots)}</b>",
        f"Лоты аккаунтов: <b>{len(hoster_lots)}</b>",
    ]
    if not ip_lots and not hoster_lots:
        lines.append("У вас нет активных лотов.")
    else:
        lines.append("Откройте нужный лот кнопкой ниже.")
    await render_message(user_id, "\n".join(lines), build_my_lots_menu(user_id), message_id=message_id)


async def show_roulette_menu(user_id: int, message_id: Optional[int] = None):
    game = ROULETTE_GAMES.get(user_id)
    if not game or game["expires_at"] <= datetime.now():
        ROULETTE_GAMES.pop(user_id, None)
        await render_message(user_id, "<b>Рулетка не активна</b>", build_back_button("menu_main"), message_id=message_id)
        return
    text = (
        "<b>Русская рулетка</b>\n\n"
        "Выберите одну из 6 камер.\n"
        "Если угадаете пустую безопасную камеру, получите бафф шансов на 5 минут.\n"
        "Если попадёте в заряженную камеру, у вас конфискуют случайный незащищённый аккаунт хостера."
    )
    await render_message(user_id, text, build_roulette_menu(), message_id=message_id)


async def show_market_item_menu(user_id: int, listing_id: int, message_id: Optional[int] = None):
    lot = get_market_item_details(listing_id)
    if not lot:
        await render_message(user_id, "<b>Лот не найден</b>", build_back_button("menu_market"), message_id=message_id)
        return
    _, seller_id, inventory_id, price, status, ip_type, acquired_at, usable_state = lot
    item = get_inventory_item(inventory_id)
    if status != "active" or not item or item[2]:
        await render_message(user_id, "<b>Лот уже недоступен</b>", build_back_button("menu_market"), message_id=message_id)
        return
    state_text = "рабочий" if usable_state == "ok" else get_inventory_state_label(usable_state)
    text = (
        f"<b>{escape(ip_type)}</b>\n\n"
        f"IP: <b>{escape(ip_type)}</b>\n"
        f"Цена: <b>{price}</b>\n"
        f"Состояние: <b>{escape(state_text)}</b>\n"
        f"Продавец: <b>{escape(get_user_display(seller_id))}</b>\n"
        f"Получен продавцом: <b>{format_dt(acquired_at)}</b>"
    )
    await render_message(user_id, text, build_market_item_menu(listing_id, seller_id, user_id), message_id=message_id)


async def show_hoster_market_item_menu(user_id: int, listing_id: int, message_id: Optional[int] = None):
    item = get_hoster_market_item(listing_id)
    if not item:
        await render_message(user_id, "<b>Лот не найден</b>", build_back_button("menu_market"), message_id=message_id)
        return
    seller_id, account_id, price, status = item
    account = get_hoster_account(account_id)
    if status != "active" or not account or account[1] != seller_id:
        await render_message(user_id, "<b>Лот уже недоступен</b>", build_back_button("menu_market"), message_id=message_id)
        return
    text = (
        f"<b>{escape(get_hoster_label(account[2]))}</b>\n\n"
        f"Хостер: <b>{escape(get_hoster_label(account[2]))}</b>\n"
        f"Цена: <b>{price}</b>\n"
        f"Статус: <b>{'активен' if account[4] == 'active' else escape(account[4])}</b>\n"
        f"Куплен за: <b>{account[3]}</b>\n"
        f"Продавец: <b>{escape(get_user_display(seller_id))}</b>"
    )
    await render_message(user_id, text, build_hoster_market_item_menu(listing_id, seller_id, user_id), message_id=message_id)


async def show_hoster_item_menu(user_id: int, account_id: int, message_id: Optional[int] = None):
    account = get_hoster_account(account_id)
    if not account or account[1] != user_id:
        await render_message(user_id, "<b>Аккаунт не найден</b>", build_back_button("menu_hosters"), message_id=message_id)
        return
    status_text = "активен"
    if account[4] == "confiscated":
        status_text = "конфискован"
    elif account[4] != "active":
        status_text = f"на проверке до {format_dt(account[6]) if account[6] else 'неизвестно'}"
    selected = get_selected_hoster_account(user_id)
    is_selected = bool(selected and selected[0] == account_id)
    is_listed = has_active_hoster_listing(account_id)
    is_protected = is_hoster_account_protected(account_id)
    buffs = ", ".join(get_hoster_buff_summary(account[2]))
    text = (
        f"<b>{escape(get_hoster_label(account[2]))}</b>\n\n"
        f"ID: <b>{account_id}</b>\n"
        f"Статус: <b>{status_text}</b>\n"
        f"Куплен за: <b>{account[3]}</b>\n"
        f"Баффы: <b>{escape(buffs)}</b>\n"
        f"Защита: <b>{'есть' if is_protected else 'нет'}</b>\n"
        f"На маркете: <b>{'да' if is_listed else 'нет'}</b>\n"
        f"Активный: <b>{'да' if is_selected else 'нет'}</b>\n"
        f"Защита стоит: <b>{get_hoster_protection_cost(account_id)}</b>"
    )
    await render_message(
        user_id,
        text,
        build_hoster_item_menu(account_id, account[4] == "active", is_selected, is_protected, is_listed),
        message_id=message_id,
    )


async def show_hoster_shop_view(user_id: int, provider_key: str, message_id: Optional[int] = None):
    config = HOSTER_CONFIGS[provider_key]
    buffs = get_hoster_buff_summary(provider_key)
    text = (
        f"<b>{escape(get_hoster_label(provider_key))}</b>\n\n"
        f"Цена покупки: <b>{config['base_cost']}</b>\n"
        f"Режим торга: цена может стать немного ниже или немного выше.\n"
        f"Баффы: <b>{escape(', '.join(buffs))}</b>\n"
        f"Шанс на белые IP: <b>{'повышенный' if config['white_bonus'] > 0 or config['jackpot_bonus'] > 0 else 'базовый'}</b>.\n"
        f"Сейчас доступно монет: <b>{get_available_balance(user_id)}</b>"
    )
    await render_message(user_id, text, build_hoster_shop_view_menu(provider_key), message_id=message_id)


async def show_proxy_item_menu(user_id: int, proxy_id: int, message_id: Optional[int] = None):
    proxy = next((item for item in get_user_proxies(user_id, active_only=True) if item[0] == proxy_id), None)
    if not proxy:
        await render_message(user_id, "<b>Сервер не найден</b>", build_back_button("menu_proxies"), message_id=message_id)
        return
    _, server_name, _, _, created_at, paid_cost, bound_inventory_id = proxy
    if bound_inventory_id:
        item = get_inventory_item(bound_inventory_id)
        bound_text = item[1] if item else "IP не найден"
        operators = ", ".join(get_inventory_operators(item[1])) if item else "неизвестно"
    else:
        bound_text = "не привязан"
        operators = "появятся после привязки"
    link = get_vpn_server_link(proxy_id)
    listing = get_active_vpn_server_listing(proxy_id)
    vpn_text = "не участвует"
    if link and link[1] == user_id and link[2] == user_id:
        vpn_text = "подключен к вашему VPN"
    elif link and link[1] == user_id and link[2] != user_id:
        vpn_text = f"сдан в аренду другому VPN за {link[4]}/ч"
    elif link and link[2] == user_id and link[1] != user_id:
        vpn_text = f"арендован для VPN за {link[4]}/ч"
    elif listing:
        vpn_text = f"выставлен на VPN-рынок за {listing[3]}/ч"
    text = (
        f"<b>{escape(server_name)}</b>\n\n"
        f"ID: <b>{proxy_id}</b>\n"
        f"Взнос: <b>{paid_cost}</b>\n"
        f"Доход: <b>{calculate_income_for_proxy(bound_inventory_id)}/ч</b>\n"
        f"IP: <b>{escape(bound_text)}</b>\n"
        f"Операторы: <b>{escape(operators)}</b>\n"
        f"VPN-режим: <b>{escape(vpn_text)}</b>\n"
        f"Защита: <b>{'есть' if is_proxy_protected(proxy_id) else 'нет'}</b>\n"
        f"Защита стоит: <b>{get_proxy_protection_cost(proxy_id)}</b>\n"
        f"Продажа системе: <b>{get_proxy_void_sale_price(paid_cost)}</b>\n"
        f"Создан: <b>{format_dt(created_at)}</b>"
    )
    await render_message(user_id, text, build_proxy_item_menu(user_id, proxy_id, bool(bound_inventory_id), is_proxy_protected(proxy_id)), message_id=message_id)


async def show_vpn_menu(user_id: int, message_id: Optional[int] = None):
    settle_vpn_service(user_id)
    service = get_vpn_service(user_id)
    if not service:
        text = (
            "<b>VPN-сервис</b>\n\n"
            f"Запуск: <b>{VPN_SERVICE_CREATE_COST}</b>\n"
            "Это поздняя активность: сервис приносит деньги, если серверы держат нагрузку,\n"
            "цена не отпугивает клиентов, а реклама не съедает всю маржу."
        )
        await render_message(user_id, text, build_vpn_menu(user_id, None), message_id=message_id)
        return
    metrics = get_vpn_service_metrics(user_id, service)
    event_state = get_vpn_event_state(user_id)
    price = int(service[2])
    marketing = int(service[3])
    customers = int(service[4])
    active_text = "работает" if service[5] else "на паузе"
    event_line = (
        f"\nСобытие: <b>{escape(event_state['event_label'])}</b> до <b>{event_state['event_until'].strftime('%H:%M')}</b>"
        if event_state["event_label"] and event_state["event_until"]
        else "\nСобытие: <b>нет</b>"
    )
    text = (
        f"<b>{escape(service[1])}</b>\n\n"
        f"Статус: <b>{active_text}</b>\n"
        f"Уровень: <b>{metrics['level']}</b>\n"
        f"Цена подписки: <b>{price}</b>\n"
        f"Реклама: <b>{marketing}</b>\n"
        f"Клиентов: <b>{customers}</b>{' / цель <b>' + str(metrics['target_customers']) + '</b>' if metrics['capacity'] > 0 else ' / серверы еще не подключены'}\n"
        f"Емкость сети: <b>{metrics['capacity']}</b>\n"
        f"Подключено своих серверов: <b>{metrics['service_servers']}</b>\n"
        f"Арендовано у других: <b>{metrics['leased_in_servers']}</b>\n"
        f"Доход: <b>{metrics['hourly_income']}/ч</b>\n"
        f"Расходы: <b>{metrics['hourly_expenses']}/ч</b>\n"
        f"Аренда другим: <b>{metrics['leased_out_income']}/ч</b>\n"
        f"Итог: <b>{metrics['hourly_profit']}/ч</b>\n"
        f"Следующий уровень: <b>{metrics['level_upgrade_cost']}</b> монет. Для апгрейда нужна емкость не ниже <b>{metrics['level'] * 3}</b>.\n"
        f"Высокая цена режет спрос. Реклама поднимает спрос, но жрёт прибыль.{event_line}"
    )
    await render_message(user_id, text, build_vpn_menu(user_id, service), message_id=message_id)


async def show_vpn_market_menu(user_id: int, message_id: Optional[int] = None):
    listings = get_vpn_server_market_listings()
    lines = [
        "<b>VPN-рынок серверов</b>",
        "",
        f"Лотов: <b>{len(listings)}</b>",
        "Здесь можно арендовать чужой сервер для своего VPN."
    ]
    await render_message(user_id, "\n".join(lines), build_vpn_market_menu(user_id), message_id=message_id)


async def show_vpn_market_item_menu(user_id: int, listing_id: int, message_id: Optional[int] = None):
    item = get_vpn_server_market_item(listing_id)
    if not item:
        await render_message(user_id, "<b>Лот аренды не найден</b>", build_back_button("vpn_market_open"), message_id=message_id)
        return
    _, seller_id, proxy_id, price, status, server_name, bound_inventory_id = item
    if status != "active" or not bound_inventory_id:
        await render_message(user_id, "<b>Лот уже недоступен</b>", build_back_button("vpn_market_open"), message_id=message_id)
        return
    inv = get_inventory_item(bound_inventory_id)
    ip_text = inv[1] if inv else "неизвестно"
    text = (
        f"<b>{escape(server_name)}</b>\n\n"
        f"Сервер ID: <b>{proxy_id}</b>\n"
        f"Цена аренды: <b>{price}/ч</b>\n"
        f"IP: <b>{escape(ip_text)}</b>\n"
        f"Емкость для VPN: <b>{get_vpn_server_capacity_from_proxy(proxy_id)}</b>\n"
        f"Владелец: <b>{escape(get_user_display(seller_id))}</b>"
    )
    await render_message(user_id, text, build_vpn_market_item_menu(user_id, listing_id, seller_id), message_id=message_id)


async def show_votes_menu(user_id: int, message_id: Optional[int] = None):
    text = (
        "<b>Управление голосованиями</b>\n\n"
        "Раздел оставлен для модераторов.\n"
        "Текущие команды:\n"
        "/newvote\n"
        "/myvotes\n"
        "!fakeadd &lt;token&gt; &lt;index&gt;\n"
        "!fakeremove &lt;token&gt; &lt;index&gt;\n"
        "!fakeset &lt;token&gt; &lt;index&gt; &lt;count&gt;\n"
        "!fakeinfo &lt;token&gt;\n"
        "!extend &lt;token&gt; &lt;minutes&gt;\n"
        "!shuffle &lt;token&gt;\n"
        "/endvote &lt;token&gt;\n\n"
        f"Результаты удаляются через {RESULTS_AUTO_DELETE_SECONDS} сек."
    )
    await render_message(user_id, text, build_back_button(), message_id=message_id)


async def show_admin_panel(user_id: int, message_id: Optional[int] = None):
    stats = get_admin_stats()
    text = (
        "<b>Админ-панель</b>\n\n"
        f"Пользователей: <b>{stats['users']}</b>\n"
        f"IP в инвентарях: <b>{stats['inventory']}</b>\n"
        f"Активных лотов: <b>{stats['market']}</b>\n"
        f"Активных серверов: <b>{stats['proxies']}</b>\n"
        f"Пользователей с баном: <b>{stats['banned']}</b>\n"
        f"Монет в системе: <b>{stats['balance']}</b>\n\n"
        "Здесь можно открыть статистику, выбрать пользователя и управлять лимитами."
    )
    await render_message(user_id, text, build_admin_menu(), message_id=message_id)


async def show_admin_stats_menu(user_id: int, message_id: Optional[int] = None):
    stats = get_admin_stats()
    limits = get_ip_limits()
    text = (
        "<b>Статистика системы</b>\n\n"
        f"Пользователей: <b>{stats['users']}</b>\n"
        f"Инвентарь: <b>{stats['inventory']}</b>\n"
        f"Маркет: <b>{stats['market']}</b>\n"
        f"Серверы: <b>{stats['proxies']}</b>\n"
        f"Забанено: <b>{stats['banned']}</b>\n"
        f"Баланс в системе: <b>{stats['balance']}</b>\n\n"
        "<b>Остатки лимитов IP</b>\n"
        f"Обычный: <b>{limits.get('обычный', 0)}</b>\n"
        f"Белый x1: <b>{limits.get('белый_1', 0)}</b>\n"
        f"Белый x2: <b>{limits.get('белый_2', 0)}</b>\n"
        f"Белый x3: <b>{limits.get('белый_3', 0)}</b>\n"
        f"Джекпот: <b>{limits.get('джекпот', 0)}</b>\n"
        f"Гос. подсеть: <b>{limits.get('гос_подсеть', 0)}</b>"
    )
    await render_message(user_id, text, build_back_button("menu_admin"), message_id=message_id)


async def show_admin_users_menu(user_id: int, message_id: Optional[int] = None):
    users = get_recent_users()
    lines = [
        "<b>Последние активные пользователи</b>",
        "",
    ]
    if not users:
        lines.append("Пользователей пока нет.")
    else:
        for target_user_id, username, first_name, last_name, balance, last_activity in users:
            name = f"@{username}" if username else (first_name or str(target_user_id))
            if last_name and not username and first_name:
                name = f"{first_name} {last_name}"
            lines.append(
                f"• <b>{escape(name)}</b> [{target_user_id}]\n"
                f"  Баланс: {balance} | Активность: {format_dt(last_activity)}"
            )
    await render_message(user_id, "\n".join(lines), build_admin_users_menu(users), message_id=message_id)


def build_admin_user_text(snapshot: Dict[str, object]) -> str:
    ban_until = snapshot["ban_until"]
    hold_until = snapshot["hold_until"]
    name = escape(get_user_display(snapshot["user_id"]))
    username = f"@{snapshot['username']}" if snapshot["username"] else "нет"
    display_nick = escape(snapshot["display_nick"] or "нет")
    ban_text = format_dt(ban_until) if ban_until else "нет"
    hold_text = (
        f"{snapshot['hold_amount']} до {format_dt(hold_until)}"
        if hold_until and snapshot["hold_amount"]
        else "нет"
    )
    return (
        f"<b>Пользователь {name}</b>\n\n"
        f"ID: <b>{snapshot['user_id']}</b>\n"
        f"Username: <b>{escape(username)}</b>\n"
        f"Display nick: <b>{display_nick}</b>\n"
        f"Баланс: <b>{snapshot['balance']}</b>\n"
        f"Доступно: <b>{snapshot['available_balance']}</b>\n"
        f"Квота серверов: <b>{snapshot['proxy_quota']}</b>\n"
        f"IP в инвентаре: <b>{snapshot['inventory_count']}</b>\n"
        f"Серверов: <b>{snapshot['proxies_count']}</b>\n"
        f"Лотов на маркете: <b>{snapshot['market_count']}</b>\n"
        f"Бан до: <b>{ban_text}</b>\n"
        f"Холд: <b>{hold_text}</b>\n"
        f"Активность: <b>{format_dt(snapshot['last_activity'])}</b>"
    )


async def show_admin_user_menu(user_id: int, target_user_id: int, message_id: Optional[int] = None):
    snapshot = get_user_admin_snapshot(target_user_id)
    if not snapshot:
        await render_message(
            user_id,
            "<b>Пользователь не найден</b>",
            build_back_button("admin_users"),
            message_id=message_id,
        )
        return
    await render_message(
        user_id,
        build_admin_user_text(snapshot),
        build_admin_user_menu(target_user_id),
        message_id=message_id,
    )


async def open_section(user_id: int, message_id: int, section: str):
    if section == "menu_main":
        await show_main_panel(user_id, message_id)
    elif section == "menu_balance":
        await show_balance_menu(user_id, message_id)
    elif section == "menu_inventory":
        await show_inventory_menu(user_id, message_id)
    elif section == "menu_market":
        await show_market_menu(user_id, message_id)
    elif section == "menu_my_lots":
        await show_my_lots_menu(user_id, message_id)
    elif section == "menu_vpn":
        await show_vpn_menu(user_id, message_id)
    elif section == "menu_roulette":
        await show_roulette_menu(user_id, message_id)
    elif section == "menu_hosters":
        await show_hosters_menu(user_id, message_id)
    elif section == "menu_proxies":
        await show_proxies_menu(user_id, message_id)
    elif section == "menu_admin" and is_admin(user_id):
        await show_admin_panel(user_id, message_id)
    elif section == "menu_votes" and is_moderator(user_id):
        await show_votes_menu(user_id, message_id)


# ========== ФОНОВЫЕ ЗАДАЧИ ==========
async def auto_end_expired_votes():
    while True:
        now = datetime.now()
        expired_tokens = []
        for token, data in list(active_votes.items()):
            if now >= data["end_time"]:
                expired_tokens.append(token)

        for token in expired_tokens:
            vote_data = active_votes[token]
            vote_id = vote_data["vote_id"]
            results_text = get_results_text(vote_id, vote_data["title"])
            try:
                await bot.send_message(
                    vote_data["chat_id"],
                    f"⏰ <b>Голосование завершено автоматически</b>\n\n{results_text}",
                    parse_mode="HTML",
                    message_thread_id=vote_data["thread_id"] or None,
                )
                await bot.delete_message(vote_data["chat_id"], vote_data["poll_message_id"])
            except Exception:
                pass

            cursor.execute("UPDATE votes SET is_active=0 WHERE vote_id=?", (vote_id,))
            conn.commit()
            del active_votes[token]
            log_admin_action(vote_id, "auto_end", "Автоматическое завершение")

        await asyncio.sleep(60)


async def auto_daily_bonus():
    while True:
        await asyncio.sleep(1800)
        cursor.execute("SELECT user_id FROM users")
        for (user_id,) in cursor.fetchall():
            grant_daily_bonus_if_available(user_id)


async def auto_income():
    while True:
        await asyncio.sleep(INCOME_INTERVAL * 60)
        cursor.execute("SELECT user_id FROM users")
        for (user_id,) in cursor.fetchall():
            income = get_proxy_income_per_hour(user_id)
            if income > 0:
                add_balance(user_id, income, f"Пассивный доход от обходок ({income} монет)")
            if not get_vpn_service(user_id):
                rent_income = get_vpn_server_rental_income_per_hour(user_id)
                if rent_income > 0:
                    add_balance(user_id, rent_income, f"Аренда серверов для чужих VPN ({rent_income} монет)")
            settle_vpn_service(user_id)


async def auto_random_events():
    while True:
        await asyncio.sleep(900)
        cursor.execute("SELECT user_id FROM users")
        for (user_id,) in cursor.fetchall():
            events = apply_random_event(user_id, "РКН", BACKGROUND_RANDOM_EVENT_CHANCE)
            if events:
                await notify_user(
                    user_id,
                    "<b>Случайное событие</b>\n\n" + "\n".join(events),
                    build_main_menu(user_id),
                )
            vpn_event = apply_vpn_random_event(user_id)
            if vpn_event:
                await notify_user(
                    user_id,
                    "<b>VPN-событие</b>\n\n" + vpn_event,
                    build_main_menu(user_id),
                )


async def auto_microloans():
    while True:
        await asyncio.sleep(300)
        cursor.execute(
            """
            SELECT user_id, total_due, due_at, warned, warning_sent_at
            FROM microloans
            WHERE status='active'
        """
        )
        now = datetime.now()
        for user_id, total_due, due_at_str, warned, warning_sent_at_str in cursor.fetchall():
            due_at = datetime.fromisoformat(due_at_str)
            if now < due_at:
                continue
            if not warned:
                cursor.execute(
                    "UPDATE microloans SET warned=1, warning_sent_at=? WHERE user_id=? AND status='active'",
                    (now.isoformat(), user_id),
                )
                conn.commit()
                await notify_user(
                    user_id,
                    (
                        "<b>Предупреждение по микрозайму</b>\n\n"
                        f"Вы просрочили платёж <b>{total_due}</b> монет.\n"
                        f"У вас есть только <b>{MICROLOAN_WARNING_MINUTES}</b> минут на погашение.\n"
                        "После этого будет полная конфискация всего имущества и денег."
                    ),
                    build_balance_actions_menu(user_id),
                )
                continue
            warning_sent_at = datetime.fromisoformat(warning_sent_at_str) if warning_sent_at_str else due_at
            if now >= warning_sent_at + timedelta(minutes=MICROLOAN_WARNING_MINUTES):
                wipe_user_assets_for_microloan(user_id)
                await notify_user(
                    user_id,
                    (
                        "<b>Взыскание по микрозайму</b>\n\n"
                        "Срок после предупреждения вышел.\n"
                        "Конфисковано всё: IP, аккаунты, серверы, VPN, лоты и монеты."
                    ),
                    build_main_menu(user_id),
                )


async def auto_reset_limits():
    while True:
        now = datetime.now()
        next_reset = now.replace(hour=RESET_LIMITS_HOUR, minute=0, second=0, microsecond=0)
        if now >= next_reset:
            next_reset += timedelta(days=1)
        await asyncio.sleep((next_reset - now).total_seconds())
        reset_ip_limits()
        log_admin_action(0, "reset_limits", "Сброс лимитов IP")


# ========== КОМАНДЫ ==========
@dp.message(Command("start"))
async def start_command(message: Message):
    ensure_user(message.from_user)
    if message.chat.type != "private":
        await message.answer("Откройте бота в личке и используйте /panel.")
        return

    text = (
        "<b>Бот для новой системы круток IP</b>\n\n"
        "Основные разделы вынесены в интерактивную панель.\n"
        "Команды для быстрого входа:\n"
        "/panel\n"
        "/balance\n"
        "/myips\n"
        "/market\n"
        "/hosters\n"
        "/proxies\n\n"
        "Крутка IP доступна только в чате командами /крутить и /крутить10."
    )
    await message.answer(text, parse_mode="HTML", reply_markup=build_main_menu(message.from_user.id))


@dp.message(Command("panel"))
async def panel_command(message: Message):
    ensure_user(message.from_user)
    if message.chat.type != "private":
        await message.answer("Панель доступна только в личных сообщениях.")
        return
    await show_main_panel(message.from_user.id)


@dp.message(Command("balance"))
async def balance_command(message: Message):
    ensure_user(message.from_user)
    if message.chat.type != "private":
        await message.answer("Баланс удобнее смотреть в личных сообщениях: /panel")
        return
    await show_balance_menu(message.from_user.id)


@dp.message(Command("myips"))
async def myips_command(message: Message):
    ensure_user(message.from_user)
    if message.chat.type != "private":
        await message.answer("Инвентарь доступен в личке: /panel")
        return
    await show_inventory_menu(message.from_user.id)


@dp.message(Command("market"))
async def market_command(message: Message):
    ensure_user(message.from_user)
    if message.chat.type != "private":
        await message.answer("Маркет доступен в личке: /panel")
        return
    await show_market_menu(message.from_user.id)


@dp.message(Command("hosters"))
async def hosters_command(message: Message):
    ensure_user(message.from_user)
    if message.chat.type != "private":
        await message.answer("Хостеры доступны в личке: /panel")
        return
    await show_hosters_menu(message.from_user.id)


@dp.message(Command("proxies"))
async def proxies_command(message: Message):
    ensure_user(message.from_user)
    if message.chat.type != "private":
        await message.answer("Серверы доступны в личке: /panel")
        return
    await show_proxies_menu(message.from_user.id)


@dp.message(Command("admin"))
async def admin_command(message: Message):
    ensure_user(message.from_user)
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа.")
        return
    if message.chat.type != "private":
        await message.answer("Админ-панель доступна только в личных сообщениях.")
        return
    await show_admin_panel(message.from_user.id)


@dp.message(Command("give"))
async def give_command(message: Message):
    ensure_user(message.from_user)
    parts = message.text.split(maxsplit=2)
    if len(parts) != 3:
        await message.answer("Использование: /give @user 15")
        return

    target_raw = parts[1].strip()
    amount_raw = parts[2].strip()
    if not amount_raw.isdigit():
        await message.answer("Сумма должна быть целым положительным числом.")
        return

    amount = int(amount_raw)
    if amount <= 0:
        await message.answer("Сумма должна быть больше нуля.")
        return

    target_user_id = find_user_id_by_handle(target_raw)
    if target_user_id is None:
        await message.answer("Пользователь не найден. Он должен хотя бы раз запустить бота.")
        return
    if target_user_id == message.from_user.id:
        await message.answer("Себе переводить нельзя.")
        return
    if get_available_balance(message.from_user.id) < amount:
        await message.answer(
            f"Недостаточно доступных монет: {get_available_balance(message.from_user.id)}/{amount}."
        )
        return

    if not transfer_balance(message.from_user.id, target_user_id, amount):
        await message.answer("Перевод не выполнен.")
        return

    update_activity(message.from_user.id)
    update_activity(target_user_id)
    await message.answer(
        f"Переведено <b>{amount}</b> монет пользователю <b>{escape(get_user_display(target_user_id))}</b>.",
        parse_mode="HTML",
    )


@dp.message(Command("крутить"))
async def spin_command(message: Message):
    ensure_user(message.from_user)
    if message.chat.type == "private":
        await message.answer("Крутка доступна только в чате или группе. В личке используйте /panel для управления IP.")
        return
    result = spin_ip_for_user(message.from_user.id)
    if not result["ok"]:
        await message.answer(f"❌ {escape(result['error'])}", parse_mode="HTML")
        return

    await message.answer(
        build_spin_result_text(result),
        parse_mode="HTML",
    )


@dp.message(Command("крутить10"))
async def spin10_command(message: Message):
    ensure_user(message.from_user)
    if message.chat.type == "private":
        await message.answer("Пакетная крутка доступна только в чате или группе.")
        return
    result = spin_ten_for_user(message.from_user.id)
    if not result["ok"]:
        await message.answer(f"❌ {escape(result['error'])}", parse_mode="HTML")
        return
    await message.answer(build_spin_ten_result_text(result), parse_mode="HTML")


@dp.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext):
    ensure_user(message.from_user)
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=build_main_menu(message.from_user.id))


# ========== CALLBACK-НАВИГАЦИЯ ==========
@dp.callback_query(F.data.in_(("menu_main", "menu_balance", "menu_inventory", "menu_market", "menu_my_lots", "menu_vpn", "menu_roulette", "menu_hosters", "menu_proxies", "menu_votes", "menu_admin")))
async def menu_callback(callback: CallbackQuery, state: FSMContext):
    ensure_user(callback.from_user)
    await state.clear()
    if callback.data == "menu_votes" and not is_moderator(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    if callback.data == "menu_admin" and not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await open_section(callback.from_user.id, callback.message.message_id, callback.data)
    await callback.answer()


@dp.callback_query(F.data.startswith("inventory_view_"))
async def inventory_view_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    inventory_id = int(callback.data.split("_")[2])
    await show_inventory_item_menu(callback.from_user.id, inventory_id, callback.message.message_id)
    await callback.answer()


@dp.callback_query(F.data.startswith("market_view_"))
async def market_view_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    listing_id = int(callback.data.split("_")[2])
    await show_market_item_menu(callback.from_user.id, listing_id, callback.message.message_id)
    await callback.answer()


@dp.callback_query(F.data.startswith("hoster_market_view_"))
async def hoster_market_view_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    listing_id = int(callback.data.split("_")[3])
    await show_hoster_market_item_menu(callback.from_user.id, listing_id, callback.message.message_id)
    await callback.answer()


@dp.callback_query(F.data.startswith("hoster_view_"))
async def hoster_view_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    account_id = int(callback.data.split("_")[2])
    await show_hoster_item_menu(callback.from_user.id, account_id, callback.message.message_id)
    await callback.answer()


@dp.callback_query(F.data.startswith("hoster_shop_view_"))
async def hoster_shop_view_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    provider_key = callback.data.split("_", 3)[3]
    if provider_key not in HOSTER_CONFIGS:
        await callback.answer("Неизвестный хостер", show_alert=True)
        return
    await show_hoster_shop_view(callback.from_user.id, provider_key, callback.message.message_id)
    await callback.answer()


@dp.callback_query(F.data.startswith("proxy_view_"))
async def proxy_view_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    proxy_id = int(callback.data.split("_")[2])
    await show_proxy_item_menu(callback.from_user.id, proxy_id, callback.message.message_id)
    await callback.answer()


@dp.callback_query(F.data == "admin_stats")
async def admin_stats_callback(callback: CallbackQuery, state: FSMContext):
    ensure_user(callback.from_user)
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.clear()
    await show_admin_stats_menu(callback.from_user.id, callback.message.message_id)
    await callback.answer()


@dp.callback_query(F.data == "admin_users")
async def admin_users_callback(callback: CallbackQuery, state: FSMContext):
    ensure_user(callback.from_user)
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.clear()
    await show_admin_users_menu(callback.from_user.id, callback.message.message_id)
    await callback.answer()


@dp.callback_query(F.data == "admin_find_user")
async def admin_find_user_callback(callback: CallbackQuery, state: FSMContext):
    ensure_user(callback.from_user)
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(AdminUserFSM.waiting_target)
    await state.update_data(admin_action="find_user")
    await callback.message.edit_text(
        "<b>Поиск пользователя</b>\n\nОтправьте ID или @username.",
        parse_mode="HTML",
        reply_markup=build_back_button("menu_admin"),
    )
    await callback.answer()


@dp.callback_query(F.data == "admin_reset_limits")
async def admin_reset_limits_callback(callback: CallbackQuery, state: FSMContext):
    ensure_user(callback.from_user)
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.clear()
    reset_ip_limits()
    log_admin_action(0, "admin_reset_limits", f"Лимиты сброшены админом {callback.from_user.id}")
    await show_admin_panel(callback.from_user.id, callback.message.message_id)
    await callback.answer("Лимиты IP сброшены", show_alert=True)


@dp.callback_query(F.data.startswith("admin_user_"))
async def admin_user_callback(callback: CallbackQuery, state: FSMContext):
    ensure_user(callback.from_user)
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.clear()
    target_user_id = int(callback.data.split("_")[2])
    await show_admin_user_menu(callback.from_user.id, target_user_id, callback.message.message_id)
    await callback.answer()


@dp.callback_query(F.data.startswith("admin_grant_"))
async def admin_grant_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    _, _, user_id_str, amount_str = callback.data.split("_", 3)
    target_user_id = int(user_id_str)
    amount = int(amount_str)
    get_user(target_user_id)
    add_balance(target_user_id, amount, f"Админ начислил {amount}")
    log_admin_action(0, "grant_balance", f"admin={callback.from_user.id}, user={target_user_id}, amount={amount}")
    await show_admin_user_menu(callback.from_user.id, target_user_id, callback.message.message_id)
    await callback.answer(f"Выдано {amount}", show_alert=True)


@dp.callback_query(F.data.startswith("admin_unban_"))
async def admin_unban_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    target_user_id = int(callback.data.split("_")[2])
    clear_user_ban(target_user_id)
    log_admin_action(0, "unban_user", f"admin={callback.from_user.id}, user={target_user_id}")
    await show_admin_user_menu(callback.from_user.id, target_user_id, callback.message.message_id)
    await callback.answer("Бан снят", show_alert=True)


@dp.callback_query(F.data.startswith("admin_clear_hold_"))
async def admin_clear_hold_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    target_user_id = int(callback.data.split("_")[3])
    cursor.execute(
        "UPDATE users SET hoster_hold_amount=0, hoster_hold_until=NULL WHERE user_id=?",
        (target_user_id,),
    )
    conn.commit()
    log_admin_action(0, "clear_hold", f"admin={callback.from_user.id}, user={target_user_id}")
    await show_admin_user_menu(callback.from_user.id, target_user_id, callback.message.message_id)
    await callback.answer("Холд снят", show_alert=True)


@dp.callback_query(F.data.startswith("admin_confiscate_confirm_"))
async def admin_confiscate_confirm_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    target_user_id = int(callback.data.split("_")[3])
    confiscate_all_user_assets(target_user_id)
    log_admin_action(0, "confiscate_all", f"admin={callback.from_user.id}, user={target_user_id}")
    await notify_user(
        target_user_id,
        "<b>Административная конфискация</b>\n\nУ вас конфисковано всё имущество: IP, аккаунты, серверы, VPN, лоты и монеты.",
    )
    await show_admin_user_menu(callback.from_user.id, target_user_id, callback.message.message_id)
    await callback.answer("Имущество конфисковано", show_alert=True)


@dp.callback_query(F.data.startswith("admin_confiscate_"))
async def admin_confiscate_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    target_user_id = int(callback.data.split("_")[2])
    await callback.message.edit_text(
        (
            "<b>Подтверждение конфискации</b>\n\n"
            f"Пользователь: <b>{target_user_id}</b>\n"
            "Будут конфискованы все IP, аккаунты, серверы, VPN, лоты и монеты."
        ),
        parse_mode="HTML",
        reply_markup=build_admin_confiscation_menu(target_user_id),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("admin_prompt_"))
async def admin_prompt_callback(callback: CallbackQuery, state: FSMContext):
    ensure_user(callback.from_user)
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    payload = callback.data.removeprefix("admin_prompt_")
    action, target_user_id_str = payload.rsplit("_", 1)
    target_user_id = int(target_user_id_str)
    await state.update_data(target_user_id=target_user_id, admin_action=action)

    prompt = "Введите значение."
    target_state = AdminUserFSM.waiting_amount
    if action == "balance_add":
        prompt = f"<b>Начисление монет</b>\n\nПользователь: <b>{target_user_id}</b>\nВведите сумму."
    elif action == "balance_set":
        prompt = f"<b>Установка баланса</b>\n\nПользователь: <b>{target_user_id}</b>\nВведите новый баланс."
    elif action == "ban":
        prompt = f"<b>Бан пользователя</b>\n\nПользователь: <b>{target_user_id}</b>\nВведите длительность в минутах."
        target_state = AdminUserFSM.waiting_ban_minutes
    elif action == "quota":
        prompt = f"<b>Квота серверов</b>\n\nПользователь: <b>{target_user_id}</b>\nВведите новую квоту."
        target_state = AdminUserFSM.waiting_quota
    elif action == "nick":
        prompt = f"<b>Смена ника</b>\n\nПользователь: <b>{target_user_id}</b>\nОтправьте новый ник."
        target_state = AdminUserFSM.waiting_nick

    await state.set_state(target_state)
    await callback.message.edit_text(
        prompt,
        parse_mode="HTML",
        reply_markup=build_back_button(f"admin_user_{target_user_id}"),
    )
    await callback.answer()


# ========== ПРОДАЖА IP ==========
@dp.callback_query(F.data.startswith("inventory_sell_"))
async def inventory_sell_callback(callback: CallbackQuery, state: FSMContext):
    ensure_user(callback.from_user)
    inventory_id = int(callback.data.split("_")[2])
    item = get_inventory_item(inventory_id)
    if not item:
        await callback.answer("IP не найден", show_alert=True)
        return

    owner_id, ip_type, is_sold, _, usable_state, _ = item
    if owner_id != callback.from_user.id:
        await callback.answer("Это не ваш IP", show_alert=True)
        return
    if is_sold:
        await callback.answer("IP уже недоступен", show_alert=True)
        return
    if not is_special_ip_type(ip_type):
        await callback.answer("Продавать можно только редкие и специальные IP", show_alert=True)
        return
    if usable_state == "confiscated":
        await callback.answer("Этот IP уже конфискован", show_alert=True)
        return
    if has_active_listing(inventory_id):
        await callback.answer("Этот IP уже выставлен на маркет", show_alert=True)
        return
    if get_server_bound_to_inventory(inventory_id):
        await callback.answer("Сначала отвяжите IP от сервера", show_alert=True)
        return

    suggestion = get_sell_price_suggestion(ip_type, usable_state)
    await state.set_state(SellFSM.waiting_price)
    await state.update_data(inventory_id=inventory_id)
    await callback.message.edit_text(
        build_sell_prompt_text(inventory_id, ip_type, suggestion),
        parse_mode="HTML",
        reply_markup=build_sell_price_menu(inventory_id, suggestion),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("sellquick_"))
async def sell_quick_callback(callback: CallbackQuery, state: FSMContext):
    ensure_user(callback.from_user)
    _, inventory_id_str, price_str = callback.data.split("_", 2)
    inventory_id = int(inventory_id_str)
    price = int(price_str)

    item = get_inventory_item(inventory_id)
    if not item:
        await callback.answer("IP не найден", show_alert=True)
        return

    owner_id, ip_type, is_sold, _, usable_state, _ = item
    if owner_id != callback.from_user.id or is_sold:
        await callback.answer("IP уже недоступен", show_alert=True)
        return
    if usable_state == "confiscated":
        await callback.answer("IP конфискован", show_alert=True)
        return
    if has_active_listing(inventory_id):
        await callback.answer("Этот IP уже выставлен на маркет", show_alert=True)
        return
    if get_server_bound_to_inventory(inventory_id):
        await callback.answer("Сначала отвяжите IP от сервера", show_alert=True)
        return

    listing_id = create_market_listing(callback.from_user.id, inventory_id, price)
    update_activity(callback.from_user.id)
    await state.clear()
    await callback.message.edit_text(
        (
            f"✅ <b>Лот создан</b>\n\n"
            f"Лот: <b>ID {listing_id}</b>\n"
            f"IP: <b>{escape(ip_type)}</b>\n"
            f"Цена: <b>{price}</b>"
        ),
        parse_mode="HTML",
        reply_markup=build_market_menu(get_active_market_listings(), callback.from_user.id),
    )
    await callback.answer("Лот выставлен")


@dp.callback_query(F.data.startswith("inventory_delete_"))
async def inventory_delete_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    inventory_id = int(callback.data.split("_")[2])
    item = get_inventory_item(inventory_id)
    if not item:
        await callback.answer("IP не найден", show_alert=True)
        return

    owner_id, ip_type, is_sold, _, usable_state, _ = item
    if owner_id != callback.from_user.id:
        await callback.answer("Это не ваш IP", show_alert=True)
        return
    if is_sold:
        await callback.answer("IP уже недоступен", show_alert=True)
        return
    if usable_state == "confiscated":
        await callback.answer("IP уже конфискован", show_alert=True)
        return
    if has_active_listing(inventory_id):
        await callback.answer("Сначала снимите лот с маркета", show_alert=True)
        return
    if get_server_bound_to_inventory(inventory_id):
        await callback.answer("Сначала отвяжите IP от сервера", show_alert=True)
        return

    payout = sell_inventory_to_system(inventory_id, callback.from_user.id)
    if payout <= 0:
        await callback.answer("Не удалось продать IP системе", show_alert=True)
        return

    update_activity(callback.from_user.id)
    balance = get_balance(callback.from_user.id)
    await callback.message.edit_text(
        (
            f"✅ <b>IP продан системе</b>\n\n"
            f"IP: <b>{escape(ip_type)}</b>\n"
            f"Получено: <b>{payout}</b> монет\n"
            f"Баланс: <b>{balance}</b>"
        ),
        parse_mode="HTML",
        reply_markup=build_inventory_menu(get_inventory_for_display(callback.from_user.id)),
    )
    await callback.answer("IP продан системе")


@dp.callback_query(F.data == "inventory_bulk_sell")
async def inventory_bulk_sell_callback(callback: CallbackQuery, state: FSMContext):
    ensure_user(callback.from_user)
    await state.clear()
    BULK_SELL_SELECTIONS[callback.from_user.id] = []
    await show_bulk_sell_menu(callback.from_user.id, callback.message.message_id)
    await callback.answer()


@dp.callback_query(F.data.startswith("inventory_protect_ask_"))
async def inventory_protect_ask_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    inventory_id = int(callback.data.split("_")[3])
    item = get_inventory_item(inventory_id)
    if not item:
        await callback.answer("IP не найден", show_alert=True)
        return
    owner_id, ip_type, is_sold, acquired_at, _, protected = item
    if owner_id != callback.from_user.id or is_sold:
        await callback.answer("IP уже недоступен", show_alert=True)
        return
    if protected:
        await callback.answer("IP уже защищен", show_alert=True)
        return
    cost = get_ip_protection_cost(ip_type)
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=f"Оплатить {cost}", callback_data=f"inventory_protect_confirm_{inventory_id}"))
    builder.add(InlineKeyboardButton(text="◀️ Назад к IP", callback_data=f"inventory_view_{inventory_id}"))
    builder.adjust(1)
    await callback.message.edit_text(
        build_inventory_item_text(inventory_id, ip_type, acquired_at) + f"\n\nЗащита РКН стоит <b>{cost}</b> монет.\nПосле оплаты конфискация этого IP через случайные события больше не сработает.",
        parse_mode="HTML",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("inventory_protect_confirm_"))
async def inventory_protect_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    inventory_id = int(callback.data.split("_")[3])
    item = get_inventory_item(inventory_id)
    if not item:
        await callback.answer("IP не найден", show_alert=True)
        return
    owner_id, ip_type, is_sold, acquired_at, _, protected = item
    if owner_id != callback.from_user.id or is_sold:
        await callback.answer("IP уже недоступен", show_alert=True)
        return
    if protected:
        await callback.answer("IP уже защищен", show_alert=True)
        return
    cost = get_ip_protection_cost(ip_type)
    if get_available_balance(callback.from_user.id) < cost:
        await callback.answer(f"Не хватает монет: нужно {cost}", show_alert=True)
        return
    balance = add_balance(callback.from_user.id, -cost, f"Защита IP ID {inventory_id} в РКН")
    protect_inventory_item(inventory_id)
    update_activity(callback.from_user.id)
    await callback.message.edit_text(
        build_inventory_item_text(inventory_id, ip_type, acquired_at) + f"\nЗащита оплачена: <b>{cost}</b>\nБаланс: <b>{balance}</b>",
        parse_mode="HTML",
        reply_markup=build_inventory_item_menu(inventory_id, ip_type, has_active_listing(inventory_id), get_server_bound_to_inventory(inventory_id) is not None, True),
    )
    await callback.answer("Защита оформлена")


@dp.message(AdminUserFSM.waiting_target, F.text)
async def admin_target_input(message: Message, state: FSMContext):
    ensure_user(message.from_user)
    if not is_admin(message.from_user.id):
        await state.clear()
        await message.answer("Нет доступа.")
        return
    target_user_id = parse_user_lookup(message.text)
    if target_user_id is None:
        await message.answer("Не удалось распознать пользователя. Отправьте ID или @username.")
        return
    await state.clear()
    await show_admin_user_menu(message.from_user.id, target_user_id)


@dp.message(AdminUserFSM.waiting_amount, F.text)
async def admin_amount_input(message: Message, state: FSMContext):
    ensure_user(message.from_user)
    if not is_admin(message.from_user.id):
        await state.clear()
        await message.answer("Нет доступа.")
        return
    value = message.text.strip()
    if not value.lstrip("-").isdigit():
        await message.answer("Нужно целое число.")
        return
    amount = int(value)
    data = await state.get_data()
    target_user_id = data.get("target_user_id")
    action = data.get("admin_action")
    if not target_user_id or action not in {"balance_add", "balance_set"}:
        await state.clear()
        await message.answer("Админ-действие сброшено.")
        return
    get_user(target_user_id)
    if action == "balance_add":
        add_balance(target_user_id, amount, f"Админ изменил баланс на {amount}")
        log_admin_action(0, "balance_add", f"admin={message.from_user.id}, user={target_user_id}, amount={amount}")
    else:
        set_balance(target_user_id, amount)
        log_admin_action(0, "balance_set", f"admin={message.from_user.id}, user={target_user_id}, amount={amount}")
    await state.clear()
    await message.answer(
        build_admin_user_text(get_user_admin_snapshot(target_user_id)),
        parse_mode="HTML",
        reply_markup=build_admin_user_menu(target_user_id),
    )


@dp.message(AdminUserFSM.waiting_ban_minutes, F.text)
async def admin_ban_input(message: Message, state: FSMContext):
    ensure_user(message.from_user)
    if not is_admin(message.from_user.id):
        await state.clear()
        await message.answer("Нет доступа.")
        return
    value = message.text.strip()
    if not value.isdigit():
        await message.answer("Нужно указать число минут.")
        return
    minutes = int(value)
    data = await state.get_data()
    target_user_id = data.get("target_user_id")
    if not target_user_id:
        await state.clear()
        await message.answer("Админ-действие сброшено.")
        return
    get_user(target_user_id)
    set_user_ban_minutes(target_user_id, minutes)
    log_admin_action(0, "ban_user", f"admin={message.from_user.id}, user={target_user_id}, minutes={minutes}")
    await state.clear()
    await message.answer(
        build_admin_user_text(get_user_admin_snapshot(target_user_id)),
        parse_mode="HTML",
        reply_markup=build_admin_user_menu(target_user_id),
    )


@dp.message(AdminUserFSM.waiting_quota, F.text)
async def admin_quota_input(message: Message, state: FSMContext):
    ensure_user(message.from_user)
    if not is_admin(message.from_user.id):
        await state.clear()
        await message.answer("Нет доступа.")
        return
    value = message.text.strip()
    if not value.isdigit():
        await message.answer("Нужно указать целое число.")
        return
    quota = int(value)
    data = await state.get_data()
    target_user_id = data.get("target_user_id")
    if not target_user_id:
        await state.clear()
        await message.answer("Админ-действие сброшено.")
        return
    get_user(target_user_id)
    set_user_proxy_quota(target_user_id, quota)
    log_admin_action(0, "set_quota", f"admin={message.from_user.id}, user={target_user_id}, quota={quota}")
    await state.clear()
    await message.answer(
        build_admin_user_text(get_user_admin_snapshot(target_user_id)),
        parse_mode="HTML",
        reply_markup=build_admin_user_menu(target_user_id),
    )


@dp.message(AdminUserFSM.waiting_nick, F.text)
async def admin_nick_input(message: Message, state: FSMContext):
    ensure_user(message.from_user)
    if not is_admin(message.from_user.id):
        await state.clear()
        await message.answer("Нет доступа.")
        return
    nick = message.text.strip()
    if len(nick) < 2:
        await message.answer("Ник слишком короткий.")
        return
    data = await state.get_data()
    target_user_id = data.get("target_user_id")
    if not target_user_id:
        await state.clear()
        await message.answer("Админ-действие сброшено.")
        return
    get_user(target_user_id)
    set_user_nick(target_user_id, nick)
    log_admin_action(0, "set_nick", f"admin={message.from_user.id}, user={target_user_id}, nick={nick}")
    await state.clear()
    await message.answer(
        build_admin_user_text(get_user_admin_snapshot(target_user_id)),
        parse_mode="HTML",
        reply_markup=build_admin_user_menu(target_user_id),
    )


@dp.message(SellFSM.waiting_price, F.text)
async def sell_price_input(message: Message, state: FSMContext):
    ensure_user(message.from_user)
    price_text = message.text.strip()
    if not price_text.isdigit():
        await message.answer("Нужна целая положительная цена.")
        return

    price = int(price_text)
    if price <= 0:
        await message.answer("Цена должна быть больше нуля.")
        return

    data = await state.get_data()
    inventory_id = data.get("inventory_id")
    item = get_inventory_item(inventory_id) if inventory_id else None
    if not inventory_id or not item:
        await state.clear()
        await message.answer("IP для продажи не найден. Начните заново из инвентаря.")
        return

    owner_id, ip_type, is_sold, _, usable_state, _ = item
    if owner_id != message.from_user.id or is_sold or has_active_listing(inventory_id) or get_server_bound_to_inventory(inventory_id):
        await state.clear()
        await message.answer("Этот IP уже недоступен для продажи.")
        return
    if usable_state == "confiscated":
        await state.clear()
        await message.answer("Этот IP уже конфискован.")
        return

    listing_id = create_market_listing(message.from_user.id, inventory_id, price)
    update_activity(message.from_user.id)
    await state.clear()
    await message.answer(
        (
            f"✅ Лот создан.\n\n"
            f"Лот: <b>ID {listing_id}</b>\n"
            f"IP: <b>{escape(ip_type)}</b>\n"
            f"Цена: <b>{price}</b>"
        ),
        parse_mode="HTML",
        reply_markup=build_main_menu(message.from_user.id),
    )


@dp.message(BulkSellFSM.waiting_ids, F.text)
async def bulk_sell_input(message: Message, state: FSMContext):
    ensure_user(message.from_user)
    raw_ids = [part for part in message.text.replace(",", " ").split() if part]
    if not raw_ids:
        await message.answer("Нужны ID через пробел или запятую.")
        return
    if not all(part.isdigit() for part in raw_ids):
        await message.answer("Все ID должны быть числами.")
        return

    sold = []
    skipped = []
    total = 0
    for inventory_id in [int(part) for part in raw_ids]:
        payout = sell_inventory_to_system(inventory_id, message.from_user.id)
        if payout > 0:
            total += payout
            sold.append(str(inventory_id))
        else:
            skipped.append(str(inventory_id))

    await state.clear()
    if not sold:
        await message.answer("Ничего не продалось. Проверьте, что IP свободны и не стоят на маркете.")
        return

    update_activity(message.from_user.id)
    lines = [
        "<b>Массовая продажа завершена</b>",
        "",
        f"Продано IP: <b>{', '.join(sold)}</b>",
        f"Получено: <b>{total}</b> монет",
        f"Баланс: <b>{get_balance(message.from_user.id)}</b>",
    ]
    if skipped:
        lines.append(f"Пропущены: <b>{', '.join(skipped)}</b>")
    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=build_main_menu(message.from_user.id))


@dp.callback_query(F.data.startswith("bulk_toggle_"))
async def bulk_toggle_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    inventory_id = int(callback.data.split("_")[2])
    selected = BULK_SELL_SELECTIONS.setdefault(callback.from_user.id, [])
    if inventory_id in selected:
        selected.remove(inventory_id)
    else:
        selected.append(inventory_id)
    await show_bulk_sell_menu(callback.from_user.id, callback.message.message_id)
    await callback.answer()


@dp.callback_query(F.data == "bulk_sell_clear")
async def bulk_sell_clear_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    BULK_SELL_SELECTIONS[callback.from_user.id] = []
    await show_bulk_sell_menu(callback.from_user.id, callback.message.message_id)
    await callback.answer("Выбор очищен")


@dp.callback_query(F.data == "bulk_sell_confirm")
async def bulk_sell_confirm_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    selected = BULK_SELL_SELECTIONS.get(callback.from_user.id, [])
    if not selected:
        await callback.answer("Сначала выберите IP", show_alert=True)
        return
    sold = []
    skipped = []
    total = 0
    for inventory_id in list(selected):
        payout = sell_inventory_to_system(inventory_id, callback.from_user.id)
        if payout > 0:
            total += payout
            sold.append(str(inventory_id))
        else:
            skipped.append(str(inventory_id))
    BULK_SELL_SELECTIONS[callback.from_user.id] = []
    lines = [
        "<b>Массовая продажа завершена</b>",
        "",
        f"Продано IP: <b>{', '.join(sold) if sold else 'нет'}</b>",
        f"Получено: <b>{total}</b>",
        f"Баланс: <b>{get_balance(callback.from_user.id)}</b>",
    ]
    if skipped:
        lines.append(f"Не продались: <b>{', '.join(skipped)}</b>")
    await callback.message.edit_text(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=build_inventory_menu(get_inventory_for_display(callback.from_user.id)),
    )
    await callback.answer("Продажа завершена")


@dp.callback_query(F.data.startswith("market_buy_"))
async def market_buy_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    market_id = int(callback.data.split("_")[2])
    lot = get_market_item(market_id)
    if not lot:
        await callback.answer("Лот не найден", show_alert=True)
        await show_market_menu(callback.from_user.id, callback.message.message_id)
        return

    seller_id, inventory_id, price, status = lot
    if status != "active":
        await callback.answer("Лот уже недоступен", show_alert=True)
        await show_market_menu(callback.from_user.id, callback.message.message_id)
        return
    if seller_id == callback.from_user.id:
        await callback.answer("Нельзя купить свой лот", show_alert=True)
        return

    balance = get_available_balance(callback.from_user.id)
    if balance < price:
        await callback.answer(f"Недостаточно монет: {balance}/{price}", show_alert=True)
        return

    item = get_inventory_item(inventory_id)
    if not item or item[2]:
        close_market_listing(market_id)
        await callback.answer("Лот стал неактуален", show_alert=True)
        await show_market_menu(callback.from_user.id, callback.message.message_id)
        return

    _, ip_type, _, _, usable_state, _ = item
    buyer_balance = add_balance(callback.from_user.id, -price, f"Покупка лота ID {market_id}")
    seller_balance = add_balance(seller_id, price, f"Продажа лота ID {market_id}")
    add_inventory(callback.from_user.id, ip_type, usable_state=usable_state)
    mark_inventory_sold(inventory_id)
    close_market_listing(market_id)
    update_activity(callback.from_user.id)
    update_activity(seller_id)

    await notify_user(
        seller_id,
        (
            "<b>Ваш IP купили на маркете</b>\n\n"
            f"Лот: <b>ID {market_id}</b>\n"
            f"IP: <b>{escape(ip_type)}</b>\n"
            f"Получено: <b>{price}</b> монет\n"
            f"Баланс: <b>{seller_balance}</b>"
        ),
        build_main_menu(seller_id),
    )
    await callback.answer(f"Покупка успешна. Баланс: {buyer_balance}", show_alert=True)
    await show_market_menu(callback.from_user.id, callback.message.message_id)


@dp.callback_query(F.data.startswith("market_cancel_"))
async def market_cancel_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    market_id = int(callback.data.split("_")[2])
    if cancel_market_listing(market_id, callback.from_user.id):
        update_activity(callback.from_user.id)
        await callback.answer("Лот снят с маркета")
    else:
        await callback.answer("Не удалось снять лот", show_alert=True)
    await show_market_menu(callback.from_user.id, callback.message.message_id)


@dp.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery):
    await callback.answer()


@dp.callback_query(F.data.startswith("hoster_select_"))
async def hoster_select_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    account_id = int(callback.data.split("_")[2])
    if select_hoster_account(callback.from_user.id, account_id):
        await callback.answer("Аккаунт выбран")
    else:
        await callback.answer("Не удалось выбрать аккаунт", show_alert=True)
    await show_hosters_menu(callback.from_user.id, callback.message.message_id)


@dp.callback_query(F.data.startswith("hoster_protect_ask_"))
async def hoster_protect_ask_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    account_id = int(callback.data.split("_")[3])
    account = get_hoster_account(account_id)
    if not account or account[1] != callback.from_user.id:
        await callback.answer("Аккаунт не найден", show_alert=True)
        return
    if is_hoster_account_protected(account_id):
        await callback.answer("Аккаунт уже защищен", show_alert=True)
        return
    cost = get_hoster_protection_cost(account_id)
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=f"Оплатить {cost}", callback_data=f"hoster_protect_confirm_{account_id}"))
    builder.add(InlineKeyboardButton(text="◀️ К аккаунту", callback_data=f"hoster_view_{account_id}"))
    builder.adjust(1)
    await callback.message.edit_text(
        (
            f"<b>{escape(get_hoster_label(account[2]))}</b>\n\n"
            f"ID: <b>{account_id}</b>\n"
            f"Защита РКН стоит <b>{cost}</b> монет.\n"
            "После оплаты случайная конфискация этого аккаунта больше не сработает.\n"
            f"Доступно монет: <b>{get_available_balance(callback.from_user.id)}</b>"
        ),
        parse_mode="HTML",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("hoster_protect_confirm_"))
async def hoster_protect_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    account_id = int(callback.data.split("_")[3])
    account = get_hoster_account(account_id)
    if not account or account[1] != callback.from_user.id:
        await callback.answer("Аккаунт не найден", show_alert=True)
        return
    if is_hoster_account_protected(account_id):
        await callback.answer("Аккаунт уже защищен", show_alert=True)
        return
    cost = get_hoster_protection_cost(account_id)
    if get_available_balance(callback.from_user.id) < cost:
        await callback.answer(f"Не хватает монет: нужно {cost}", show_alert=True)
        return
    balance = add_balance(callback.from_user.id, -cost, f"Защита аккаунта {get_hoster_label(account[2])} в РКН")
    protect_hoster_account(account_id)
    update_activity(callback.from_user.id)
    await callback.answer(f"Защита оплачена. Баланс: {balance}", show_alert=True)
    await show_hoster_item_menu(callback.from_user.id, account_id, callback.message.message_id)


@dp.callback_query(F.data.startswith("hoster_shop_"))
async def hoster_shop_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    provider_key = callback.data.split("_", 2)[2]
    if provider_key not in HOSTER_CONFIGS:
        await callback.answer("Неизвестный хостер", show_alert=True)
        return
    result = attempt_buy_hoster_account(callback.from_user.id, provider_key, haggle=False)
    if not result["ok"]:
        await callback.answer(f"Недостаточно монет. Нужно {result['price']}", show_alert=True)
    else:
        await callback.answer(f"Аккаунт {get_hoster_label(provider_key)} куплен за {result['price']}. Баланс: {get_balance(callback.from_user.id)}", show_alert=True)
    await show_hosters_menu(callback.from_user.id, callback.message.message_id)


@dp.callback_query(F.data.startswith("hoster_haggle_"))
async def hoster_haggle_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    provider_key = callback.data.split("_", 2)[2]
    if provider_key not in HOSTER_CONFIGS:
        await callback.answer("Неизвестный хостер", show_alert=True)
        return
    result = attempt_buy_hoster_account(callback.from_user.id, provider_key, haggle=True)
    if not result["ok"]:
        await callback.answer(f"После торга цена {result['price']}. Монет не хватает.", show_alert=True)
    else:
        suffix = "скидка выбита" if result["outcome"] == "success" else "продавец поднял цену, но вы всё равно купили"
        await callback.answer(f"{suffix}: {result['price']}. Баланс: {get_balance(callback.from_user.id)}", show_alert=True)
    await show_hosters_menu(callback.from_user.id, callback.message.message_id)


@dp.callback_query(F.data.startswith("hoster_sell_"))
async def hoster_sell_start_callback(callback: CallbackQuery, state: FSMContext):
    ensure_user(callback.from_user)
    account_id = int(callback.data.split("_")[2])
    account = get_hoster_account(account_id)
    if not account or account[1] != callback.from_user.id:
        await callback.answer("Аккаунт не найден", show_alert=True)
        return
    active_accounts = [item for item in get_user_hoster_accounts(callback.from_user.id, active_only=True) if item[4] == "active"]
    if account[4] != "active":
        await callback.answer("Аккаунт сейчас на проверке", show_alert=True)
        return
    if has_active_hoster_listing(account_id):
        await callback.answer("Аккаунт уже выставлен на продажу", show_alert=True)
        return
    selected = get_selected_hoster_account(callback.from_user.id)
    if selected and selected[0] == account_id and len(active_accounts) <= 1:
        await callback.answer("Нельзя продать последний активный аккаунт хостера", show_alert=True)
        return
    suggested_price = max(10, round(max(20, HOSTER_CONFIGS[account[2]]["base_cost"]) * 0.9))
    await state.set_state(HosterSellFSM.waiting_price)
    await state.update_data(hoster_account_id=account_id)
    await callback.message.edit_text(
        (
            f"<b>Продажа аккаунта {get_hoster_label(account[2])}</b>\n\n"
            f"Рекомендуемая цена: <b>{suggested_price}</b>\n"
            "Отправьте цену одним числом."
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.message(HosterSellFSM.waiting_price, F.text)
async def hoster_sell_price_input(message: Message, state: FSMContext):
    ensure_user(message.from_user)
    if not message.text.strip().isdigit():
        await message.answer("Нужна целая цена.")
        return
    price = int(message.text.strip())
    if price <= 0:
        await message.answer("Цена должна быть больше нуля.")
        return
    data = await state.get_data()
    account_id = data.get("hoster_account_id")
    account = get_hoster_account(account_id) if account_id else None
    if not account or account[1] != message.from_user.id or account[4] != "active":
        await state.clear()
        await message.answer("Аккаунт недоступен для продажи.")
        return
    if has_active_hoster_listing(account_id):
        await state.clear()
        await message.answer("Аккаунт уже выставлен на продажу.")
        return
    active_accounts = [item for item in get_user_hoster_accounts(message.from_user.id, active_only=True) if item[4] == "active"]
    selected = get_selected_hoster_account(message.from_user.id)
    if selected and selected[0] == account_id and len(active_accounts) <= 1:
        await state.clear()
        await message.answer("Нельзя продать последний активный аккаунт хостера.")
        return
    listing_id = create_hoster_market_listing(message.from_user.id, account_id, price)
    await state.clear()
    await message.answer(
        f"Аккаунт выставлен на маркет лотом <b>ID {listing_id}</b> за <b>{price}</b>.",
        parse_mode="HTML",
        reply_markup=build_main_menu(message.from_user.id),
    )


@dp.callback_query(F.data.startswith("hoster_buy_"))
async def hoster_buy_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    listing_id = int(callback.data.split("_")[2])
    item = get_hoster_market_item(listing_id)
    if not item:
        await callback.answer("Лот не найден", show_alert=True)
        return
    seller_id, account_id, price, status = item
    if status != "active":
        await callback.answer("Лот уже недоступен", show_alert=True)
        return
    if seller_id == callback.from_user.id:
        await callback.answer("Нельзя купить свой аккаунт", show_alert=True)
        return
    if get_available_balance(callback.from_user.id) < price:
        await callback.answer(f"Недостаточно монет: нужно {price}", show_alert=True)
        return
    account = get_hoster_account(account_id)
    if not account or account[1] != seller_id:
        close_hoster_market_listing(listing_id, "cancelled")
        await callback.answer("Аккаунт уже снят с продажи", show_alert=True)
        await show_market_menu(callback.from_user.id, callback.message.message_id)
        return
    buyer_balance = add_balance(callback.from_user.id, -price, f"Покупка аккаунта хостера ID {listing_id}")
    seller_balance = add_balance(seller_id, price, f"Продажа аккаунта хостера ID {listing_id}")
    cursor.execute("UPDATE hoster_accounts SET user_id=? WHERE id=?", (callback.from_user.id, account_id))
    conn.commit()
    close_hoster_market_listing(listing_id)
    if not get_selected_hoster_account(callback.from_user.id):
        select_hoster_account(callback.from_user.id, account_id)
    await notify_user(
        seller_id,
        (
            "<b>Ваш аккаунт хостера купили на маркете</b>\n\n"
            f"Лот: <b>ID {listing_id}</b>\n"
            f"Аккаунт: <b>{escape(get_hoster_label(account[2]))}</b>\n"
            f"Получено: <b>{price}</b> монет\n"
            f"Баланс: <b>{seller_balance}</b>"
        ),
        build_main_menu(seller_id),
    )
    await callback.answer(f"Аккаунт куплен. Баланс: {buyer_balance}", show_alert=True)
    await show_market_menu(callback.from_user.id, callback.message.message_id)


@dp.callback_query(F.data.startswith("hoster_cancel_"))
async def hoster_cancel_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    listing_id = int(callback.data.split("_")[2])
    item = get_hoster_market_item(listing_id)
    if not item:
        await callback.answer("Лот не найден", show_alert=True)
        return
    if item[0] != callback.from_user.id or item[3] != "active":
        await callback.answer("Нельзя снять этот лот", show_alert=True)
        return
    close_hoster_market_listing(listing_id, "cancelled")
    await callback.answer("Лот снят")
    await show_market_menu(callback.from_user.id, callback.message.message_id)


# ========== ОБХОДКИ ==========
@dp.callback_query(F.data == "proxy_add_start")
async def proxy_add_start_callback(callback: CallbackQuery, state: FSMContext):
    ensure_user(callback.from_user)
    proxies = get_user_proxies(callback.from_user.id, active_only=True)
    quota = get_proxy_quota(callback.from_user.id)
    if len(proxies) >= quota:
        await callback.answer(
            f"Лимит серверов достигнут: {len(proxies)}/{quota}",
            show_alert=True,
        )
        return
    purchase_cost = get_server_purchase_cost(callback.from_user.id)
    available_balance = get_available_balance(callback.from_user.id)
    if available_balance < purchase_cost:
        await callback.answer(
            f"Недостаточно монет. Нужно {purchase_cost}, доступно {available_balance}",
            show_alert=True,
        )
        return

    await state.set_state(AddProxyFSM.waiting_name)
    await callback.message.edit_text(
        (
            "<b>Покупка сервера</b>\n\n"
            f"Первоначальный взнос: <b>{purchase_cost}</b>\n"
            "Отправьте имя сервера.\n"
            "Пример: <code>storm-1</code>\n"
            "Операторы вручную больше не выбираются: их определит привязанный IP.\n"
            "Для отмены используйте /cancel."
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@dp.message(AddProxyFSM.waiting_name, F.text)
async def proxy_name_input(message: Message, state: FSMContext):
    ensure_user(message.from_user)
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Имя сервера слишком короткое.")
        return

    await state.clear()
    proxies = get_user_proxies(message.from_user.id, active_only=True)
    quota = get_proxy_quota(message.from_user.id)
    if len(proxies) >= quota:
        await message.answer("Лимит серверов достигнут.")
        return
    proxy_id = add_proxy(message.from_user.id, name, "")
    if not proxy_id:
        await message.answer("Недостаточно доступных монет для покупки сервера.")
        return
    update_activity(message.from_user.id)
    purchase_cost = next(item[5] for item in get_user_proxies(message.from_user.id, active_only=True) if item[0] == proxy_id)
    await message.answer(
        (
            f"✅ <b>Сервер куплен</b>\n\n"
            f"ID: <b>{proxy_id}</b>\n"
            f"Сервер: <b>{escape(name)}</b>\n"
            "Операторы: <b>определятся после привязки IP</b>\n"
            f"Первоначальный взнос: <b>{purchase_cost}</b>\n"
            f"Баланс: <b>{get_balance(message.from_user.id)}</b>\n"
            "Доход появится после привязки белого IP."
        ),
        parse_mode="HTML",
        reply_markup=build_main_menu(message.from_user.id),
    )


@dp.callback_query(F.data.startswith("proxy_bind_"))
async def proxy_bind_start_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    proxy_id = int(callback.data.split("_")[2])
    items = get_bindable_inventory(callback.from_user.id)
    if not items:
        await callback.answer("Нет свободных белых IP для привязки", show_alert=True)
        return
    await callback.message.edit_text(
        "<b>Привязка IP к серверу</b>\n\nВыберите IP из коллекции:",
        parse_mode="HTML",
        reply_markup=build_server_bind_menu(proxy_id, items),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("proxybind_"))
async def proxy_bind_apply_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    _, proxy_id_str, inventory_id_str = callback.data.split("_", 2)
    proxy_id = int(proxy_id_str)
    inventory_id = int(inventory_id_str)
    if is_proxy_committed_to_vpn(proxy_id) or has_active_vpn_server_listing(proxy_id):
        await callback.answer("Сначала уберите сервер из VPN-режима или снимите с VPN-рынка", show_alert=True)
        await show_proxy_item_menu(callback.from_user.id, proxy_id, callback.message.message_id)
        return
    if bind_ip_to_server(proxy_id, callback.from_user.id, inventory_id):
        update_activity(callback.from_user.id)
        await callback.answer("IP привязан к серверу")
    else:
        await callback.answer("Не удалось привязать IP", show_alert=True)
    await show_proxies_menu(callback.from_user.id, callback.message.message_id)


@dp.callback_query(F.data.startswith("proxy_unbind_"))
async def proxy_unbind_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    proxy_id = int(callback.data.split("_")[2])
    if is_proxy_committed_to_vpn(proxy_id) or has_active_vpn_server_listing(proxy_id):
        await callback.answer("Нельзя отвязать IP, пока сервер участвует в VPN", show_alert=True)
        await show_proxy_item_menu(callback.from_user.id, proxy_id, callback.message.message_id)
        return
    if unbind_ip_from_server(proxy_id, callback.from_user.id):
        update_activity(callback.from_user.id)
        await callback.answer("IP отвязан от сервера")
    else:
        await callback.answer("На сервере нет привязанного IP", show_alert=True)
    await show_proxies_menu(callback.from_user.id, callback.message.message_id)


@dp.callback_query(F.data.startswith("proxy_remove_"))
async def proxy_remove_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    proxy_id = int(callback.data.split("_")[2])
    if is_proxy_committed_to_vpn(proxy_id) or has_active_vpn_server_listing(proxy_id):
        await callback.answer("Сначала уберите сервер из VPN или снимите VPN-лот", show_alert=True)
        await show_proxy_item_menu(callback.from_user.id, proxy_id, callback.message.message_id)
        return
    payout = remove_proxy(proxy_id, callback.from_user.id)
    if payout > 0:
        update_activity(callback.from_user.id)
        await callback.answer(f"Сервер продан за {payout}. Баланс: {get_balance(callback.from_user.id)}")
    else:
        await callback.answer("Сервер не найден или на нем висит IP", show_alert=True)
    await show_proxies_menu(callback.from_user.id, callback.message.message_id)


@dp.callback_query(F.data.startswith("proxy_protect_ask_"))
async def proxy_protect_ask_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    proxy_id = int(callback.data.split("_")[3])
    proxy = next((item for item in get_user_proxies(callback.from_user.id, active_only=True) if item[0] == proxy_id), None)
    if not proxy:
        await callback.answer("Сервер не найден", show_alert=True)
        return
    if is_proxy_protected(proxy_id):
        await callback.answer("Сервер уже защищен", show_alert=True)
        return
    cost = get_proxy_protection_cost(proxy_id)
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=f"Оплатить {cost}", callback_data=f"proxy_protect_confirm_{proxy_id}"))
    builder.add(InlineKeyboardButton(text="◀️ К серверу", callback_data=f"proxy_view_{proxy_id}"))
    builder.adjust(1)
    await callback.message.edit_text(
        (
            f"<b>Защита сервера</b>\n\n"
            f"Сервер: <b>{escape(proxy[1])}</b>\n"
            f"ID: <b>{proxy_id}</b>\n"
            f"Цена защиты: <b>{cost}</b>\n"
            "После оплаты сервер нельзя будет конфисковать случайным событием."
        ),
        parse_mode="HTML",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("proxy_protect_confirm_"))
async def proxy_protect_confirm_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    proxy_id = int(callback.data.split("_")[3])
    proxy = next((item for item in get_user_proxies(callback.from_user.id, active_only=True) if item[0] == proxy_id), None)
    if not proxy:
        await callback.answer("Сервер не найден", show_alert=True)
        return
    if is_proxy_protected(proxy_id):
        await callback.answer("Сервер уже защищен", show_alert=True)
        return
    cost = get_proxy_protection_cost(proxy_id)
    if get_available_balance(callback.from_user.id) < cost:
        await callback.answer(f"Не хватает монет: нужно {cost}", show_alert=True)
        return
    balance = add_balance(callback.from_user.id, -cost, f"Защита сервера ID {proxy_id} в РКН")
    protect_proxy(proxy_id)
    await callback.answer(f"Защита оплачена. Баланс: {balance}", show_alert=True)
    await show_proxy_item_menu(callback.from_user.id, proxy_id, callback.message.message_id)


@dp.callback_query(F.data == "proxy_upgrade_ask")
async def proxy_upgrade_ask_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    cost = get_proxy_quota_upgrade_cost(callback.from_user.id)
    quota = get_proxy_quota(callback.from_user.id)
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=f"Оплатить {cost}", callback_data="proxy_upgrade_confirm"))
    builder.add(InlineKeyboardButton(text="◀️ К серверам", callback_data="menu_proxies"))
    builder.adjust(1)
    await callback.message.edit_text(
        (
            "<b>Покупка слота сервера</b>\n\n"
            f"Текущая квота: <b>{quota}</b>\n"
            f"После покупки: <b>{quota + 1}</b>\n"
            f"Цена: <b>{cost}</b>\n"
            f"Доступно: <b>{get_available_balance(callback.from_user.id)}</b>"
        ),
        parse_mode="HTML",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@dp.callback_query(F.data == "proxy_upgrade_confirm")
async def proxy_upgrade_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    if not upgrade_proxy_quota(callback.from_user.id):
        await callback.answer(
            f"Недостаточно монет. Нужно {get_proxy_quota_upgrade_cost(callback.from_user.id)}",
            show_alert=True,
        )
        return

    await callback.answer(f"Квота повышена. Баланс: {get_balance(callback.from_user.id)}", show_alert=True)
    await show_proxies_menu(callback.from_user.id, callback.message.message_id)


@dp.callback_query(F.data == "vpn_create_start")
async def vpn_create_start_callback(callback: CallbackQuery, state: FSMContext):
    ensure_user(callback.from_user)
    if get_vpn_service(callback.from_user.id):
        await callback.answer("VPN-сервис уже запущен", show_alert=True)
        await show_vpn_menu(callback.from_user.id, callback.message.message_id)
        return
    if get_available_balance(callback.from_user.id) < VPN_SERVICE_CREATE_COST:
        await callback.answer(f"Нужно {VPN_SERVICE_CREATE_COST} монет", show_alert=True)
        return
    await state.set_state(VPNSetupFSM.waiting_name)
    await callback.message.edit_text(
        (
            "<b>Запуск VPN-сервиса</b>\n\n"
            f"Стартовая стоимость: <b>{VPN_SERVICE_CREATE_COST}</b>\n"
            "Отправьте название сервиса.\n"
            "Дальше вы сможете управлять ценой и рекламой."
        ),
        parse_mode="HTML",
        reply_markup=build_back_button("menu_vpn"),
    )
    await callback.answer()


@dp.message(VPNSetupFSM.waiting_name, F.text)
async def vpn_create_name_input(message: Message, state: FSMContext):
    ensure_user(message.from_user)
    service_name = message.text.strip()
    if len(service_name) < 2:
        await message.answer("Название слишком короткое.")
        return
    await state.clear()
    if not create_vpn_service(message.from_user.id, service_name):
        await message.answer("Не удалось запустить сервис. Возможно, он уже создан или не хватает монет.")
        return
    await message.answer(
        (
            f"✅ <b>VPN-сервис запущен</b>\n\n"
            f"Название: <b>{escape(service_name)}</b>\n"
            f"Списано: <b>{VPN_SERVICE_CREATE_COST}</b>\n"
            f"Баланс: <b>{get_balance(message.from_user.id)}</b>"
        ),
        parse_mode="HTML",
        reply_markup=build_main_menu(message.from_user.id),
    )


@dp.callback_query(F.data == "vpn_noop")
async def vpn_noop_callback(callback: CallbackQuery):
    await callback.answer()


@dp.callback_query(F.data.startswith("microloan_offer_"))
async def microloan_offer_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    amount = int(callback.data.split("_")[2])
    if get_active_microloan(callback.from_user.id):
        await callback.answer("У вас уже есть активный микрозайм", show_alert=True)
        await show_balance_menu(callback.from_user.id, callback.message.message_id)
        return
    offer = get_microloan_offer(amount)
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=f"Взять {offer['amount']}", callback_data=f"microloan_take_{offer['amount']}"))
    builder.add(InlineKeyboardButton(text="◀️ К балансу", callback_data="menu_balance"))
    builder.adjust(1)
    await callback.message.edit_text(
        (
            "<b>Микрозайм</b>\n\n"
            f"Сумма: <b>{offer['amount']}</b>\n"
            f"Вернуть: <b>{offer['total_due']}</b>\n"
            f"Срок: <b>{MICROLOAN_TERM_HOURS}</b> ч, до <b>{offer['due_at'].strftime('%H:%M')}</b>\n"
            "Условия жесткие: при просрочке будет только одно предупреждение.\n"
            "Если после него не погасить долг вовремя, конфискуется вообще всё."
        ),
        parse_mode="HTML",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("microloan_take_"))
async def microloan_take_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    amount = int(callback.data.split("_")[2])
    offer = issue_microloan(callback.from_user.id, amount)
    if not offer:
        await callback.answer("Не удалось выдать микрозайм", show_alert=True)
        await show_balance_menu(callback.from_user.id, callback.message.message_id)
        return
    await callback.answer(f"Микрозайм выдан. Баланс: {get_balance(callback.from_user.id)}")
    await show_balance_menu(callback.from_user.id, callback.message.message_id)


@dp.callback_query(F.data == "microloan_repay")
async def microloan_repay_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    result = repay_microloan(callback.from_user.id)
    if result is None:
        await callback.answer("Активного займа нет", show_alert=True)
    elif result == -1:
        await callback.answer("Недостаточно доступных монет для погашения", show_alert=True)
    else:
        await callback.answer(f"Займ погашен. Баланс: {result}")
    await show_balance_menu(callback.from_user.id, callback.message.message_id)


@dp.callback_query(F.data == "vpn_market_open")
async def vpn_market_open_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    await show_vpn_market_menu(callback.from_user.id, callback.message.message_id)
    await callback.answer()


@dp.callback_query(F.data == "vpn_delete_ask")
async def vpn_delete_ask_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    service = get_vpn_service(callback.from_user.id)
    if not service:
        await callback.answer("VPN уже удален", show_alert=True)
        await show_vpn_menu(callback.from_user.id, callback.message.message_id)
        return
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Удалить VPN", callback_data="vpn_delete_confirm"))
    builder.add(InlineKeyboardButton(text="◀️ К VPN", callback_data="menu_vpn"))
    builder.adjust(1)
    await callback.message.edit_text(
        (
            "<b>Удаление VPN</b>\n\n"
            "Будет удален сам VPN-сервис и все его внутренние привязки серверов.\n"
            "Ваши серверы останутся у вас, но перестанут работать на этот VPN.\n"
            "Сданные другим пользователям серверы не трогаются."
        ),
        parse_mode="HTML",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@dp.callback_query(F.data == "vpn_delete_confirm")
async def vpn_delete_confirm_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    deleted = delete_vpn_service(callback.from_user.id)
    await callback.answer("VPN удален" if deleted else "VPN не найден", show_alert=not deleted)
    await show_main_panel(callback.from_user.id, callback.message.message_id)


@dp.callback_query(F.data == "vpn_level_up")
async def vpn_level_up_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    service = get_vpn_service(callback.from_user.id)
    if not service:
        await callback.answer("VPN-сервис не найден", show_alert=True)
        return
    current_level = get_vpn_level(service)
    cost = get_vpn_level_upgrade_cost(current_level)
    needed_capacity = current_level * 3
    if get_vpn_capacity(callback.from_user.id) < needed_capacity:
        await callback.answer(f"Нужна емкость VPN не ниже {needed_capacity}", show_alert=True)
        return
    if not upgrade_vpn_level(callback.from_user.id):
        await callback.answer(f"Не хватает монет: нужно {cost}", show_alert=True)
        return
    await callback.answer(f"Уровень VPN повышен. Баланс: {get_balance(callback.from_user.id)}")
    await show_vpn_menu(callback.from_user.id, callback.message.message_id)


@dp.callback_query(F.data.in_(("vpn_price_down", "vpn_price_up", "vpn_marketing_down", "vpn_marketing_up", "vpn_toggle")))
async def vpn_control_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    settle_vpn_service(callback.from_user.id)
    service = get_vpn_service(callback.from_user.id)
    if not service:
        await callback.answer("Сервис не найден", show_alert=True)
        await show_vpn_menu(callback.from_user.id, callback.message.message_id)
        return
    action = callback.data
    if action == "vpn_price_down":
        update_vpn_service_settings(callback.from_user.id, price=service[2] - 1)
    elif action == "vpn_price_up":
        update_vpn_service_settings(callback.from_user.id, price=service[2] + 1)
    elif action == "vpn_marketing_down":
        update_vpn_service_settings(callback.from_user.id, marketing=service[3] - 5)
    elif action == "vpn_marketing_up":
        update_vpn_service_settings(callback.from_user.id, marketing=service[3] + 5)
    elif action == "vpn_toggle":
        update_vpn_service_settings(callback.from_user.id, is_active=not bool(service[5]))
    await show_vpn_menu(callback.from_user.id, callback.message.message_id)
    await callback.answer()


@dp.callback_query(F.data.startswith("vpnproxy_"))
async def vpn_proxy_control_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    payload = callback.data.removeprefix("vpnproxy_")
    action, proxy_id_str = payload.rsplit("_", 1)
    proxy_id = int(proxy_id_str)
    if action in {"service", "retail", "virtual"}:
        ok = assign_proxy_to_vpn(callback.from_user.id, proxy_id, "service")
        await callback.answer("Сервер подключен к вашему VPN" if ok else "Не удалось подключить сервер к VPN", show_alert=not ok)
    elif action == "remove":
        ok = remove_proxy_from_vpn(callback.from_user.id, proxy_id)
        await callback.answer("Сервер убран из VPN" if ok else "Сервер не был привязан к вашему VPN", show_alert=not ok)
    elif action == "unlist":
        listing = get_active_vpn_server_listing(proxy_id)
        ok = bool(listing and listing[1] == callback.from_user.id)
        if ok:
            close_vpn_server_market_listing(listing[0], "cancelled")
            await callback.answer("Сервер снят с VPN-рынка")
        else:
            await callback.answer("Этот сервер уже не стоит на VPN-рынке", show_alert=True)
    elif action == "list":
        proxy = next((item for item in get_user_proxies(callback.from_user.id, active_only=True) if item[0] == proxy_id), None)
        ok = bool(proxy and proxy[6] and not get_vpn_server_link(proxy_id) and not has_active_vpn_server_listing(proxy_id))
        if ok:
            price = get_vpn_server_suggested_rent(proxy_id)
            create_vpn_server_market_listing(callback.from_user.id, proxy_id, price)
            await callback.answer(f"Сервер выставлен на VPN-рынок за {price}/ч")
        else:
            await callback.answer("Нельзя выставить этот сервер на VPN-рынок", show_alert=True)
    else:
        await callback.answer()
        return
    await show_proxy_item_menu(callback.from_user.id, proxy_id, callback.message.message_id)


@dp.callback_query(F.data.startswith("vpnlease_release_"))
async def vpn_lease_release_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    proxy_id = int(callback.data.split("_")[2])
    released = release_leased_server(callback.from_user.id, proxy_id)
    await callback.answer("Аренда сервера завершена" if released else "Эта аренда уже не активна", show_alert=not released)
    await show_vpn_menu(callback.from_user.id, callback.message.message_id)


@dp.callback_query(F.data.startswith("vpnmarket_view_"))
async def vpn_market_view_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    listing_id = int(callback.data.split("_")[2])
    await show_vpn_market_item_menu(callback.from_user.id, listing_id, callback.message.message_id)
    await callback.answer()


@dp.callback_query(F.data.startswith("vpnmarket_buy_"))
async def vpn_market_buy_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    listing_id = int(callback.data.split("_")[2])
    result = lease_server_to_vpn(callback.from_user.id, listing_id)
    if not result:
        await callback.answer("Не удалось арендовать сервер", show_alert=True)
        await show_vpn_market_menu(callback.from_user.id, callback.message.message_id)
        return
    await notify_user(
        result["seller_id"],
        f"<b>Ваш сервер ID {result['proxy_id']} арендовали для VPN</b>\n\nДоход по аренде: <b>{result['price']}/ч</b>.",
        build_main_menu(result["seller_id"]),
    )
    await callback.answer(f"Сервер арендован за {result['price']}/ч")
    await show_vpn_menu(callback.from_user.id, callback.message.message_id)


@dp.callback_query(F.data.startswith("vpnmarket_cancel_"))
async def vpn_market_cancel_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    listing_id = int(callback.data.split("_")[2])
    item = get_vpn_server_market_item(listing_id)
    if not item or item[1] != callback.from_user.id or item[4] != "active":
        await callback.answer("Нельзя снять этот VPN-лот", show_alert=True)
        return
    close_vpn_server_market_listing(listing_id, "cancelled")
    await callback.answer("VPN-лот снят")
    await show_vpn_market_menu(callback.from_user.id, callback.message.message_id)


@dp.callback_query(F.data.startswith("roulette_pick_"))
async def roulette_pick_callback(callback: CallbackQuery):
    ensure_user(callback.from_user)
    game = ROULETTE_GAMES.get(callback.from_user.id)
    if not game or game["expires_at"] <= datetime.now():
        ROULETTE_GAMES.pop(callback.from_user.id, None)
        await callback.answer("Игра уже исчезла", show_alert=True)
        await show_main_panel(callback.from_user.id, callback.message.message_id)
        return
    chosen = int(callback.data.split("_")[2])
    loaded = int(game["loaded"])
    ROULETTE_GAMES.pop(callback.from_user.id, None)
    if chosen == loaded:
        account = get_random_unprotected_hoster_account(callback.from_user.id)
        if account:
            confiscate_hoster_account(account[0])
            text = (
                "<b>Русская рулетка проиграна</b>\n\n"
                f"Вы выбрали камеру <b>{chosen}</b>, и она оказалась заряженной.\n"
                f"Конфискован аккаунт: <b>{escape(get_hoster_label(account[2]))}</b>."
            )
        else:
            text = (
                "<b>Русская рулетка проиграна</b>\n\n"
                f"Вы выбрали камеру <b>{chosen}</b>, она оказалась заряженной.\n"
                "Но у вас не нашлось незащищенных аккаунтов для конфискации."
            )
    else:
        apply_luck_buff(callback.from_user.id)
        text = (
            "<b>Русская рулетка выиграна</b>\n\n"
            f"Вы выбрали камеру <b>{chosen}</b>, а заряжена была <b>{loaded}</b>.\n"
            "Шансы на хорошие IP усилены на 5 минут."
        )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=build_main_menu(callback.from_user.id))
    await callback.answer()


# ========== ЗАПУСК ==========
async def main():
    load_active_votes()
    asyncio.create_task(auto_end_expired_votes())
    asyncio.create_task(auto_daily_bonus())
    asyncio.create_task(auto_income())
    asyncio.create_task(auto_random_events())
    asyncio.create_task(auto_microloans())
    asyncio.create_task(auto_reset_limits())
    print("Бот запущен. Все системы активны.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
