# Personal playlists: /createplaylist, /myplaylists, /playlistinfo,
# /addtoplaylist, /removefromplaylist, /editplaylist, /deleteplaylist
# and `/play playlist-<ID>` (hooked in plugins/play.py).

import html
import re
import secrets

from pyrogram import filters, types

from AloneX.music import app, config, db, logger, yt
from AloneX.music.helpers import Track

MAX_PLAYLISTS = 10  # per user
NAME_LIMIT = 40
MAX_SONGS = 1000  # per playlist
MSG_LIMIT = 3800

_YT_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def _col():
    return db.db.playlists


def _q(text: str, expandable: bool = False) -> str:
    """Wraps text in a Telegram blockquote (expandable = collapsed when long)."""
    open_tag = "<blockquote expandable>" if expandable else "<blockquote>"
    return f"{open_tag}{text}</blockquote>"


async def _reply(m: types.Message, text: str):
    return await m.reply_text(_q(text))


async def _edit_msg(msg: types.Message, text: str):
    return await msg.edit_text(_q(text))


# ───────────────────────── helpers ─────────────────────────


def _args(m: types.Message) -> str:
    parts = (m.text or "").split(None, 1)
    return parts[1].strip() if len(parts) > 1 else ""


def norm_id(raw: str) -> str:
    """'playlist-tgpl_ab12', 'tgpl_ab12' or just 'ab12' -> 'tgpl_ab12'."""
    pid = (raw or "").strip()
    if pid.lower().startswith("playlist-"):
        pid = pid[len("playlist-"):]
    return pid if pid.startswith("tgpl_") else f"tgpl_{pid}"


def parse_playlist_id(text: str) -> str | None:
    """Returns a playlist id if `text` looks like `playlist-<id>` / `tgpl_<id>`."""
    text = (text or "").strip()
    low = text.lower()
    if low.startswith("playlist-") and len(text) > len("playlist-"):
        return norm_id(text)
    if low.startswith("tgpl_") and len(text) > len("tgpl_"):
        return text
    return None


async def get_playlist(pid: str) -> dict | None:
    return await _col().find_one({"_id": pid})


def _song_to_track(song: dict, mention: str, chat_id: int, video: bool) -> Track:
    tid = str(song.get("track_id") or "")
    url = song.get("url") or ""
    if _YT_ID.match(tid) and "youtu" in url:
        thumbnail = f"https://i.ytimg.com/vi/{tid}/hqdefault.jpg"
    else:
        thumbnail = config.DEFAULT_THUMB
    dur = int(song.get("duration") or 0)
    return Track(
        id=tid,
        channel_name="Playlist",
        duration=yt._format_duration(dur),
        duration_sec=dur,
        title=(song.get("name") or "Unknown")[:25],
        url=url,
        thumbnail=thumbnail,
        user=mention,
        view_count="",
        video=video,
        message_chat_id=chat_id,
    )


async def load_playlist_tracks(
    pid: str, mention: str, chat_id: int, video: bool = False
) -> tuple[dict | None, list[Track]]:
    """Used by /play playlist-<id>. Returns (playlist_doc | None, tracks)."""
    pl = await get_playlist(pid)
    if not pl:
        return None, []
    tracks = [
        _song_to_track(s, mention, chat_id, video)
        for s in pl.get("songs", [])
        if s.get("track_id")
        and 0 < int(s.get("duration") or 1) <= config.DURATION_LIMIT
    ]
    return pl, tracks


async def _owned(m: types.Message, pid: str) -> dict | None:
    """Fetch playlist and make sure the sender owns it (replies on failure)."""
    pl = await get_playlist(pid)
    if not pl:
        await _reply(m, "Playlist not found. Please check the playlist ID.")
        return None
    if pl.get("user_id") != m.from_user.id:
        await _reply(m, "You can only modify playlists that you created.")
        return None
    return pl


def _fmt_total(seconds: int) -> str:
    h, rem = divmod(max(int(seconds), 0), 3600)
    mi, s = divmod(rem, 60)
    return f"{h}:{mi:02d}:{s:02d}" if h else f"{mi}:{s:02d}"


async def _resolve(query: str, mention: str) -> list[Track]:
    """Turns a song name / URL / playlist URL into a list of Tracks."""
    if yt.valid(query) and "playlist" in query:
        return await yt.playlist(MAX_SONGS, mention, query, False)
    res = await yt.search(query, 0)
    if not res:
        return []
    return res if isinstance(res, list) else [res]


