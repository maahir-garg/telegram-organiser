#!/usr/bin/env python3
"""Sort Telegram chats into folders.

  tg.py login              Log in; all prompts are hidden and stay on this Mac
  tg.py export             Write chat names and types to chats.json (never messages)
  tg.py apply              Preview the folders described in folders.json
  tg.py apply --confirm    Create those folders
  tg.py logout             End this login with Telegram and delete local login files
"""
import argparse
import asyncio
import getpass
import json
import os
import sys
from pathlib import Path

from telethon import TelegramClient, errors, utils
from telethon.tl.functions.messages import (
    GetDialogFiltersRequest,
    UpdateDialogFilterRequest,
)
from telethon.tl.types import Channel, Chat, DialogFilter, TextWithEntities, User

HERE = Path(__file__).resolve().parent
CREDS = HERE / ".tg_credentials.json"
SESSION = HERE / "tg_session"
SESSION_FILE = HERE / "tg_session.session"
CHATS = HERE / "chats.json"
FOLDERS = HERE / "folders.json"

# Telegram's folder limits: (free, Premium)
MAX_FOLDERS = (10, 20)
MAX_CHATS_PER_FOLDER = (100, 200)
MAX_TITLE_LENGTH = 12
# Telegram reserves id 0 (All Chats) and 1 (Archive).
FIRST_FOLDER_ID, LAST_FOLDER_ID = 2, 255


def make_client(creds):
    return TelegramClient(str(SESSION), creds["api_id"], creds["api_hash"])


def load_creds():
    if not CREDS.exists():
        sys.exit("Not logged in. Run: tg.py login")
    return json.loads(CREDS.read_text())


async def connect():
    client = make_client(load_creds())
    await client.connect()
    if not await client.is_user_authorized():
        await client.disconnect()
        sys.exit("Login has expired. Run: tg.py login")
    return client


def chat_type(entity):
    if isinstance(entity, User):
        if entity.is_self:
            return "saved_messages"
        return "bot" if entity.bot else "person"
    if isinstance(entity, Chat):
        return "group"
    if isinstance(entity, Channel):
        return "channel" if entity.broadcast else "group"
    return "unknown"


async def get_custom_folders(client):
    result = await client(GetDialogFiltersRequest())
    filters = getattr(result, "filters", result)
    return [f for f in filters if hasattr(f, "title") and hasattr(f, "id")]


def title_text(folder):
    return getattr(folder.title, "text", folder.title)


async def cmd_login():
    print("Your input is hidden as you type or paste. Press Enter after each one.\n")
    api_id = int(getpass.getpass("API ID (numbers only): ").strip())
    api_hash = getpass.getpass("API hash: ").strip()
    creds = {"api_id": api_id, "api_hash": api_hash}

    client = make_client(creds)
    await client.start(
        phone=lambda: getpass.getpass("Phone number, with country code: ").strip(),
        code_callback=lambda: getpass.getpass("Login code Telegram just sent you: ").strip(),
        password=lambda: getpass.getpass("Two-step verification password: "),
    )
    await client.disconnect()

    CREDS.write_text(json.dumps(creds))
    print("\nLogged in.")


async def cmd_export():
    client = await connect()
    try:
        folders = await get_custom_folders(client)
        membership = {}
        for folder in folders:
            for peer in folder.include_peers:
                membership.setdefault(utils.get_peer_id(peer), []).append(title_text(folder))

        chats = []
        async for dialog in client.iter_dialogs():
            entity = dialog.entity
            chats.append(
                {
                    "id": dialog.id,
                    "name": dialog.name or "(no name)",
                    "type": chat_type(entity),
                    "members": getattr(entity, "participants_count", None),
                    "is_contact": getattr(entity, "contact", None),
                    "archived": dialog.archived,
                    "last_active": dialog.date.date().isoformat() if dialog.date else None,
                    "current_folders": membership.get(dialog.id, []),
                }
            )
        me = await client.get_me()
    finally:
        await client.disconnect()

    CHATS.write_text(
        json.dumps(
            {
                "premium": bool(me.premium),
                "existing_folders": [
                    {
                        "title": title_text(f),
                        "chat_count": len(f.include_peers),
                        # Rule-based folders, e.g. "all groups", hold more than their listed chats.
                        "uses_rules": any(
                            getattr(f, flag, False)
                            for flag in ("contacts", "non_contacts", "groups", "broadcasts", "bots")
                        ),
                    }
                    for f in folders
                ],
                "chats": chats,
            },
            ensure_ascii=False,
            indent=1,
        )
    )
    print(f"Exported {len(chats)} chats and {len(folders)} existing folders to {CHATS.name}")


