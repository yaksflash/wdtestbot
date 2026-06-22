
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
