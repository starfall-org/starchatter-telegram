"""Pagination helper functions for AI provider handlers."""

from pyrogram import types

# Paging constants
ITEMS_PER_PAGE = 80  # 10 rows × 8 buttons
COLUMNS = 8  # 8 buttons per row

# Backward compatibility aliases
PROVIDERS_PER_PAGE = ITEMS_PER_PAGE
MODELS_PER_PAGE = ITEMS_PER_PAGE


def create_pagination_buttons(
    page: int, total_pages: int, callback_prefix: str
) -> list:
    """Create pagination buttons"""
    buttons = []
    row = []

    if page > 0:
        row.append(
            types.InlineKeyboardButton(
                text="◀ Prev", callback_data=f"{callback_prefix}/page/{page - 1}"
            )
        )

    row.append(
        types.InlineKeyboardButton(
            text=f"{page + 1}/{total_pages}",
            callback_data="noop",  # Current page indicator, not clickable
        )
    )

    if page < total_pages - 1:
        row.append(
            types.InlineKeyboardButton(
                text="Next ▶", callback_data=f"{callback_prefix}/page/{page + 1}"
            )
    )

    # Add back button at the end of pagination row (or close if single page)
    if total_pages == 1:
        row.append(
            types.InlineKeyboardButton(
                text="❌ Close",
                callback_data=f"{callback_prefix}/close",
            )
        )
    else:
        row.append(
            types.InlineKeyboardButton(
                text="⬅️ Back",
                callback_data=f"{callback_prefix}/back",
            )
        )

    if row:
        buttons.append(row)

    return buttons


def create_numbered_keyboard(
    items: list[str],
    page: int,
    callback_prefix: str,
    total_pages: int,
    extra_buttons: list[list[types.InlineKeyboardButton]] | None = None,
) -> types.InlineKeyboardMarkup:
    """Create keyboard displaying list with number buttons and pagination.

    - Each row has 8 number buttons
    - 10 rows for numbers (80 items)
    - Last row for pagination
    """
    buttons: list[list[types.InlineKeyboardButton]] = []
    
    # Calculate starting number for this page
    start_num = page * ITEMS_PER_PAGE + 1
    
    # Number buttons - 8 per row, 10 rows
    for i, item in enumerate(items):
        num = start_num + i
        col = i % COLUMNS
        
        # Start new row every 8 items
        if col == 0:
            buttons.append([])
        
        buttons[-1].append(
            types.InlineKeyboardButton(
                text=str(num),
                callback_data=f"{callback_prefix}/{num}",
            )
        )
    
    # Fill empty slots in last row if needed
    if buttons and len(buttons[-1]) < COLUMNS:
        missing = COLUMNS - len(buttons[-1])
        for _ in range(missing):
            buttons[-1].append(
                types.InlineKeyboardButton(
                    text=" ",
                    callback_data="noop",
                )
            )
    
    # Pagination buttons (last row)
    pagination_buttons = create_pagination_buttons(
        page, total_pages, callback_prefix
    )
    if pagination_buttons:
        buttons.extend(pagination_buttons)
    
    # Extra buttons (like Back button for providers list)
    if extra_buttons:
        buttons.extend(extra_buttons)
    
    return types.InlineKeyboardMarkup(buttons)


def create_models_keyboard(
    models: list[str],
    page: int,
    callback_prefix: str,
    total_pages: int,
    selected_model: str | None = None,
    extra_buttons: list[list[types.InlineKeyboardButton]] | None = None,
) -> types.InlineKeyboardMarkup:
    """Create keyboard displaying list of models with number buttons and pagination.

    - Each row has 8 number buttons
    - 10 rows for numbers (80 items)
    - Last row for pagination
    """
    return create_numbered_keyboard(
        items=models,
        page=page,
        callback_prefix=callback_prefix,
        total_pages=total_pages,
        extra_buttons=extra_buttons,
    )


def create_providers_keyboard(
    providers: list[tuple[int, str]],
    page: int,
    callback_prefix: str,
    total_pages: int,
    extra_buttons: list[list[types.InlineKeyboardButton]] | None = None,
) -> types.InlineKeyboardMarkup:
    """Create keyboard displaying list of providers with number buttons and pagination.

    - Each row has 8 number buttons
    - 10 rows for numbers (80 items)
    - Last row for pagination

    Args:
        providers: List of tuples (provider_id, provider_name)
    """
    # Create items list with provider names for display
    items = [name for _, name in providers]

    return create_numbered_keyboard(
        items=items,
        page=page,
        callback_prefix=callback_prefix,
        total_pages=total_pages,
        extra_buttons=extra_buttons,
    )


def create_provider_actions_keyboard(
    providers: list[tuple[int, str]],
    callback_prefix: str = "provider",
) -> types.InlineKeyboardMarkup:
    """Create keyboard displaying list of providers with action buttons.

    Each provider has buttons: select, edit, models, delete
    End of list has back and close buttons.

    Args:
        providers: List of tuples (provider_id, provider_name)
        callback_prefix: Prefix for callback data
    """
    buttons: list[list[types.InlineKeyboardButton]] = []

    for provider_id, provider_name in providers:
        # Provider name as header (disabled button)
        buttons.append([
            types.InlineKeyboardButton(
                text=f"🔹 {provider_name}",
                callback_data="noop",
            )
        ])

        # Action buttons for this provider
        buttons.append([
            types.InlineKeyboardButton(
                text="✅ Select",
                callback_data=f"{callback_prefix}/select/{provider_id}",
            ),
            types.InlineKeyboardButton(
                text="✏️ Edit",
                callback_data=f"{callback_prefix}/edit/{provider_id}",
            ),
        ])
        buttons.append([
            types.InlineKeyboardButton(
                text="🤖 Models",
                callback_data=f"{callback_prefix}/models/{provider_id}",
            ),
            types.InlineKeyboardButton(
                text="🗑️ Delete",
                callback_data=f"{callback_prefix}/delete/{provider_id}",
            ),
        ])

    # Bottom navigation buttons
    buttons.append([
        types.InlineKeyboardButton(
            text="⬅️ Back",
            callback_data=f"{callback_prefix}/back",
        ),
        types.InlineKeyboardButton(
            text="❌ Close",
            callback_data=f"{callback_prefix}/close",
        ),
    ])

    return types.InlineKeyboardMarkup(buttons)
