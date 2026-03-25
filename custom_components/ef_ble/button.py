"""EcoFlow BLE Button"""

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.button import (
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.ef_ble.eflib import DeviceBase

from . import DeviceConfigEntry
from .entity import EcoflowEntity


@dataclass(frozen=True, kw_only=True)
class EcoflowButtonEntityDescription(ButtonEntityDescription):
    availability_prop: str | None = None


BUTTON_TYPES = [
    # DPU
    EcoflowButtonEntityDescription(key="unpause_solar"),
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: DeviceConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add binary sensors for passed config_entry in HA."""
    device = config_entry.runtime_data

    new_buttons = [
        EcoflowButton(device, button_desc)
        for button_desc in BUTTON_TYPES
        if isinstance(getattr(device, button_desc.key, None), Callable)
    ]

    if new_buttons:
        async_add_entities(new_buttons)


class EcoflowButton(EcoflowEntity, ButtonEntity):
    def __init__(self, device: DeviceBase, entity_description: ButtonEntityDescription):
        super().__init__(device)

        self._attr_unique_id = f"ef_{device.serial_number}_{entity_description.key}"
        self._prop_name = entity_description.key
        self._press = getattr(device, f"{self._prop_name}", None)
        self.entity_description = entity_description
        self._availability_prop = getattr(entity_description, "availability_prop", None)

        if entity_description.translation_key is None:
            self._attr_translation_key = self.entity_description.key

        self._register_update_callback(
            entity_attr="_attr_available",
            prop_name=self._availability_prop,
            get_state=lambda state: state if state is not None else self.SkipWrite,
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if self._availability_prop is not None:
            self._device.register_state_update_callback(
                self.availability_updated,
                self._availability_prop,
            )

    async def async_will_remove_from_hass(self) -> None:
        await super().async_will_remove_from_hass()
        if self._availability_prop is not None:
            self._device.remove_state_update_callback(
                self.availability_updated,
                self._availability_prop,
            )

    @callback
    def availability_updated(self, state: bool):
        self._attr_available = state
        self.async_write_ha_state()

    async def async_press(self) -> None:
        """Handle the button press."""
        if isinstance(self._press, Callable):
            await self._press()
