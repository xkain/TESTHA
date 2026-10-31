"""Support for ESPSomfy RTS updates."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any, cast

from homeassistant.components.update import (
    UpdateDeviceClass,
    UpdateEntity,
    UpdateEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval

from .const import DOMAIN, EVT_CONNECTED, EVT_FWSTATUS, EVT_UPDPROGRESS, FW_RELEASES_URL
from .controller import ESPSomfyController, ota_error
from .entity import ESPSomfyEntity

_LOGGER = logging.getLogger(__name__)

# Relecture du catalogue OTA (firmware à relais) en plus de chaque fwStatus.
CATALOG_REFRESH = timedelta(hours=6)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ESPSomfy RTS update based on a config entry."""
    controller: ESPSomfyController = hass.data[DOMAIN][config_entry.entry_id]
    data = controller.api.get_config()
    if "serverId" in data:
        async_add_entities([ESPSomfyRTSUpdateEntity(controller=controller)])


class ESPSomfyRTSUpdateEntity(ESPSomfyEntity, UpdateEntity):
    """Defines an ESPSomfy RTS update entity."""
    _attr_device_class = UpdateDeviceClass.FIRMWARE
    _attr_entity_category = EntityCategory.CONFIG

    _attr_should_poll = False

    _attr_has_entity_name = True
    _attr_translation_key = "firmware"

    def __init__(self, *, controller: ESPSomfyController) -> None:
        """Initialize the update entity."""
        super().__init__(data=None, controller=controller)

        self._controller = controller
        self._available = True
        self._attr_unique_id = f"update_{controller.unique_id}"
        self._update_status = 0
        self._fw_progress = 100
        self._app_progress = 100
        self._total_progress = 100

        self._attr_supported_features = (
            UpdateEntityFeature.SPECIFIC_VERSION
            | UpdateEntityFeature.PROGRESS
            | UpdateEntityFeature.RELEASE_NOTES
        )

    async def async_added_to_hass(self) -> None:
        """Start the periodic catalog refresh."""
        await super().async_added_to_hass()

        async def _refresh(_now=None) -> None:
            await self._controller.refresh_catalog(force=True)
            self.async_write_ha_state()

        self.async_on_remove(
            async_track_time_interval(self.hass, _refresh, CATALOG_REFRESH)
        )
        self.hass.async_create_task(_refresh())

    async def _async_refresh_catalog(self) -> None:
        await self._controller.refresh_catalog()
        self.async_write_ha_state()

    def _set_progress(self, pct: int) -> None:
        # Appelé à chaque bloc envoyé : n'écrire l'état que quand le pourcentage change.
        if pct == self._total_progress:
            return
        self._total_progress = pct
        self.async_write_ha_state()

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if (
            self._controller.data["event"] == EVT_CONNECTED
            and "connected" in self._controller.data
        ):
            self._available = bool(self._controller.data["connected"])
            self.async_write_ha_state()

        elif self._controller.data["event"] == EVT_FWSTATUS:
            evt_data = self._controller.data

            _LOGGER.debug("ESPSomfy RTS FWSTATUS Payload: %s", evt_data)

            check_updates = evt_data.get("checkForUpdate", False)
            internet_ok = evt_data.get("inetAvailable", False)

            # Firmware à relais : c'est HA qui télécharge, l'accès Internet du boîtier ne compte
            # plus. Ancien firmware : installation offerte seulement si l'ESP confirme les deux.
            relay = self._controller.relay_ota
            if relay:
                self.hass.async_create_task(self._async_refresh_catalog())
            if check_updates and (relay or internet_ok):
                self._attr_supported_features = (
                    UpdateEntityFeature.INSTALL
                    | UpdateEntityFeature.SPECIFIC_VERSION
                    | UpdateEntityFeature.PROGRESS
                    | UpdateEntityFeature.BACKUP
                    | UpdateEntityFeature.RELEASE_NOTES
                )
            else:
                self._attr_supported_features = (
                    UpdateEntityFeature.SPECIFIC_VERSION
                    | UpdateEntityFeature.PROGRESS
                    | UpdateEntityFeature.RELEASE_NOTES
                )
            self.async_write_ha_state()

        elif self.controller.data["event"] == EVT_UPDPROGRESS:
            d = self.controller.data
            if "part" in d:
                if int(d["part"]) == 0:
                    self._app_progress = 0
                    self._fw_progress = (int(d["loaded"]) / int(d["total"])) * 100
                elif int(d["part"]) == 100:
                    self._fw_progress = 100
                    self._app_progress = (int(d["loaded"]) / int(d["total"])) * 100
                self._total_progress = int((self._fw_progress + self._app_progress) / 2)
                self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Indicates whether the shade is available."""
        return self._available

    @property
    def can_install(self) -> bool:
        """Indicates whether the current version supports firmware installation."""
        return True

    @property
    def installed_version(self) -> str | None:
        """Version currently installed and in use."""
        if (version := self._controller.version) is None:
            return None
        return str(version)

    @property
    def latest_version(self) -> str | None:
        """Latest version available for install."""
        cfg = self._controller.api.get_config()
        if cfg.get("checkForUpdate", False) is False:
            return None

        if (latest := self._controller.latest_version) is None:
            return None
        return str(latest)

    @property
    def in_progress(self) -> bool | None:
        """Update installation progress."""
        return self._total_progress < 100

    @property
    def update_percentage(self) -> int | None:
        """Update installation percentage."""
        if self._total_progress < 100:
            return self._total_progress
        return None

    @property
    def release_url(self) -> str | None:
        """URL to the full release notes of the latest version available."""
        if (version := self.latest_version) is None:
            return None
        return f"{FW_RELEASES_URL}{version}"

    async def async_install(
        self, version: str | None, backup: bool, **kwargs: Any
    ) -> None:
        """Install an update."""
        success = True
        if backup:
            success = await self._controller.create_backup()
            if not success:
                raise ota_error("ota_backup_failed")
        if success and self._controller.relay_ota:
            version = version or self.latest_version
            if version is None:
                raise ota_error("ota_no_version")
            self._set_progress(0)
            try:
                await self._controller.update_firmware(version, self._set_progress)
            except HomeAssistantError:
                raise
            except Exception as e:
                _LOGGER.exception("ESPSomfy-RTS firmware update failed")
                raise ota_error("ota_failed", error=e) from e
            finally:
                self._set_progress(100)
            return
        if success:
            version = cast(str, self.latest_version)
            if version is not None:
                await self.controller.update_firmware(version)

    async def async_release_notes(self) -> str | None:
        """Return the release notes from GitHub."""
        if (version := self.latest_version) is None:
            return None

        return await self._controller.fetch_release_notes(version)

    async def async_update(self) -> None:
        """Update the entity state.

        Overridden to prevent Home Assistant from polling the coordinator
        and triggering a NotImplementedError.
        """
        pass
