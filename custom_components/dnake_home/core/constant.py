from enum import Enum

TITLE = "Dnake Home"
DOMAIN = "dnake_home"
MANUFACTURER = "Dnake"

CONF_GATEWAY_IP = "gateway_ip"
CONF_AUTH_USERNAME = "auth_username"
CONF_AUTH_PASSWORD = "auth_password"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_GATEWAY_MACS = "gateway_macs"

DEFAULT_GATEWAY_IP = "192.168.1.2"
DEFAULT_AUTH_USERNAME = "admin"
DEFAULT_AUTH_PASSWORD = "123456"
DEFAULT_SCAN_INTERVAL = 10
DEFAULT_GATEWAY_MACS = []
DEFAULT_GATEWAY_CHECK_INTERVAL = 30


class Action(Enum):
    # 获取单设备状态
    ReadDev = "readDev"
    # 获取所有设备状态
    ReadAllDevState = "readAllDevState"
    # 控制设备
    CtrlDev = "ctrlDev"


class Cmd(Enum):
    # 灯.etc
    On = "on"
    # 灯.etc
    Off = "off"
    # 窗帘.etc
    Stop = "stop"
    # 窗帘.etc
    Level = "level"
    # 空调
    AirCondition = "airCondition"


class Power(Enum):
    On = "powerOn"
    Off = "powerOff"
