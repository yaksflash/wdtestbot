

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
