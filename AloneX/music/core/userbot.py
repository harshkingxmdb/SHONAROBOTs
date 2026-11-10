# Copyright (c) 2025 TheHamkerAlone
# Licensed under the MIT License.
# This file is part of AloneXMusic


from pyrogram import Client

from AloneX.music import config, logger


class Userbot(Client):
    def __init__(self):
        """
        Initializes the userbot with multiple clients.

        This method sets up clients for the userbot using predefined session strings.
        Each client is assigned a unique name based on the key in the `clients` dictionary.
        """
        self.clients = []
        self.shared = set()
        clients = {"one": "SESSION1", "two": "SESSION2", "three": "SESSION3"}
        for key, string_key in clients.items():
            name = f"AloneXUB{key[-1]}"
            session = getattr(config, string_key)

            # The same string must never be logged in twice (AUTH_KEY_DUPLICATED), so when the
            # music assistant is the manage bot's USER_STRING we reuse that very client.
            try:
                from AloneX import user as manage_user
                from config import USER_STRING

                if session and USER_STRING and session == USER_STRING:
                    setattr(self, key, manage_user)
                    self.shared.add(key)
                    continue
            except Exception:
                pass

            setattr(
                self,
                key,
                Client(
                    name=name,
                    api_id=config.API_ID,
                    api_hash=config.API_HASH,
                    session_string=session,
                ),
            )

    async def boot_client(self, num: int, ub: Client):
        """
        Boot a client and perform initial setup.
        Args:
            num (int): The client number to boot (1, 2, or 3).
            ub (Client): The userbot client instance.
        Raises:
            SystemExit: If the client fails to send a message in the log group.
        """
        clients = {
            1: self.one,
            2: self.two,
            3: self.three,
        }
        client = clients[num]
        if not client.is_connected:
            await client.start()
        try:
            await client.send_message(config.LOGGER_ID, "Assistant Started")
        except:
            raise SystemExit(f"Assistant {num} failed to send message in log group.")

        client.id = ub.me.id
        client.name = ub.me.first_name
        client.username = ub.me.username
        client.mention = ub.me.mention
        self.clients.append(client)
        try:
            await ub.join_chat("AloneUpdates")
        except:
            pass
        logger.info(f"Assistant {num} started as @{client.username}")

    async def boot(self):
        """
        Asynchronously starts the assistants.
        """
        if config.SESSION1:
            await self.boot_client(1, self.one)
        if config.SESSION2:
            await self.boot_client(2, self.two)
        if config.SESSION3:
            await self.boot_client(3, self.three)

    async def exit(self):
        """
        Asynchronously stops the assistants.
        """
        if config.SESSION1 and "one" not in self.shared:
            await self.one.stop()
        if config.SESSION2 and "two" not in self.shared:
            await self.two.stop()
        if config.SESSION3 and "three" not in self.shared:
            await self.three.stop()
        logger.info("Assistants stopped.")