# ───────────────────────── commands ─────────────────────────


@app.on_message(filters.command(["createplaylist"]) & ~app.bl_users)
async def _create(_, m: types.Message):
    if not m.from_user:
        return
    name = _args(m)
    if not name:
        return await _reply(m, "<b>Usage:</b> /createplaylist [playlist name]")

    uid = m.from_user.id
    if await _col().count_documents({"user_id": uid}) >= MAX_PLAYLISTS:
        return await _reply(m, 
            f"You have reached the maximum limit of {MAX_PLAYLISTS} playlists."
        )

    name = name[:NAME_LIMIT]
    pid = f"tgpl_{secrets.token_hex(5)}"
    await _col().insert_one({"_id": pid, "name": name, "user_id": uid, "songs": []})
    await _reply(m, 
        f"Playlist <b>{html.escape(name)}</b> has been created successfully.\n"
        f"ID: <code>{pid}</code>\n\n"
        f"Add songs: <code>/addtoplaylist {pid} song name</code>\n"
        f"Play it: <code>/play playlist-{pid}</code>"
    )


@app.on_message(filters.command(["myplaylists"]) & ~app.bl_users)
async def _my(_, m: types.Message):
    if not m.from_user:
        return
    docs = await _col().find({"user_id": m.from_user.id}).to_list(length=None)
    if not docs:
        return await _reply(m, "You do not have any playlists.")

    lines = [
        f"• {html.escape(d.get('name', '?'))} — {len(d.get('songs', []))} tracks\n"
        f"  ID: <code>{d['_id']}</code>"
        for d in docs
    ]
    await _reply(m, "<b>📋 My Playlists</b>\n\n" + "\n".join(lines))


@app.on_message(filters.command(["playlistinfo"]) & ~app.bl_users)
async def _info(_, m: types.Message):
    args = _args(m).split()
    if not args:
        return await _reply(m, "<b>Usage:</b> /playlistinfo [playlist id] [page]")

    pl = await get_playlist(norm_id(args[0]))
    if not pl:
        return await _reply(m, "Playlist not found. Please check the playlist ID.")

    owner = "Unknown"
    try:
        user = await app.get_users(pl["user_id"])
        owner = html.escape(user.first_name or "Unknown")
    except Exception:
        pass

    songs = pl.get("songs", [])
    total = sum(int(s.get("duration") or 0) for s in songs)
    header = (
        "<b>🎵 Playlist Info</b>\n\n"
        f"<b>Name:</b> {html.escape(pl.get('name', '?'))}\n"
        f"<b>Owner:</b> {owner}\n"
        f"<b>Songs:</b> {len(songs)}\n"
        f"<b>Duration:</b> {_fmt_total(total)}\n"
        f"<b>ID:</b> <code>{pl['_id']}</code>\n"
    )
    if not songs:
        return await _reply(m, header + "\nThis playlist is empty.")

    lines = []
    for i, s in enumerate(songs, 1):
        title = html.escape(s.get("name") or "Unknown")
        url = html.escape(s.get("url") or "", quote=True)
        dur = _fmt_total(int(s.get("duration") or 0))
        lines.append(f'{i}. <a href="{url}">{title}</a> ({dur})' if url else f"{i}. {title} ({dur})")

    # split into pages that fit one Telegram message
    pages, cur, size = [], [], len(header) + 120
    for line in lines:
        if size + len(line) + 1 > MSG_LIMIT:
            pages.append("\n".join(cur))
            cur, size = [], len(header) + 120
        cur.append(line)
        size += len(line) + 1
    pages.append("\n".join(cur))

    page = 1
    if len(args) > 1 and args[1].isdigit():
        page = min(max(int(args[1]), 1), len(pages))

    footer = ""
    if len(pages) > 1:
        footer = f"\n<b>Page {page}/{len(pages)}</b>"
        if page < len(pages):
            footer += f" — <code>/playlistinfo {pl['_id']} {page + 1}</code> for next page"
    await m.reply_text(_q(header) + _q(pages[page - 1], expandable=True) + footer)


