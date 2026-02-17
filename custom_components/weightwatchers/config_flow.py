"""Config flow for WeightWatchers."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    WeightWatchersApiClient,
    WeightWatchersAuthError,
    WeightWatchersConnectionError,
    WeightWatchersError,
)
from .const import CONF_REGION, DEFAULT_REGION, DOMAIN, REGION_TO_DOMAIN


def _entry_unique_id(region: str, username: str) -> str:
    return f"{region}:{username.lower()}"


class WeightWatchersConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for WeightWatchers."""

    VERSION = 1

    _reauth_entry: ConfigEntry | None = None

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> WeightWatchersOptionsFlow:
        """Return the options flow handler."""
        return WeightWatchersOptionsFlow(config_entry)

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial setup flow."""
        errors: dict[str, str] = {}

        if user_input is not None:
            region = str(user_input[CONF_REGION])
            username = str(user_input[CONF_USERNAME]).strip()
            password = str(user_input[CONF_PASSWORD])

            if await self._async_validate_input(region, username, password, errors):
                await self.async_set_unique_id(_entry_unique_id(region, username))
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"WeightWatchers ({username})",
                    data={
                        CONF_REGION: region,
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                    },
                )

            user_input = {
                CONF_REGION: region,
                CONF_USERNAME: username,
                CONF_PASSWORD: password,
            }

        return self.async_show_form(
            step_id="user",
            data_schema=self._build_user_schema(user_input),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]):
        """Start reauthentication flow."""
        self._reauth_entry = self._get_reauth_entry()
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None):
        """Handle reauthentication."""
        entry = self._reauth_entry or self._get_reauth_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            username = str(user_input[CONF_USERNAME]).strip()
            password = str(user_input[CONF_PASSWORD])
            region = str(entry.data[CONF_REGION])

            if await self._async_validate_input(region, username, password, errors):
                await self.async_set_unique_id(_entry_unique_id(region, username))
                self._abort_if_unique_id_mismatch(reason="wrong_account")

                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                    },
                )

            user_input = {
                CONF_USERNAME: username,
                CONF_PASSWORD: password,
            }

        defaults = user_input or {CONF_USERNAME: entry.data.get(CONF_USERNAME, "")}

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME, default=defaults[CONF_USERNAME]): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def _async_validate_input(
        self,
        region: str,
        username: str,
        password: str,
        errors: dict[str, str],
    ) -> bool:
        """Validate user supplied credentials."""
        region_domain = REGION_TO_DOMAIN.get(region)
        if region_domain is None:
            errors["base"] = "unknown"
            return False

        session = async_get_clientsession(self.hass)
        client = WeightWatchersApiClient(
            session=session,
            region_domain=region_domain,
            username=username,
            password=password,
        )

        try:
            await client.async_validate_credentials()
        except WeightWatchersAuthError:
            errors["base"] = "invalid_auth"
            return False
        except WeightWatchersConnectionError:
            errors["base"] = "cannot_connect"
            return False
        except WeightWatchersError:
            errors["base"] = "unknown"
            return False

        return True

    @staticmethod
    def _build_user_schema(user_input: dict[str, Any] | None) -> vol.Schema:
        """Build the user step schema."""
        defaults = user_input or {}

        return vol.Schema(
            {
                vol.Required(
                    CONF_REGION, default=defaults.get(CONF_REGION, DEFAULT_REGION)
                ): vol.In(REGION_TO_DOMAIN),
                vol.Required(
                    CONF_USERNAME, default=defaults.get(CONF_USERNAME, "")
                ): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )


class WeightWatchersOptionsFlow(OptionsFlow):
    """Handle WeightWatchers options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Manage options."""
        errors: dict[str, str] = {}
        entry_data = dict(self.config_entry.data)

        if user_input is not None:
            region = str(user_input[CONF_REGION])

            new_unique_id = _entry_unique_id(region, entry_data[CONF_USERNAME])
            for entry in self.hass.config_entries.async_entries(DOMAIN):
                if (
                    entry.entry_id != self.config_entry.entry_id
                    and entry.unique_id == new_unique_id
                ):
                    errors["base"] = "already_configured"
                    break

            if not errors:
                entry_data[CONF_REGION] = region
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data=entry_data,
                    title=f"WeightWatchers ({entry_data[CONF_USERNAME]})",
                    unique_id=new_unique_id,
                )
                await self.hass.config_entries.async_reload(self.config_entry.entry_id)
                return self.async_create_entry(title="", data={})

        defaults = user_input or {
            CONF_REGION: entry_data.get(CONF_REGION, DEFAULT_REGION),
        }

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_REGION, default=defaults[CONF_REGION]): vol.In(
                        REGION_TO_DOMAIN
                    ),
                }
            ),
            errors=errors,
        )
