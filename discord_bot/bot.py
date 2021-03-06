from asyncio import sleep as a_sleep
from discord import Message, Intents, TextChannel
from discord.client import Client
import logging
from modules.config import Config, _Ark_Server
from modules.rcon import Rcon_Session, TAG_DISCORD
from modules.threading import restart, stop
from time import time
from typing import Union

logger = logging.getLogger("main")

def _search_rcon(channel_id: int) -> Union[Rcon_Session, None]:
    server_config: _Ark_Server
    for server_config in Config.servers:
        if channel_id == server_config.discord.chat_channel:
            return server_config.rcon_session
    return None

class Custom_Client(Client):
    def __init__(self, *args, **kwargs):
        intents = Intents.all()
        super().__init__(*args, **kwargs, intents=intents)
        # print([logger.getLogger(name) for name in logger.root.manager.loggerDict])
        self.first_connect = True

    async def on_ready(self):
        if self.first_connect:
            self.first_connect = False
            logger.warning("Discord Bot Connected!")
            self.bg_task_1 = self.loop.create_task(self.state_update())
            self.bg_task_2 = self.loop.create_task(self.chat_update())
            self.main_thread_command = ""
            self.main_thread_command_time = 0
        else:
            logger.warning("Discord Bot Reonnected!")

    async def state_update(self):
        logger.info("state_update Start.")
        while True:
            await self._state_update()
            await a_sleep(60)

    async def _state_update(self):
        """
        自動更新狀態頻道。
        """
        for server_config in Config.servers:
            rcon_session: Rcon_Session = server_config.rcon_session
            # :red_circle: :green_circle: :orange_circle:
            if rcon_session.rcon_alive:
                state_message = Config.other_setting.state_message["running"]
            else:
                if rcon_session.server_alive:
                    if rcon_session.server_first_connect:
                        state_message = Config.other_setting.state_message["starting"]
                    elif rcon_session.rcon_alive == None:
                        state_message = Config.other_setting.state_message["network_disconnect"]
                    else:
                        state_message = Config.other_setting.state_message["rcon_disconnect"]
                else:
                    state_message = Config.other_setting.state_message["stopped"]
            state_channel = self.get_channel(server_config.discord.state_channel)
            if state_message != state_channel.name:
                logger.info("Update Statechannel Name.")
                await state_channel.edit(name=state_message)

    async def chat_update(self):
        """
        聊天同步。
        """
        logger.info("chat_update Start.")
        while True:
            for server_config in Config.servers:
                rcon_session: Rcon_Session = server_config.rcon_session
                mes = rcon_session.get(TAG_DISCORD)
                channel: TextChannel = None
                chat_content = None
                while mes != None:
                    arg = mes["args"]
                    if arg["type"] == "chat":
                        if channel == None:
                            channel = self.get_channel(arg["target"])
                            chat_content = mes["reply"]
                        else:
                            chat_content += f"\n{mes['reply']}"
                    elif arg["type"] == "user_command":
                        if type(arg["target"]) == int:
                            channel = self.get_channel(arg["target"])
                            await channel.send(mes["reply"])
                        else:
                            await arg["target"].send(mes["reply"])
                    mes = rcon_session.get(TAG_DISCORD)
                if chat_content != None and channel != None:
                    await channel.send(chat_content)
                await a_sleep(1)

    async def on_message(self, message: Message):
        if message.author == self.user: return
        logger.debug(f"[{message.channel.name}][{message.author.display_name}]{message.content}")
        if _search_rcon(message.channel.id) == None: return
        if Config.discord.admin_role not in [role.id for role in message.author.roles]: return

        content = message.content
        logger.info(f"[{message.channel.name}][{message.author.display_name}]{content}")

        # 判斷並移除開頭
        if not content.startswith(tuple(Config.discord.prefixs)): return
        for prefix in Config.discord.prefixs:
            if content.startswith(prefix):
                content = content[len(prefix):]
                break
        # 指令切分
        content_list = content.split(" ")
        if content_list[0] == "del":
            await message.delete()
            content_list = content_list[1:]
        if content_list[0] == "c" or content_list[0] == "cb":
            if content_list[0] == "c":
                backup = False
            else:
                backup = True
            rcon_session = _search_rcon(message.channel.id)
            delay = 5
            try: delay = int(content_list[2])
            except ValueError: pass
            except IndexError: pass
            reason = " ".join(content_list[3:])
            logger.info(f"Receive Command:{content_list}")
            if content_list[1] == "start":
                rcon_session.start(TAG_DISCORD)
            elif content_list[1] == "stop":
                rcon_session.stop(TAG_DISCORD, backup=backup, delay=delay, reason=reason)
            elif content_list[1] == "saveworld":
                rcon_session.save(TAG_DISCORD, backup=backup, delay=delay, reason=reason)
            elif content_list[1] == "restart":
                rcon_session.restart(TAG_DISCORD, backup=backup, delay=delay, reason=reason)
            elif content_list[1] == "clear":
                rcon_session.clear(TAG_DISCORD)
            elif content_list[1] == "backup":
                rcon_session.backup(TAG_DISCORD)
            else:
                target = message.author
                # if message.author.dm_channel.can_send():
                #     target = message.author.dm_channel.id
                # else:
                #     target = message.channel.id
                rcon_session.add(" ".join(content_list[1:]), TAG_DISCORD, {"type": "user_command", "target": target})
        elif content_list[0] == "m":
            if content_list[1] == "confirm" and time() - self.main_thread_command_time < 15:
                if self.main_thread_command == "stop":
                    stop()
                elif self.main_thread_command == "restart":
                    restart()
            else:
                self.main_thread_command = content_list[1]
                self.main_thread_command_time = time()
        elif content_list[0] == "debug" and message.author.id == 302774180611358720:
            await self._state_update()
    
    async def on_disconnect(self):
        logger.warning("Discord Bot Disconnected!")

    def run(self, *args, **kwargs) -> None:
        return super().run(Config.discord.token, *args, **kwargs)

if __name__ == "__main__":
    client = Client()
    client.run()