@app.on_message(filters.command(["addtoplaylist"]) & ~app.bl_users)
async def _add(_, m: types.Message):
    if not m.from_user:
        return
    parts = _args(m).split(None, 1)
    if len(parts) != 2:
        return await _reply(m, 
            "<b>Usage:</b> /addtoplaylist [playlist id] [song name / URL]"
        )

    pid = norm_id(parts[0])
    pl = await _owned(m, pid)
    if not pl:
        return

    songs = pl.get("songs", [])
    room = MAX_SONGS - len(songs)
    if room <= 0:
        return await _reply(m, f"This playlist is full (max {MAX_SONGS} tracks).")

    sent = await _reply(m, "🔎 Searching...")
    mention = m.from_user.mention
    try:
        tracks = await _resolve(parts[1], mention)
    except Exception as e:
        logger.warning(f"[Playlist] resolve failed: {e}")
        tracks = []
    if not tracks:
        return await _edit_msg(sent, "No playable tracks were found for that query.")

    existing = {s.get("track_id") for s in songs}
    new, seen = [], set()
    for t in tracks:
        if not t.id or t.id in existing or t.id in seen:
            continue
        seen.add(t.id)
        new.append(
            {
                "url": t.url,
                "name": t.title,
                "track_id": t.id,
                "duration": int(t.duration_sec or 0),
                "platform": "api" if yt.is_platform_url(t.url or "") else "youtube",
            }
        )
        if len(new) >= room:
            break

    if not new:
        return await _edit_msg(sent, "That track is already in the playlist.")

    await _col().update_one(
        {"_id": pid, "user_id": m.from_user.id},
        {"$push": {"songs": {"$each": new}}},
    )
    name = html.escape(pl.get("name", "?"))
    if len(new) == 1:
        await _edit_msg(sent, 
            f"Track <b>{html.escape(new[0]['name'])}</b> has been added to playlist <b>{name}</b>."
        )
    else:
        await _edit_msg(sent, f"Added <b>{len(new)}</b> tracks to playlist <b>{name}</b>.")


@app.on_message(filters.command(["removefromplaylist"]) & ~app.bl_users)
async def _remove(_, m: types.Message):
    if not m.from_user:
        return
    parts = _args(m).split(None, 1)
    if len(parts) != 2:
        return await _reply(m, 
            "<b>Usage:</b> /removefromplaylist [playlist id] [track #]"
        )

    pid = norm_id(parts[0])
    pl = await _owned(m, pid)
    if not pl:
        return

    songs = pl.get("songs", [])
    ident = parts[1].strip()
    target = None
    if ident.isdigit():
        idx = int(ident)
        if not 1 <= idx <= len(songs):
            return await _reply(m, "Invalid track number.")
        target = songs[idx - 1]
    else:
        target = next(
            (s for s in songs if ident in (s.get("url"), s.get("track_id"))), None
        )
    if not target:
        return await _reply(m, "Track not found in the playlist.")

    await _col().update_one(
        {"_id": pid, "user_id": m.from_user.id},
        {"$pull": {"songs": {"track_id": target["track_id"]}}},
    )
    await _reply(m, 
        f"Removed <b>{html.escape(target.get('name', '?'))}</b> from playlist "
        f"<b>{html.escape(pl.get('name', '?'))}</b>."
    )


@app.on_message(filters.command(["editplaylist"]) & ~app.bl_users)
async def _edit(_, m: types.Message):
    if not m.from_user:
        return
    parts = _args(m).split(None, 1)
    if len(parts) != 2:
        return await _reply(m, "<b>Usage:</b> /editplaylist [playlist id] [new name]")

    pid = norm_id(parts[0])
    pl = await _owned(m, pid)
    if not pl:
        return

    new_name = parts[1].strip()[:NAME_LIMIT]
    await _col().update_one(
        {"_id": pid, "user_id": m.from_user.id}, {"$set": {"name": new_name}}
    )
    await _reply(m, 
        f"Playlist renamed: <b>{html.escape(pl.get('name', '?'))}</b> → "
        f"<b>{html.escape(new_name)}</b>."
    )


@app.on_message(filters.command(["deleteplaylist"]) & ~app.bl_users)
async def _delete(_, m: types.Message):
    if not m.from_user:
        return
    arg = _args(m)
    if not arg:
        return await _reply(m, "<b>Usage:</b> /deleteplaylist [playlist id]")

    pid = norm_id(arg.split()[0])
    pl = await _owned(m, pid)
    if not pl:
        return

    await _col().delete_one({"_id": pid, "user_id": m.from_user.id})
    await _reply(m, 
        f"Playlist <b>{html.escape(pl.get('name', '?'))}</b> has been deleted successfully."
    )
