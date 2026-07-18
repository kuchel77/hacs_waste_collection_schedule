import logging
from datetime import datetime, timedelta
from typing import List

from waste_collection_schedule import Collection, Icons  # type: ignore[attr-defined]
from waste_collection_schedule.exceptions import SourceArgumentNotFound
from waste_collection_schedule.service.Pozi import PoziGeoJsonError, query_geojson_zones

TITLE = "Southern Grampians Shire Council"
DESCRIPTION = "Source for Southern Grampians Shire Council rubbish collection."
URL = "https://www.sthgrampians.vic.gov.au/"

# Geographic boundaries for Southern Grampians area
STHGRAMPIANS_BOUNDS = {
    "min_lat": -38.0,
    "min_lon": 141.6,
    "max_lat": -37.2,
    "max_lon": 142.6,
}

# API endpoints
ZONES_API_URL = "https://connect.pozi.com/userdata/southerngrampians-publisher/Public/Bin_Collection_Areas.json"

# Test cases for validation
TEST_CASES = {
    "Bunnings Hamilton": {
        "latitude": -37.72206336022167,
        "longitude": 141.9938232815261,
    },
    "Maccas Hamilton": {
        "latitude": -37.74133764660676,
        "longitude": 142.02420785035088,
    },
    "Hamilton Model Railway Museum": {
        "latitude": -37.74226873047067,
        "longitude": 142.05171594397333,
    }
}

_LOGGER = logging.getLogger(__name__)

WASTE_NAMES = {"waste": "Garbage", "recycle": "Recycling", "green": "Organic"}

ICON_MAP = {"waste": Icons.GENERAL_WASTE, "recycle": Icons.RECYCLING, "green": Icons.ORGANIC }

COLLECTION_FREQUENCY = {"Weekly": 1, "Fortnightly": 2}

class Source:
    def __init__(self, latitude: float, longitude: float):
        """Initialize source with latitude and longitude coordinates.

        Args:
            latitude: Latitude coordinate (-37.07 to -36.39)
            longitude: Longitude coordinate (144.03 to 144.86)
        """
        try:
            # Convert inputs to float if they're strings
            self._latitude = float(latitude)
            self._longitude = float(longitude)

            if (
                not STHGRAMPIANS_BOUNDS["min_lat"]
                <= self._latitude
                <= STHGRAMPIANS_BOUNDS["max_lat"]
            ):
                raise SourceArgumentNotFound(
                    "latitude",
                    str(self._latitude),
                    f"Latitude must be between {STHGRAMPIANS_BOUNDS['min_lat']} and {STHGRAMPIANS_BOUNDS['max_lat']}",
                )
            if (
                not STHGRAMPIANS_BOUNDS["min_lon"]
                <= self._longitude
                <= STHGRAMPIANS_BOUNDS["max_lon"]
            ):
                raise SourceArgumentNotFound(
                    "longitude",
                    str(self._longitude),
                    f"Longitude must be between {STHGRAMPIANS_BOUNDS['min_lon']} and {STHGRAMPIANS_BOUNDS['max_lon']}",
                )
        except (ValueError, TypeError) as e:
            raise Exception(
                f"Invalid coordinate format. Please provide numeric values. Error: {str(e)}"
            )

    def fetch(self):
        try:
            zone_props = query_geojson_zones(
                ZONES_API_URL, self._latitude, self._longitude
            )
        except PoziGeoJsonError:
            raise Exception(
                f"Coordinates ({self._latitude}, {self._longitude}) not found in any Southern Grampians collection zone. "
                "Please check your location at https://www.sthgrampians.vic.gov.au/Our-Services/Waste-Recycling/Kerbside-collections",
            )

        _LOGGER.debug(
            "Found collection zone: %s",
            zone_props.get("ZoneName")
        )

        entries = []

        for i in range(3):
            date = datetime.strptime(zone_props['nextwaste'],"%Y-%m-%d").date() + timedelta(days=i*7)
            entries.append(
                Collection(
                    date=date,
                    t="Rubbish",
                    icon=ICON_MAP.get("waste"),
                )
            )

        for i in range(3):
            date = datetime.strptime(zone_props['nextrecyc'],"%Y-%m-%d").date() + timedelta(days=i*14)
            entries.append(
                Collection(
                    date=date,
                    t="Recycling",
                    icon=ICON_MAP.get("recycle"),
                )
            )


        for i in range(3):
            date = datetime.strptime(zone_props['nextgreen'],"%Y-%m-%d").date() + timedelta(days=i*14)
            entries.append(
                Collection(
                    date=date,
                    t="Green Waste",
                    icon=ICON_MAP.get("green"),
                )
            )

        _LOGGER.debug("Entries: %s", entries)

        return entries
