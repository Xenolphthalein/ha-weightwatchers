"""Constants for the Weight Watchers integration."""

from datetime import timedelta

DOMAIN = "weight_watchers"

PLATFORMS: list[str] = ["sensor"]

CONF_REGION = "region"

DEFAULT_REGION = "US"
DEFAULT_SCAN_INTERVAL = timedelta(minutes=15)

REGION_TO_DOMAIN: dict[str, str] = {
    "AU": "weightwatchers.com.au",
    "NB": "weightwatchers.be",
    "FB": "fr.weightwatchers.be",
    "BR": "vigilantesdopeso.com.br",
    "CA": "weightwatchers.ca",
    "FC": "fr.weightwatchers.ca",
    "FR": "weightwatchers.fr",
    "DE": "weightwatchers.de",
    "NL": "weightwatchers.nl",
    "NZ": "weightwatchers.com.au",
    "SE": "viktvaktarna.se",
    "FS": "fr.weightwatchers.ch",
    "DS": "weightwatchers.ch",
    "UK": "weightwatchers.co.uk",
    "US": "weightwatchers.com",
}

CMX_SUMMARY_ENDPOINT = "/api/v4/cmx/operations/composed/members/~/my-day-summary/{date}"

WW_PRIVACY_SETTINGS = '{"doNotTrack":0,"doNotSell":0}'
USER_AGENT = "HomeAssistant-Weight-Watchers/1.0"
