import json
from urllib.parse import quote

import httpx
from django.conf import settings
from pydantic import Field

from pyhub.mcptools import mcp
from pyhub.mcptools.maps.types import (
    NaverMapCarTypes,
    NaverMapFuelTypes,
    NaverMapGeocodingResponseLanguages,
    NaverMapResponseLanguages,
    NaverMapRouteOptions,
)

ENABLED_MAPS_NAVER_TOOLS = settings.NAVER_MAP_CLIENT_ID and settings.NAVER_MAP_CLIENT_SECRET

NAVER_MAP_HEADERS = {
    "X-NCP-APIGW-API-KEY-ID": settings.NAVER_MAP_CLIENT_ID,
    "X-NCP-APIGW-API-KEY": settings.NAVER_MAP_CLIENT_SECRET,
}


@mcp.tool(enabled=ENABLED_MAPS_NAVER_TOOLS)
async def maps__naver_geocode(
    query: str = Field(
        ...,
        description="""
            Address to geocode. Must be a legal (법정동) or administrative (행정동) address.
            Place names or points of interest (e.g., "강남역", "코엑스") are not supported.
            Both full addresses and partial addresses work:
                - Full address: "경기도 성남시 분당구 불정로 6"
                - Partial address: "불정로 6" or "분당구 불정로 6"
        """,
        examples=[
            "불정로 6",  # 부분 주소
            "분당구 불정로 6",  # 구+도로명
            "경기도 성남시 분당구 불정로 6",  # 전체 주소
        ],
    ),
    coordinate: str = Field(
        "",
        description="Coordinates for coordinate-based search (longitude,latitude). Optional.",
        examples=["127.1054328,37.3595963"],
    ),
    language: str = Field(
        NaverMapGeocodingResponseLanguages.KOREAN,
        description=NaverMapGeocodingResponseLanguages.get_description("Response language"),
    ),
) -> str:
    """
    Geocode an address using Naver Maps Geocoding API.
    Converts Korean addresses to coordinates.

    Returns:
        str: JSON response containing:
            - response: Original geocoding results including coordinates and address details
            - map_urls: Direct links to open the location in various map services:
                - google: Google Maps link
                - naver: Naver Maps link
                - kakao: Kakao Maps link
              These URLs can be used to instantly open the location in the respective map service's web interface.

    Note:
        - This API works best with Korean addresses.
        - Only legal (법정동) or administrative (행정동) addresses are supported.
        - The coordinate parameter can be used to improve search accuracy in specific areas.
        - Place names, landmarks, or business names will not return results.
        - You can use either full addresses or partial addresses. When using partial addresses,
          the API will attempt to find the best match, but may return multiple results.
        - The returned map_urls provide convenient direct links to view the location
          in Google Maps, Naver Maps, or Kakao Maps without additional steps.
    """
    api_url = "https://naveropenapi.apigw.ntruss.com/map-geocode/v2/geocode"
    params = {
        "query": query,
        "language": language,
    }

    if coordinate:
        params["coordinate"] = coordinate

    async with httpx.AsyncClient() as client:
        res = await client.get(api_url, headers=NAVER_MAP_HEADERS, params=params)
        obj = res.json()

        if len(obj["addresses"]) > 0:
            address = obj["addresses"][0]
            title = quote(query)
            lat, lng = address["y"], address["x"]
            map_urls = {
                # https://developers.google.com/maps/architecture/maps-url?authuser=1&hl=ko
                "google": f"https://www.google.com/maps/search/?api=1&query={lat},{lng}",
                # https://www.ncloud-forums.com/topic/242/
                "naver": f"https://map.naver.com/?lng={lng}&lat={lat}&title={title}",
                "kakao": f"https://map.kakao.com/link/map/{title},{lat},{lng}",
            }
        else:
            map_urls = {}

        return json.dumps(
            {
                "response": obj,
                "map_urls": map_urls,
            },
            ensure_ascii=False,
        )


@mcp.tool(enabled=ENABLED_MAPS_NAVER_TOOLS)
async def maps__naver_route(
    start_lnglat: str = Field(
        ...,
        description="Starting point coordinates in longitude,latitude format (Must be within South Korea)",
        examples=["127.027619,37.497952"],
    ),
    goal_lnglat: str = Field(
        ...,
        description="Destination coordinates in longitude,latitude format (Must be within South Korea)",
        examples=["126.92361,37.55667"],
    ),
    waypoints: str = Field(
        "",
        description=(
            "Up to 5 waypoint coordinates separated by '|'. "
            "Each waypoint should be in 'longitude,latitude' format. "
            "Example format: 'lng1,lat1|lng2,lat2|lng3,lat3'. "
            "Must be within South Korea (longitude: 124-132°E, latitude: 33-39°N)."
        ),
        examples=[
            "127.12345,37.12345",
            "127.12345,37.12345|128.12345,38.12345|127.98765,37.87654",
        ],
    ),
    option: str = Field(
        NaverMapRouteOptions.FASTEST,
        description=NaverMapRouteOptions.get_description("Route search option"),
    ),
    cartype: int = Field(
        NaverMapCarTypes.GENERIC_CAR,
        description=NaverMapCarTypes.get_description(
            f"Car type for toll fee calculation. "
            f"Use {NaverMapCarTypes.GENERIC_CAR} for all regular passenger vehicles."
        ),
    ),
    fueltype: str = Field(
        NaverMapFuelTypes.GASOLINE,
        description=NaverMapFuelTypes.get_description("Fuel type"),
    ),
    mileage: float = Field(
        14,
        description="Vehicle fuel efficiency in km/L (kilometers per liter)",
    ),
    lang: str = Field(
        NaverMapResponseLanguages.KOREAN,
        description=NaverMapResponseLanguages.get_description("Response language"),
    ),
) -> str:
    """
    Get driving directions between two points using Naver Maps Direction API.
    Only supports locations within South Korea.

    Returns:
        str: JSON response containing route information

    Note:
        This API only works for coordinates within South Korea.
        Typical coordinate ranges for South Korea:
        - Latitude: 33° to 39° N (33.0 to 39.0)
        - Longitude: 124° to 132° E (124.0 to 132.0)
    """

    api_url = "https://naveropenapi.apigw.ntruss.com/map-direction/v1/driving"
    params = {
        "start": start_lnglat,
        "goal": goal_lnglat,
        "option": option,
        "cartype": cartype,
        "fueltype": fueltype,
        "mileage": mileage,
        "lang": lang,
    }

    if waypoints:
        if len(waypoints.split("|")) > 5:
            raise ValueError("Maximum 5 waypoints are allowed")
        params["waypoints"] = "|".join(waypoints)

    async with httpx.AsyncClient() as client:
        res = await client.get(api_url, headers=NAVER_MAP_HEADERS, params=params)
        return res.text