async def cmd_apply(confirm):
    plan = json.loads(FOLDERS.read_text())["folders"]
    client = await connect()
    try:
        me = await client.get_me()
        tier = 1 if me.premium else 0
        existing = await get_custom_folders(client)
        existing_titles = {title_text(f).casefold() for f in existing}
        used_ids = {f.id for f in existing}
        free_ids = [i for i in range(FIRST_FOLDER_ID, LAST_FOLDER_ID + 1) if i not in used_ids]
        peers = {d.id: d.input_entity async for d in client.iter_dialogs()}

        problems = []
        for spec in plan:
            title = spec["title"]
            ids = spec["chat_ids"]
            if title.casefold() in existing_titles:
                problems.append(f'"{title}": a folder with this name already exists')
            if len(title) > MAX_TITLE_LENGTH:
                problems.append(f'"{title}": name is over {MAX_TITLE_LENGTH} characters')
            if not ids:
                problems.append(f'"{title}": has no chats')
            if len(ids) > MAX_CHATS_PER_FOLDER[tier]:
                problems.append(
                    f'"{title}": {len(ids)} chats is over the limit of {MAX_CHATS_PER_FOLDER[tier]}'
                )
            missing = [i for i in ids if i not in peers]
            if missing:
                problems.append(f'"{title}": chat ids not found: {missing}')

        if len(existing) + len(plan) > MAX_FOLDERS[tier]:
            problems.append(
                f"{len(existing)} existing + {len(plan)} new folders "
                f"is over the limit of {MAX_FOLDERS[tier]}"
            )

        for spec in plan:
            print(f'{spec["title"]}: {len(spec["chat_ids"])} chats')
        if problems:
            print("\nNothing was changed. Fix these first:")
            for problem in problems:
                print(f"  - {problem}")
            sys.exit(1)
        if not confirm:
            print("\nPreview only. Nothing was changed.")
            return

        for folder_id, spec in zip(free_ids, plan):
            await client(
                UpdateDialogFilterRequest(
                    id=folder_id,
                    filter=DialogFilter(
                        id=folder_id,
                        title=TextWithEntities(text=spec["title"], entities=[]),
                        emoticon=spec.get("emoticon"),
                        pinned_peers=[],
                        include_peers=[peers[i] for i in spec["chat_ids"]],
                        exclude_peers=[],
                    ),
                )
            )
            print(f'Created "{spec["title"]}"')
            await asyncio.sleep(1)
    except errors.RPCError as error:
        sys.exit(f"Telegram refused the request: {error}")
    finally:
        await client.disconnect()


async def cmd_logout():
    if CREDS.exists() and SESSION_FILE.exists():
        client = make_client(load_creds())
        await client.connect()
        if await client.is_user_authorized():
            await client.log_out()
        await client.disconnect()
    for path in (CREDS, SESSION_FILE, HERE / "tg_session.session-journal"):
        path.unlink(missing_ok=True)
    print("Logged out and deleted the local login files.")


def main():
    os.umask(0o077)  # The login files give full account access: owner-only.
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("command", choices=["login", "export", "apply", "logout"])
    parser.add_argument("--confirm", action="store_true", help="with apply: actually create the folders")
    args = parser.parse_args()
    if args.command == "login":
        asyncio.run(cmd_login())
    elif args.command == "export":
        asyncio.run(cmd_export())
    elif args.command == "apply":
        asyncio.run(cmd_apply(args.confirm))
    else:
        asyncio.run(cmd_logout())


if __name__ == "__main__":
    main()
