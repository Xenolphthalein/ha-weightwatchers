"""Sensor platform for Weight Watchers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .api import WeightWatchersPointsSnapshot
from .const import CONF_REGION, DOMAIN
from .coordinator import WeightWatchersDataUpdateCoordinator

POINTS_UNIT = "pt"


@dataclass(frozen=True, kw_only=True)
class WeightWatchersSensorEntityDescription(SensorEntityDescription):
    """Describes WW sensor entity."""

    value_fn: Callable[[WeightWatchersPointsSnapshot], int | None]


SENSOR_DESCRIPTIONS: tuple[WeightWatchersSensorEntityDescription, ...] = (
    WeightWatchersSensorEntityDescription(
        key="daily_points_remaining",
        name="Daily points remaining",
        native_unit_of_measurement=POINTS_UNIT,
        icon="mdi:counter",
        suggested_display_precision=0,
        value_fn=lambda data: data.daily_points_remaining,
    ),
    WeightWatchersSensorEntityDescription(
        key="daily_points_used",
        name="Daily points used",
        native_unit_of_measurement=POINTS_UNIT,
        icon="mdi:food-apple",
        suggested_display_precision=0,
        value_fn=lambda data: data.daily_points_used,
    ),
    WeightWatchersSensorEntityDescription(
        key="daily_activity_points_earned",
        name="Daily activity points earned",
        native_unit_of_measurement=POINTS_UNIT,
        icon="mdi:run",
        suggested_display_precision=0,
        value_fn=lambda data: data.daily_activity_points_earned,
    ),
    WeightWatchersSensorEntityDescription(
        key="weekly_points_remaining",
        name="Weekly points remaining",
        native_unit_of_measurement=POINTS_UNIT,
        icon="mdi:calendar-week",
        suggested_display_precision=0,
        value_fn=lambda data: data.weekly_points_remaining,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up WW sensors from a config entry."""
    coordinator: WeightWatchersDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        WeightWatchersPointSensor(coordinator, entry, description)
        for description in SENSOR_DESCRIPTIONS
    )


class WeightWatchersPointSensor(
    CoordinatorEntity[WeightWatchersDataUpdateCoordinator], SensorEntity
):
    """Representation of a Weight Watchers points sensor."""

    entity_description: WeightWatchersSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WeightWatchersDataUpdateCoordinator,
        entry: ConfigEntry,
        description: WeightWatchersSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description

        base_id = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{base_id}_{description.key}"
        account_slug = slugify(entry.data.get(CONF_USERNAME, "account"))
        self._attr_suggested_object_id = (
            f"weight_watchers_{account_slug}_{description.key}"
        )

        username = entry.data.get(CONF_USERNAME, "account")
        region = entry.data.get(CONF_REGION, "WW")
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Weight Watchers {username}",
            model=f"Region {region}",
            manufacturer="Weight Watchers",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> int | None:
        """Return the state."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, int | None]:
        """Expose raw WW API values used by this integration."""
        details = self.coordinator.data.raw_details if self.coordinator.data else {}
        return {
            "dailyPointsRemaining": details.get("dailyPointsRemaining"),
            "dailyPointsUsed": details.get("dailyPointsUsed"),
            "dailyActivityPointsEarned": details.get("dailyActivityPointsEarned"),
            "weeklyPointAllowanceRemaining": details.get(
                "weeklyPointAllowanceRemaining"
            ),
        }
