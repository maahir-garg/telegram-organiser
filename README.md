# telegram-organiser

Create Telegram chat folders in bulk from a JSON file, instead of adding chats one at a time in the app.

It exports your chat list, you decide which chats go in which folder, and it creates the folders. It never reads or exports messages.

## Status

A small personal tool in a single script, `tg.py`, with no tests. It talks to Telegram as your own user account through the [Telethon](https://github.com/LonamiWebs/Telethon) library (pinned to 1.45.0 in `requirements.txt`), not through a bot token.

## Setup

You need Python 3 (the README was written against 3.9 or newer; the version is not enforced in the code) and your own Telegram API ID and hash:

1. Sign in at [my.telegram.org](https://my.telegram.org).
2. Open **API development tools** and create an app.

Then install:

```bash
git clone https://github.com/maahir-garg/telegram-organiser.git
cd telegram-organiser
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Usage

**1. Log in.** You'll be asked for your API ID, API hash, phone number, login code and two-step verification password, if you have one. Input is hidden as you type.

```bash
.venv/bin/python tg.py login
```

**2. Export your chats** to `chats.json`, which lists each chat's ID, name, type, member count, last activity and current folders.

```bash
.venv/bin/python tg.py export
```

**3. Write `folders.json`** using IDs from `chats.json`. A chat can be in more than one folder. `emoticon` is an optional single emoji shown on the folder; `folders.example.json` has a sample.

```json
{
  "folders": [
    {
      "title": "Uni",
      "chat_ids": [-1001234567890, -1009876543210]
    }
  ]
}
```

**4. Preview the result.** This checks your file against Telegram's limits and changes nothing.

```bash
.venv/bin/python tg.py apply
```

**5. Create the folders.**

```bash
.venv/bin/python tg.py apply --confirm
```

**6. Log out** when you're finished. This ends the session with Telegram and deletes the local login files.

```bash
.venv/bin/python tg.py logout
```

## How it works

`tg.py` is one script with four subcommands. `login` runs Telethon's interactive sign-in and saves the API ID and hash to `.tg_credentials.json` and the session to `tg_session.session`. `export` lists your dialogs and existing folders (it requests `GetDialogFiltersRequest` and iterates dialogs, and reads no message text). `apply` loads `folders.json`, checks it, and sends one `UpdateDialogFilterRequest` per folder, using the first free folder IDs from 2 upward and pausing one second between requests.

## Limits

| | Free | Premium |
| --- | --- | --- |
| Folders, including existing ones | 10 | 20 |
| Chats per folder | 100 | 200 |

Folder names can be up to 12 characters. These limits are the constants in `tg.py`; Telegram may change them, and `apply` does not read them from Telegram. The Premium column is used when the logged-in account is Premium.

## Behaviour

- Existing folders are never changed. If a new folder has the same name as an existing one, `apply` stops before changing anything.
- Folders contain the chats you list. Rule-based folders, such as "all groups", aren't supported.
- `apply` needs every chat ID in `folders.json` to appear in your current chat list, and it refuses a folder with no chats.
- To undo, delete the folder in Telegram. Its chats stay in your chat list.

## Security

`.tg_credentials.json` and `tg_session.session` give **full access to your Telegram account**. They're readable only by your user and excluded by `.gitignore`, but don't share them. Run `logout` when you're finished. You can also end the session from Telegram under **Settings > Devices**.

`chats.json` and `folders.json` contain personal data and are also excluded by `.gitignore`.

Telegram may restrict accounts it suspects of misusing its API. This tool only makes a small number of requests, but use it at your own risk. See Telegram's [API Terms of Service](https://core.telegram.org/api/terms).

This project isn't affiliated with Telegram.

## License

[MIT](LICENSE)
