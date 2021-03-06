from datetime import time as d_time, timedelta as d_timedelta, timezone as d_timezone
import logging
from modules.json import Json
from modules.threading import Thread
from os.path import getmtime, isfile
from time import sleep
from typing import Union
from threading import current_thread

logger = logging.getLogger("main")
_FILE_PATH = "config.json"

_CONFIG: dict
modify_time = 0

def _gen_config():
    """
    如果沒有設置檔，則從範例中生成。
    """
    with open("config-example.json", mode="rb") as example_file:
        EXAMPLE_DATA = example_file.read()
    with open("config.json", mode="wb") as config_file:
        config_file.write(EXAMPLE_DATA)
    Config.update()
    sleep(1)
    logger.critical("config.json not found.")
    logger.info("Generate a new config.json from config-example.json.")
    Config.ready(False)
    current_thread().stop()

def _config_patch():
    """
    設置檔完整度檢查。
    """
    EXAMPLE_DATA = Json.load("config-example.json")
    CONFIG_DATA = Json.load(_FILE_PATH)
    Json.dump("config.json", __patch(EXAMPLE_DATA, CONFIG_DATA))

def __patch(example: dict, config: dict):
    """
    設置完整度修復。
    """
    example = example.copy()
    config = config.copy()
    for key, value in example.items():
        try:
            c_value = config[key]
            if type(c_value) == dict:
                c_value = __patch(value, c_value)
                config[key] = c_value
        except KeyError:
            config[key] = value
    return config

class _Discord_Config(dict):
    token: str
    prefixs: list[str] = []
    admin_role: int
    def __init__(self, _config: dict) -> None:
        for item in _config.items():
            self[item[0]] = item[1]
        self.token = _config["token"]
        self.prefixs = _config["prefixs"]
        self.admin_role = _config["admin_role"]

class _Rcon_Info(dict):
    address: str
    port: int
    password: str
    timeout: int
    m_filter: str
    def __init__(self, _config: dict) -> None:
        for item in _config.items():
            self[item[0]] = item[1]
        self.address = _config["address"]
        self.port = _config["port"]
        self.password = _config["password"]
        self.timeout = _config["timeout"]
        self.m_filter = _config["m_filter"]

class _Discord_Info(dict):
    chat_channel: int
    state_channel: int
    message_forward: bool
    def __init__(self, _config: dict) -> None:
        for item in _config.items():
            self[item[0]] = item[1]
        self.chat_channel = _config["chat_channel"]
        self.state_channel = _config["state_channel"]
        self.message_forward = _config["message_forward"]

class _Ark_Server(dict):
    key: str
    local: bool
    dir_path: str
    file_name: str
    display_name: str
    rcon: _Rcon_Info
    discord: _Discord_Info
    save: str
    restart: str
    clear_dino: bool
    rcon_session = None
    def __init__(self, _config: dict) -> None:
        for item in _config.items():
            self[item[0]] = item[1]
        self.key = _config["key"]
        self.local = _config["local"]
        self.dir_path = _config["dir_path"]
        self.file_name = _config["file_name"]
        self.display_name = _config["display_name"]
        self.rcon = _Rcon_Info(_config["rcon"])
        self.discord = _Discord_Info(_config["discord"])
        self.save = _config["save"]
        self.restart = _config["restart"]
        self.clear_dino = _config["clear_dino"]

class _Web_Console(dict):
    host: str
    port: int
    debug: bool
    def __init__(self, _config: dict) -> None:
        for item in _config.items():
            self[item[0]] = item[1]
        self.host = _config["host"]
        self.port = _config["port"]
        self.debug = _config["debug"]

class _Time_Data(list[str, bool]):
    time: d_time
    backup: bool
    def __init__(self, _config: list) -> None:
        for item in _config:
            self.append(item)
        self.time = d_time.fromisoformat(_config[0])
        self.backup = _config[1]

class _Time_Setting(dict):
    time_zone: d_timezone
    save_delay: int
    save_tables: dict[list[_Time_Data]] = {}
    restart_tables: dict[list[_Time_Data]] = {}
    backup_day: d_timedelta
    def __init__(self, _config: dict) -> None:
        for item in _config.items():
            self[item[0]] = item[1]
        self.time_zone = d_timezone(d_timedelta(hours=_config["time_zone"]))
        self.save_delay = _config["save_delay"]
        _save_tables: dict = _config["save_tables"]
        for key in _save_tables.keys():
            time_data = _save_tables[key]
            self.save_tables[key] = [_Time_Data(__config) for __config in time_data]
        _restart_tables: dict = _config["restart_tables"]
        for key in _restart_tables.keys():
            time_data = _restart_tables[key]
            self.restart_tables[key] = [_Time_Data(__config) for __config in time_data]
        self.backup_day = d_timedelta(days=_config["backup_day"])

class _Other_Setting(dict):
    low_battery: int
    m_filter_tables: dict[dict[list[str]]] = {}
    log_level: str
    message: dict[str] = {}
    state_message: dict[str] = {}
    def __init__(self, _config: dict):
        for item in _config.items():
            self[item[0]] = item[1]
        self.low_battery = _config["low_battery"]
        self.m_filter_tables = _config["m_filter_tables"].copy()
        self.log_level = _config["log_level"]
        self.message = _config["message"]
        self.state_message = _config["state_message"]

class Config:
    discord: _Discord_Config
    servers: list[_Ark_Server] = []
    web_console: _Web_Console
    time_setting: _Time_Setting
    other_setting: _Other_Setting
    updated: bool = False
    readied: Union[bool, None] = None

    @classmethod
    def update(self):
        """
        從設置檔中更新當前設置。
        """
        global _CONFIG
        _config_patch()
        _CONFIG = Json.load(_FILE_PATH)

        self.config = _CONFIG.copy()
        self.discord = _Discord_Config(_CONFIG["discord"])
        i = 0
        for _config in _CONFIG["servers"]:
            if len(self.servers) > i:
                from modules.rcon import Rcon_Session
                self.servers[i].rcon_session = Rcon_Session(self.servers[i])
            else:
                self.servers.append(_Ark_Server(_config))
            i += 1
        self.web_console = _Web_Console(_CONFIG["web_console"])
        self.time_setting = _Time_Setting(_CONFIG["time_setting"])
        self.other_setting = _Other_Setting(_CONFIG["other_setting"])
        self.updated = True

    @classmethod
    def ready(self, value: bool):
        self.readied = value

def auto_update():
    """
    自動更新設置檔。
    """
    global modify_time
    # 檢查檔案是否存在
    if not isfile(_FILE_PATH):
        _gen_config()
    else:
        Config.update()
    # 準備完成
    Config.ready(True)
    while True:
        # 檢查設置檔修改時間
        if getmtime("config.json") != modify_time:
            Config.update()
            modify_time = getmtime("config.json")
        sleep(1)

auto_update_thread = Thread(target=auto_update, name="Config_Auto_Update")
auto_update_thread.start()
