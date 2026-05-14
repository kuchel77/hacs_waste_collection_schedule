import logging
from datetime import datetime, timedelta
from typing import List

from waste_collection_schedule import Collection  # type: ignore[attr-defined]
from waste_collection_schedule.exceptions import SourceArgumentNotFound
from waste_collection_schedule.service.Pozi import PoziGeoJsonError, query_geojson_zones

TITLE = "Southern Grampians Shire Council"
DESCRIPTION = "Source for Southern Grampians Shire Council rubbish collection."
URL = "https://www.sthgrampians.vic.gov.au/"

# Geographic boundaries for Southern Grampians area
STHGRAMPIANS_BOUNDS = {
    "min_lat": -37.9,
    "min_lon": 142.6,
    "max_lat": -37.2,
    "max_lon": 141.4,
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

ICON_MAP = {"waste": "mdi:trash-can", "recycle": "mdi:recycle", "green": "mdi:leaf"}

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
            zone_props.get("Collection Reference"),
        )

        entries = []

        Source.__add_collection(
            zone_props.get("Collection Reference"),
            zone_props.get("Collection Day"),
            COLLECTION_FREQUENCY.get(zone_props.get("General Waste Frequency"), 0),
            zone_props.get("Next General Waste Pickup"),
            "waste",
            entries,
        )

        Source.__add_collection(
            zone_props.get("Collection Reference"),
            zone_props.get("Collection Day"),
            COLLECTION_FREQUENCY.get(zone_props.get("Recycling Frequency"), 0),
            zone_props.get("Next Recycling Pickup"),
            "recycle",
            entries,
        )

        Source.__add_collection(
            zone_props.get("Collection Reference"),
            zone_props.get("Collection Day"),
            COLLECTION_FREQUENCY.get(zone_props.get("Organics Frequency"), 0),
            zone_props.get("Next Organics Pickup"),
            "green",
            entries,
        )

        _LOGGER.debug("Entries: %s", entries)

        return entries

    @staticmethod
    def __add_collection(
        desc: str,
        day: str,
        weeks: int,
        start: str,
        collection_type: str,
        entries: List[Collection],
    ):
        if not desc:
            raise ValueError(
                f"Missing description for {WASTE_NAMES[collection_type]} collection"
            )

        if not start:
            raise ValueError(
                f"Missing start date for {WASTE_NAMES[collection_type]} collection"
            )

        if not day:
            raise ValueError(
                f"Missing collection day for {WASTE_NAMES[collection_type]} collection"
            )

        if not weeks or weeks < 1:
            raise ValueError(
                f"Invalid collection frequency for {WASTE_NAMES[collection_type]} collection"
            )

        try:
            start_date = datetime.strptime(start.strip(), "%d-%b-%Y").date()

            start_day = start_date.strftime("%A")

            # If the start date isn't on the specified day, find the next occurrence
            if start_day != day:
                days_ahead = [
                    "Monday",
                    "Tuesday",
                    "Wednesday",
                    "Thursday",
                    "Friday",
                    "Saturday",
                    "Sunday",
                ].index(day) - [
                    "Monday",
                    "Tuesday",
                    "Wednesday",
                    "Thursday",
                    "Friday",
                    "Saturday",
                    "Sunday",
                ].index(
                    start_day
                )
                if days_ahead <= 0:
                    days_ahead += 7
                start_date = start_date + timedelta(days=days_ahead)

            current_date = start_date
            end_date = datetime.now().date() + timedelta(days=365)

            while current_date <= end_date:
                entries.append(
                    Collection(
                        date=current_date,
                        t=WASTE_NAMES[collection_type],
                        icon=ICON_MAP[collection_type],
                    )
                )

                current_date = current_date + timedelta(weeks=weeks)

        except ValueError as e:
            raise ValueError(
                f"Invalid date format for {WASTE_NAMES[collection_type]} collection: {start}"
            ) from e
