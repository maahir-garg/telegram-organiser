# telegram-organiser

Create Telegram chat folders in bulk from a JSON file, instead of adding chats one at a time in the app.

It exports your chat list, you decide which chats go in which folder, and it creates the folders. It never reads or exports messages.

## Setup

You need Python 3.9 or newer and your own Telegram API ID and hash:

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

**3. Write `folders.json`** using IDs from `chats.json`. A chat can be in more than one folder. `emoticon` is optional.

```json
{
  "folders": [
    {
      "title": "Uni",
      "emoticon": "🎓",
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

## Limits

| | Free | Premium |
| --- | --- | --- |
| Folders, including existing ones | 10 | 20 |
| Chats per folder | 100 | 200 |

Folder names can be up to 12 characters.

## Behaviour

- Existing folders are never changed. If a new folder has the same name as an existing one, `apply` stops before changing anything.
- Folders contain the chats you list. Rule-based folders, such as "all groups", aren't supported.
- To undo, delete the folder in Telegram. Its chats stay in your chat list.

## Security

`.tg_credentials.json` and `tg_session.session` give **full access to your Telegram account**. They're readable only by your user and excluded by `.gitignore`, but don't share them. Run `logout` when you're finished. You can also end the session from Telegram under **Settings > Devices**.

`chats.json` and `folders.json` contain personal data and are also excluded by `.gitignore`.

Telegram may restrict accounts it suspects of misusing its API. This tool only makes a small number of requests, but use it at your own risk. See Telegram's [API Terms of Service](https://core.telegram.org/api/terms).

This project isn't affiliated with Telegram.

## License

[MIT](LICENSE)
