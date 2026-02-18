"""API client for Weight Watchers."""

from __future__ import annotations

import base64
import json
import secrets
import time
from dataclasses import dataclass
from datetime import date
from typing import Any
from urllib.parse import parse_qs, urlsplit

import aiohttp

from .const import CMX_SUMMARY_ENDPOINT, USER_AGENT, WW_PRIVACY_SETTINGS


class WeightWatchersError(Exception):
    """Base integration error."""


class WeightWatchersAuthError(WeightWatchersError):
    """Authentication failed."""


class WeightWatchersConnectionError(WeightWatchersError):
    """Connection or timeout error."""


@dataclass(slots=True, frozen=True)
class WeightWatchersPointsSnapshot:
    """Points data returned by the WW My Day summary endpoint."""

    daily_points_remaining: int | None
    daily_points_used: int | None
    daily_activity_points_earned: int | None
    weekly_points_remaining: int | None
    raw_details: dict[str, Any]


class WeightWatchersApiClient:
    """Async client for Weight Watchers web APIs."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        region_domain: str,
        username: str,
        password: str,
    ) -> None:
        self._session = session
        self._region_domain = region_domain
        self._username = username
        self._password = password

        self._id_token: str | None = None
        self._id_token_exp: int | None = None

    async def async_validate_credentials(self) -> WeightWatchersPointsSnapshot:
        """Validate credentials by authenticating and fetching today's summary."""
        return await self.async_get_points_summary()

    async def async_get_points_summary(
        self, target_date: date | None = None
    ) -> WeightWatchersPointsSnapshot:
        """Fetch My Day points summary for a date."""
        if target_date is None:
            target_date = date.today()

        await self._async_ensure_id_token()

        try:
            return await self._async_fetch_my_day_summary(target_date)
        except WeightWatchersAuthError:
            await self._async_ensure_id_token(force=True)
            return await self._async_fetch_my_day_summary(target_date)

    async def _async_ensure_id_token(self, force: bool = False) -> None:
        if not force and self._id_token and self._token_is_valid(self._id_token_exp):
            return

        session_token = await self._async_authenticate_login_api()
        id_token = await self._async_exchange_for_id_token(session_token)

        self._id_token = id_token
        self._id_token_exp = self._extract_jwt_exp(id_token)

    async def _async_authenticate_login_api(self) -> str:
        url = f"{self._auth_base_url}/login-apis/v1/authenticate"
        payload = {
            "username": self._username,
            "password": self._password,
            "rememberMe": True,
            "usernameEncoded": False,
            "retry": False,
        }
        headers = {
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            async with self._session.post(
                url, json=payload, headers=headers, timeout=20
            ) as response:
                if response.status == 401:
                    raise WeightWatchersAuthError(
                        "Invalid username, password, or region"
                    )
                if response.status >= 400:
                    raise WeightWatchersError(
                        f"Login API request failed with status {response.status}"
                    )

                body = await response.json(content_type=None)
        except (TimeoutError, aiohttp.ClientError) as err:
            raise WeightWatchersConnectionError(
                "Unable to reach Weight Watchers login API"
            ) from err

        token_id = body.get("data", {}).get("tokenId")
        if not token_id:
            raise WeightWatchersAuthError(
                "Login response did not include session token"
            )

        return token_id

    async def _async_exchange_for_id_token(self, session_token: str) -> str:
        url = f"{self._auth_base_url}/openam/oauth2/authorize"

        params = {
            "response_type": "id_token",
            "client_id": "webCMX",
            "scope": "openid session",
            "redirect_uri": f"{self._cmx_base_url}/auth",
            "nonce": secrets.token_hex(16),
            "state": f"{self._cmx_base_url}/",
        }

        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
        }

        try:
            async with self._session.get(
                url,
                params=params,
                headers=headers,
                cookies={"wwAuth2": session_token},
                allow_redirects=False,
                timeout=20,
            ) as response:
                if response.status in (401, 403):
                    raise WeightWatchersAuthError("Failed to authorize WW session")
                if response.status not in (301, 302):
                    raise WeightWatchersError(
                        f"Authorize request failed with status {response.status}"
                    )

                redirect_url = response.headers.get("Location", "")
        except (TimeoutError, aiohttp.ClientError) as err:
            raise WeightWatchersConnectionError(
                "Unable to reach Weight Watchers auth API"
            ) from err

        query = parse_qs(urlsplit(redirect_url).fragment)
        id_token = query.get("id_token", [None])[0]
        if not id_token:
            raise WeightWatchersAuthError("Authorize response did not include id_token")

        return id_token

    async def _async_fetch_my_day_summary(
        self, target_date: date
    ) -> WeightWatchersPointsSnapshot:
        if not self._id_token:
            raise WeightWatchersAuthError("Missing session token")

        endpoint = CMX_SUMMARY_ENDPOINT.format(date=target_date.isoformat())
        url = f"{self._cmx_base_url}{endpoint}"

        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        }
        cookies = {
            "wwSession": self._id_token,
            "ww_privacy_settings": WW_PRIVACY_SETTINGS,
        }

        try:
            async with self._session.get(
                url,
                params={"useHTS": "false", "useRounded": "false"},
                headers=headers,
                cookies=cookies,
                timeout=20,
            ) as response:
                if response.status in (401, 403):
                    raise WeightWatchersAuthError("WW session is no longer valid")
                if response.status >= 400:
                    raise WeightWatchersError(
                        f"My Day request failed with status {response.status}"
                    )

                body = await response.json(content_type=None)
        except (TimeoutError, aiohttp.ClientError) as err:
            raise WeightWatchersConnectionError(
                "Unable to reach Weight Watchers CMX API"
            ) from err

        details = body.get("pointsDetails")
        if not isinstance(details, dict):
            raise WeightWatchersError(
                "Unexpected My Day response: missing pointsDetails"
            )

        return WeightWatchersPointsSnapshot(
            daily_points_remaining=self._as_int(details.get("dailyPointsRemaining")),
            daily_points_used=self._as_int(details.get("dailyPointsUsed")),
            daily_activity_points_earned=self._as_int(
                details.get("dailyActivityPointsEarned")
            ),
            weekly_points_remaining=self._as_int(
                details.get("weeklyPointAllowanceRemaining")
            ),
            raw_details=details,
        )

    @property
    def _auth_base_url(self) -> str:
        return f"https://auth.{self._region_domain}"

    @property
    def _cmx_base_url(self) -> str:
        return f"https://cmx.{self._region_domain}"

    @staticmethod
    def _token_is_valid(expiration_epoch: int | None) -> bool:
        if expiration_epoch is None:
            return False
        return int(time.time()) < expiration_epoch - 60

    @staticmethod
    def _extract_jwt_exp(token: str) -> int | None:
        try:
            payload = token.split(".")[1]
            payload += "=" * (-len(payload) % 4)
            data = json.loads(base64.urlsafe_b64decode(payload.encode("utf-8")))
            exp = data.get("exp")
            return int(exp) if exp is not None else None
        except Exception:
            return None

    @staticmethod
    def _as_int(value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
