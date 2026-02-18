"""Data coordinator for Weight Watchers."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    WeightWatchersApiClient,
    WeightWatchersAuthError,
    WeightWatchersConnectionError,
    WeightWatchersError,
    WeightWatchersPointsSnapshot,
)
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class WeightWatchersDataUpdateCoordinator(
    DataUpdateCoordinator[WeightWatchersPointsSnapshot]
):
    """Coordinate Weight Watchers API polling."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        api: WeightWatchersApiClient,
        config_entry: ConfigEntry,
    ) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
            config_entry=config_entry,
        )
        self.api = api

    async def _async_update_data(self) -> WeightWatchersPointsSnapshot:
        try:
            return await self.api.async_get_points_summary()
        except WeightWatchersAuthError as err:
            raise ConfigEntryAuthFailed("Weight Watchers authentication failed") from err
        except WeightWatchersConnectionError as err:
            raise UpdateFailed(f"Connection error: {err}") from err
        except WeightWatchersError as err:
            raise UpdateFailed(str(err)) from err
