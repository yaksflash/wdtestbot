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
