"""Constants for the ESPSomfy RTS integration."""

from homeassistant.const import Platform

VERSION = "v2.6.0"
DOMAIN = "espsomfy_rts_enhanced"
MANUFACTURER = "xkain"
API_CONTROLLER = "/controller"
API_SHADES = "/shades"
API_GROUPS = "/groups"
API_SHADECOMMAND = "/shadeCommand"
API_GROUPCOMMAND = "/groupCommand"
API_TILTCOMMAND = "/tiltCommand"
API_DISCOVERY = "/discovery"
API_LOGIN = "/login"
API_SETPOSITIONS = "/setPositions"
API_SETSENSOR = "/setSensor"
API_BACKUP = "/backup"
API_REBOOT = "/reboot"
API_RESTORE = "/restore"
API_SCHEDULES = "/schedules"
API_SAVESCHEDULE = "/saveSchedule"
# OTA par relais (firmware 3.0.1+) : le boîtier ne télécharge plus rien, l'intégration lit le
# catalogue publié sur Pages, récupère l'image et la pousse à /updateFirmware.
OTA_CATALOG_URL = "https://xkain.github.io/TESTRTS/ota/index.json"
FW_RAW_ROOT = "https://raw.githubusercontent.com/xkain/TESTRTS/"
FW_RELEASES_URL = "https://github.com/xkain/TESTRTS/releases/tag/"
EVT_CONTROLLER = "controller"
EVT_SHADESTATE = "shadeState"
EVT_GROUPSTATE = "groupState"
EVT_SHADECOMMAND = "shadeCommand"
EVT_SHADEADDED = "shadeAdded"
EVT_SHADEREMOVED = "shadeRemoved"
EVT_SCHEDULESTATE = "scheduleState"
EVT_SCHEDULEREMOVED = "scheduleRemoved"
EVT_CONNECTED = "connected"
EVT_FWSTATUS = "fwStatus"
EVT_UPDPROGRESS = "updateProgress"
EVT_WIFISTRENGTH = "wifiStrength"
EVT_ETHERNET = "ethernet"
EVT_MEMSTATUS = "memStatus"

ATTR_RESTOREFILE = "Restore File"
ATTR_AVAILABLE_MODES = "???"

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.COVER,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.UPDATE,
]
