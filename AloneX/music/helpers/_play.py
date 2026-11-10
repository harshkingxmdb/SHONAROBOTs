# Copyright (c) 2025 @THECDERQUEEN
# Licensed under the MIT License.
# This file is part of @SHONA_BOTS
#SHONA-DECODER

import asyncio

from pyrogram import enums, errors, types

from AloneX.music import app, config, db, lang, logger, queue, yt
from AloneX.music.helpers import utils


def checkUB(play):
    async def wrapper(_, m: types.Message):
        # `lang.language()` is not used here on purpose — it silently drops
        # any message with no `from_user` (channel posts, anonymous admins).
        if m.chat.id in db.blacklisted:
            logger.warning(f"Chat {m.chat.id} is blacklisted, leaving...")
            return await m.chat.leave()
        m.lang = await lang.get_lang(m.chat.id)

        is_channel_cmd = m.command[0].startswith("c")
        target_chat = m.chat

        if is_channel_cmd:
            if m.chat.type == enums.ChatType.CHANNEL:
                # Direct post in the channel itself.
                target_chat = m.chat

            elif m.chat.type == enums.ChatType.PRIVATE:
                # DM with the bot: /cplay @channel_username <song>
                # or:              /cplay -1001234567890 <song>
                if len(m.command) < 2 or not (
                    m.command[1].startswith("@") or m.command[1].lstrip("-").isdigit()
                ):
                    return await m.reply_text(
                        m.lang.get(
                            "cplay_dm_usage",
                            "Please mention the channel: /cplay @channel_username <song name>\n"
                            "(private channels: /cplay -1001234567890 <song name>)",
                        )
                    )
                target_ref = m.command[1]
                target_ref = target_ref[1:] if target_ref.startswith("@") else int(target_ref)
                try:
                    target_chat = await app.get_chat(target_ref)
                except Exception:
                    return await m.reply_text(
                        m.lang.get(
                            "cplay_channel_not_found",
                            "Couldn't find that channel. For private channels, the bot "
                            "must already be an admin there.",
                        )
                    )
                if target_chat.type != enums.ChatType.CHANNEL:
                    return await m.reply_text(
                        m.lang.get("cplay_not_a_channel", "That isn't a channel.")
                    )
                # Drop the channel reference so the rest is just the song name.
                m.command = [m.command[0]] + m.command[2:]

            elif m.chat.type == enums.ChatType.SUPERGROUP:
                # Discussion group linked to a channel — linked_chat is only
                # populated by fetching the chat fresh.
                full_chat = await app.get_chat(m.chat.id)
                linked = full_chat.linked_chat
                if not linked or linked.type != enums.ChatType.CHANNEL:
                    return await m.reply_text(
                        m.lang.get(
                            "cplay_group_not_linked",
                            "This group isn't linked to a channel. Use /play here, or /cplay directly in a channel.",
                        )
                    )
                target_chat = await app.get_chat(linked.id)

            else:
                return await m.reply_text(m.lang["play_chat_invalid"])

        else:
            if m.chat.type == enums.ChatType.CHANNEL:
                return await m.reply_text(
                    m.lang.get(
                        "play_cmd_group_only",
                        "This command only works in groups. Use /cplay (or /cvplay) in channels instead.",
                    )
                )
            if m.chat.type != enums.ChatType.SUPERGROUP:
                await m.reply_text(m.lang["play_chat_invalid"])
                return await app.leave_chat(m.chat.id)
            target_chat = m.chat

        target_chat_id = target_chat.id
        is_channel = target_chat.type == enums.ChatType.CHANNEL

        if not m.from_user and not is_channel:
            return await m.reply_text(m.lang["play_user_invalid"])

        if not m.reply_to_message and (
            len(m.command) < 2 or (len(m.command) == 2 and m.command[1] == "-f")
        ):
            return await m.reply_text(m.lang["play_usage"])

        if len(queue.get_queue(target_chat_id)) >= config.QUEUE_LIMIT:
            return await m.reply_text(m.lang["play_queue_full"].format(config.QUEUE_LIMIT))

        force = m.command[0].endswith("force") or (
            len(m.command) > 1 and "-f" in m.command[1]
        )
        video = "vplay" in m.command[0] and config.VIDEO_PLAY
        url = utils.get_url(m)
        m3u8 = url and not yt.valid(url)

        # NOTE: the old "admin only play" gate (play_mode / force) was
        # removed on purpose — every group member can use play / vplay /
        # cplay / cvplay and their force variants.

        if target_chat_id not in db.active_calls:
            client = await db.get_client(target_chat_id)
            try:
                member = await app.get_chat_member(target_chat_id, client.id)
                if member.status in [
                    enums.ChatMemberStatus.BANNED,
                    enums.ChatMemberStatus.RESTRICTED,
                ]:
                    try:
                        await app.unban_chat_member(
                            chat_id=target_chat_id, user_id=client.id
                        )
                    except:
                        return await m.reply_text(
                            m.lang["play_banned"].format(
                                app.name,
                                client.id,
                                client.mention,
                                f"@{client.username}" if client.username else None,
                            )
                        )
            except errors.ChatAdminRequired:
                return await m.reply_text(m.lang["admin_required"])
            except (errors.UserNotParticipant, errors.exceptions.bad_request_400.UserNotParticipant):
                if target_chat.username:
                    invite_link = target_chat.username
                    try:
                        await client.resolve_peer(invite_link)
                    except:
                        pass
                else:
                    try:
                        invite_link = target_chat.invite_link
                        if not invite_link:
                            invite_link = await app.export_chat_invite_link(target_chat_id)
                    except errors.ChatAdminRequired:
                        return await m.reply_text(m.lang["admin_required"])
                    except Exception as ex:
                        return await m.reply_text(
                            m.lang["play_invite_error"].format(type(ex).__name__)
                        )

                umm = await m.reply_text(m.lang["play_invite"].format(app.name))
                await asyncio.sleep(2)
                try:
                    await client.join_chat(invite_link)
                except errors.UserAlreadyParticipant:
                    pass
                except errors.InviteRequestSent:
                    await asyncio.sleep(2)
                    try:
                        await client.approve_chat_join_request(target_chat_id, client.id)
                    except errors.HideRequesterMissing:
                        pass
                    except Exception as ex:
                        return await umm.edit_text(
                            m.lang["play_invite_error"].format(type(ex).__name__)
                        )
                except Exception as ex:
                    logger.error(f"Error joining chat - {target_chat_id}: {ex}")
                    return await umm.edit_text(
                        m.lang["play_invite_error"].format(type(ex).__name__)
                    )

                await umm.delete()
                await client.resolve_peer(target_chat_id)

        if await db.get_cmd_delete(target_chat_id):
            try:
                await m.delete()
            except:
                pass

        try:
            return await play(_, m, force, m3u8, video, url, target_chat_id)
        except (errors.Forbidden, errors.exceptions.Forbidden):
            logger.warning(f"Cannot write to chat {m.chat.id}, leaving...")
            return await m.chat.leave()

    return wrapper
