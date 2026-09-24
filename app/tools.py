"""Firestore-backed tools for Smart Travel Concierge."""

import json
import os
from typing import List, Optional
import urllib.parse
import urllib.request
import uuid

from google import genai
from google.adk.tools import ToolContext
from google.cloud import firestore, storage
from google.genai import types

# CRITICAL: Hardcoded GCP Project ID for Firestore client (avoids project number issues on Agent Platform)
FIRESTORE_PROJECT_ID = "qwiklabs-gcp-02-3a45c164a8f8"

# CRITICAL: Hardcoded Public GCS Bucket Name for media uploads
GCS_BUCKET_NAME = "smart-travel-concierge-media-3a45c164a8f8"


def _get_firestore_client() -> firestore.Client:
    return firestore.Client(project=FIRESTORE_PROJECT_ID)


def search_destinations(
    category: Optional[str] = None,
    max_daily_budget_usd: Optional[float] = None,
) -> List[dict]:
    """Search travel destinations from the Firestore catalog.

    Args:
        category: Optional category filter (e.g. 'Culture & History', 'Art & Culinary', 'Coastal & Tech', 'Culture & Nature').
        max_daily_budget_usd: Optional maximum average daily budget in USD.

    Returns:
        List of matching destination dictionaries from Firestore.
    """
    db = _get_firestore_client()
    docs = db.collection("destinations").stream()

    results = []
    for doc in docs:
        data = doc.to_dict()
        if category and category.lower() not in data.get("category", "").lower():
            continue
        if max_daily_budget_usd is not None and data.get("average_daily_budget_usd", 0) > max_daily_budget_usd:
            continue
        results.append(data)

    return results


def get_destination_details(destination_name: str) -> dict:
    """Get detailed information about a specific travel destination from Firestore.

    Args:
        destination_name: The name or partial name of the destination (e.g., 'Kyoto', 'Paris', 'Pune', 'San Francisco').

    Returns:
        Dictionary with destination details or an error message dict if not found.
    """
    db = _get_firestore_client()
    docs = db.collection("destinations").stream()

    for doc in docs:
        data = doc.to_dict()
        if destination_name.lower() in data.get("name", "").lower() or destination_name.lower() in doc.id.lower():
            return data

    return {"error": f"No destination found matching '{destination_name}' in the catalog."}


def add_destination(
    name: str,
    category: str,
    description: str,
    best_time_to_visit: str,
    average_daily_budget_usd: float,
    popular_attractions: List[str],
) -> dict:
    """Add a new travel destination to the Firestore catalog.

    Args:
        name: Name of the destination (e.g., 'Rome, Italy').
        category: Category of travel (e.g., 'History & Architecture').
        description: Brief overview of the destination.
        best_time_to_visit: Best seasons or months to visit.
        average_daily_budget_usd: Estimated average daily cost in USD.
        popular_attractions: List of top attractions.

    Returns:
        Confirmation dictionary with the created destination ID and status.
    """
    db = _get_firestore_client()
    doc_id = name.lower().replace(" ", "-").replace(",", "")
    doc_ref = db.collection("destinations").document(doc_id)

    data = {
        "id": doc_id,
        "name": name,
        "category": category,
        "description": description,
        "best_time_to_visit": best_time_to_visit,
        "average_daily_budget_usd": average_daily_budget_usd,
        "popular_attractions": popular_attractions,
    }
    doc_ref.set(data)
    return {"status": "success", "message": f"Successfully added '{name}' to destinations catalog.", "destination": data}


def calculate_trip_budget(
    destination_name: str,
    num_days: int,
    daily_budget_usd: float,
    estimated_flight_usd: float = 0.0,
    num_travelers: int = 1,
) -> dict:
    """Calculates estimated total budget breakdown for a trip.

    Args:
        destination_name: Name of the destination (e.g. 'Kyoto, Japan').
        num_days: Duration of the trip in days.
        daily_budget_usd: Estimated average daily expenses per person (accommodations, food, activities).
        estimated_flight_usd: Estimated round-trip flight cost per person in USD (default 0.0).
        num_travelers: Number of people traveling together (default 1).

    Returns:
        A dictionary with total group costs, per-person costs, and itemized breakdown.
    """
    daily_total_per_person = num_days * daily_budget_usd
    total_per_person = daily_total_per_person + estimated_flight_usd
    total_group_cost = total_per_person * num_travelers

    return {
        "destination": destination_name,
        "duration_days": num_days,
        "num_travelers": num_travelers,
        "breakdown_per_person": {
            "daily_expenses_total": round(daily_total_per_person, 2),
            "estimated_flight": round(estimated_flight_usd, 2),
            "total_per_person": round(total_per_person, 2),
        },
        "total_group_cost_usd": round(total_group_cost, 2),
    }


def create_itinerary_plan(
    destination_name: str,
    num_days: int = 3,
) -> dict:
    """Generates a day-by-day travel itinerary schedule for a destination.

    Args:
        destination_name: Name of the destination (e.g. 'Kyoto', 'Paris', 'Pune', 'San Francisco').
        num_days: Duration of the itinerary in days (default 3).

    Returns:
        A dictionary with day-by-day morning, afternoon, and evening activity plans.
    """
    dest_details = get_destination_details(destination_name)
    attractions = dest_details.get(
        "popular_attractions", ["Historic City Center", "Local Food Market", "Scenic Viewpoint"]
    )

    itinerary_days = []
    for day in range(1, num_days + 1):
        attraction_1 = attractions[(day - 1) % len(attractions)]
        attraction_2 = attractions[day % len(attractions)]
        itinerary_days.append({
            "day": day,
            "morning": f"Explore {attraction_1} and surrounding area",
            "afternoon": f"Local lunch & visit {attraction_2}",
            "evening": "Dinner at a local restaurant & evening leisure stroll",
        })

    return {
        "destination": dest_details.get("name", destination_name),
        "total_days": num_days,
        "itinerary": itinerary_days,
    }


def convert_currency(
    amount_usd: float,
    target_currency: str,
) -> dict:
    """Converts a USD amount into a target foreign currency.

    Args:
        amount_usd: Amount in USD to convert.
        target_currency: 3-letter currency code (e.g. 'EUR', 'JPY', 'INR', 'GBP', 'CAD', 'AUD').

    Returns:
        A dictionary with exchange rate and converted currency details.
    """
    exchange_rates = {
        "USD": 1.0,
        "EUR": 0.92,
        "JPY": 155.0,
        "INR": 83.5,
        "GBP": 0.78,
        "CAD": 1.36,
        "AUD": 1.50,
    }

    target_code = target_currency.upper().strip()
    rate = exchange_rates.get(target_code)

    if rate is None:
        return {
            "error": f"Unsupported currency '{target_currency}'. Supported currencies: {list(exchange_rates.keys())}"
        }

    return {
        "amount_usd": round(amount_usd, 2),
        "target_currency": target_code,
        "exchange_rate": rate,
        "converted_amount": round(amount_usd * rate, 2),
    }


def get_real_city_weather(city_name: str) -> dict:
    """Fetches real-time weather information for any destination city using the Open-Meteo public API.

    Args:
        city_name: Name of the destination city (e.g. 'Kyoto', 'Paris', 'Pune', 'San Francisco').

    Returns:
        A dictionary with real-time temperature (Celsius and Fahrenheit), wind speed, country, and timezone.
    """
    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(city_name)}&count=1&language=en&format=json"
        req = urllib.request.Request(geo_url, headers={"User-Agent": "Antigravity/1.0"})
        with urllib.request.urlopen(req) as response:
            geo_data = json.loads(response.read().decode())

        results = geo_data.get("results")
        if not results:
            return {"error": f"Could not find coordinates for city '{city_name}'."}

        city_info = results[0]
        lat = city_info["latitude"]
        lon = city_info["longitude"]
        country = city_info.get("country", "")
        timezone = city_info.get("timezone", "")

        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        req_weather = urllib.request.Request(weather_url, headers={"User-Agent": "Antigravity/1.0"})
        with urllib.request.urlopen(req_weather) as response:
            weather_data = json.loads(response.read().decode())

        current = weather_data.get("current_weather", {})
        temp_c = current.get("temperature", 0.0)
        temp_f = round((temp_c * 9 / 5) + 32, 1)

        return {
            "city": city_info.get("name", city_name),
            "country": country,
            "timezone": timezone,
            "temperature_celsius": temp_c,
            "temperature_fahrenheit": temp_f,
            "windspeed_kmh": current.get("windspeed", 0.0),
            "is_daytime": bool(current.get("is_day", 1)),
        }
    except Exception as e:
        return {"error": f"Failed to fetch real-time weather data for '{city_name}': {str(e)}"}


def geocode_address(address: str) -> dict:
    """Uses Google Maps Geocoding API to convert a location name or address into geographic coordinates.

    Args:
        address: The location name or address (e.g., 'Kyoto Station', '1600 Amphitheatre Pkwy, Mountain View, CA').

    Returns:
        A dictionary with formatted address and location coordinates (latitude and longitude).
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return {"error": "GOOGLE_MAPS_API_KEY environment variable is not set."}

    try:
        url = f"https://maps.googleapis.com/maps/api/geocode/json?address={urllib.parse.quote(address)}&key={api_key}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())

        results = data.get("results")
        if not results:
            return {"error": f"No geocoding results found for address '{address}'."}

        first_result = results[0]
        formatted_address = first_result.get("formatted_address", address)
        location = first_result.get("geometry", {}).get("location", {})

        return {
            "name": address,
            "address": formatted_address,
            "location": {
                "latitude": location.get("lat"),
                "longitude": location.get("lng"),
            },
        }
    except Exception as e:
        return {"error": f"Failed to geocode address '{address}': {str(e)}"}


def find_nearby_places(
    latitude: float,
    longitude: float,
    place_type: str = "restaurant",
    radius_meters: float = 1000.0,
) -> dict:
    """Uses Google Places API (New) to search for nearby places of a given type around a coordinate center.

    Args:
        latitude: Latitude of the search center.
        longitude: Longitude of the search center.
        place_type: Type of place to search (e.g., 'restaurant', 'cafe', 'tourist_attraction', 'museum', 'lodging').
        radius_meters: Search radius in meters (default 1000.0).

    Returns:
        A dictionary with a list of nearby places with name, address, and location coordinates.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return {"error": "GOOGLE_MAPS_API_KEY environment variable is not set."}

    try:
        url = "https://places.googleapis.com/v1/places:searchNearby"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location",
        }
        body = {
            "includedTypes": [place_type],
            "maxResultCount": 5,
            "locationRestriction": {
                "circle": {
                    "center": {
                        "latitude": latitude,
                        "longitude": longitude,
                    },
                    "radius": radius_meters,
                }
            },
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())

        places = data.get("places", [])
        results = []
        for p in places:
            display_name = p.get("displayName", {}).get("text", "")
            address = p.get("formattedAddress", "")
            loc = p.get("location", {})
            results.append({
                "name": display_name,
                "address": address,
                "location": {
                    "latitude": loc.get("latitude"),
                    "longitude": loc.get("longitude"),
                },
            })

        return {
            "search_center": {"latitude": latitude, "longitude": longitude},
            "place_type": place_type,
            "places": results,
        }
    except Exception as e:
        return {"error": f"Failed to search nearby places: {str(e)}"}


async def generate_destination_image(prompt: str, tool_context: ToolContext) -> dict:
    """Generates an image for a travel destination using gemini-3.1-flash-lite-image in the global region.

    Saves the image as an ADK artifact and uploads it directly to the public Cloud Storage bucket.

    Args:
        prompt: Description of the travel destination scene, postcard, or attraction to generate.

    Returns:
        A dictionary with the prompt, saved artifact filename, and public GCS HTTPS URL.
    """
    try:
        client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT_ID, location="global")
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"]
            ),
        )

        image_bytes = None
        mime_type = "image/jpeg"
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                image_bytes = part.inline_data.data
                if part.inline_data.mime_type:
                    mime_type = part.inline_data.mime_type
                break

        if not image_bytes:
            return {"error": "Model response did not contain image data."}

        ext = "png" if "png" in mime_type else "jpg"
        unique_id = uuid.uuid4().hex[:8]
        filename = f"destination_{unique_id}.{ext}"

        # 1. Save as artifact so it appears in Playground Artifacts panel
        artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        await tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # 2. Upload image bytes directly to public GCS bucket
        storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob_name = f"images/{filename}"
        blob = bucket.blob(blob_name)
        blob.upload_from_string(image_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{blob_name}"

        return {
            "status": "success",
            "prompt": prompt,
            "artifact_filename": filename,
            "image_url": public_url,
        }
    except Exception as e:
        return {"error": f"Failed to generate destination image: {str(e)}"}


async def generate_destination_video(prompt: str, tool_context: ToolContext) -> dict:
    """Generates a short video preview for a travel destination or attraction using Google's Omni model (gemini-omni-flash-preview) in the global region.

    Saves the generated video as an ADK artifact and uploads it directly to the public Cloud Storage bucket.

    Args:
        prompt: Description of the travel scene, destination preview, or attraction video to generate.

    Returns:
        A dictionary with the prompt, saved artifact filename, and public GCS HTTPS URL.
    """
    try:
        import base64
        client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT_ID, location="global")
        response = client.interactions.create(
            model="gemini-omni-flash-preview",
            input=prompt,
            response_modalities=["text", "video"],
        )

        video_data = getattr(getattr(response, "output_video", None), "data", None)
        if not video_data:
            return {"error": "Model response did not contain video data."}

        if isinstance(video_data, str):
            video_bytes = base64.b64decode(video_data)
        elif isinstance(video_data, bytes):
            video_bytes = video_data
        else:
            return {"error": f"Unexpected video data format: {type(video_data)}"}

        unique_id = uuid.uuid4().hex[:8]
        filename = f"destination_video_{unique_id}.mp4"

        # 1. Save as artifact so it appears in Playground Artifacts panel
        artifact_part = types.Part.from_bytes(data=video_bytes, mime_type="video/mp4")
        await tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # 2. Upload video bytes directly to public GCS bucket
        storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob_name = f"videos/{filename}"
        blob = bucket.blob(blob_name)
        blob.upload_from_string(video_bytes, content_type="video/mp4")

        public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{blob_name}"

        return {
            "status": "success",
            "prompt": prompt,
            "artifact_filename": filename,
            "video_url": public_url,
        }
    except Exception as e:
        return {"error": f"Failed to generate destination video: {str(e)}"}



async def remember_travel_preference(preference: str, tool_context: ToolContext) -> str:
    """Saves a user's travel preference to their long-term Memory Bank.

    Args:
        preference: The travel preference or detail to remember (e.g. 'Prefers nature & quiet places', 'Budget under $2000', 'Loves vegetarian street food').

    Returns:
        Confirmation message that the preference was saved.
    """
    try:
        from google.adk.memory.memory_entry import MemoryEntry
        entry = MemoryEntry(
            content=types.Content(parts=[types.Part.from_text(text=preference)])
        )
        await tool_context.add_memory(memories=[entry])
        return f"Successfully saved travel preference to long-term memory: '{preference}'"
    except Exception as e:
        return f"Logged preference in context. Note: memory service response: {e}"


async def remember_user_allergy(allergy: str, tool_context: ToolContext) -> str:
    """Saves a user's allergy or dietary restriction (e.g., 'Peanut allergy', 'Lactose intolerant', 'Gluten sensitivity', 'Shellfish allergy') to their long-term Memory Bank.

    Args:
        allergy: The allergy or dietary restriction details to remember.

    Returns:
        Confirmation message that the allergy was saved to long-term memory.
    """
    try:
        from google.adk.memory.memory_entry import MemoryEntry
        entry = MemoryEntry(
            content=types.Content(parts=[types.Part.from_text(text=f"User Allergy / Dietary Restriction: {allergy}")])
        )
        await tool_context.add_memory(memories=[entry])
        return f"Successfully saved allergy information to long-term memory: '{allergy}'"
    except Exception as e:
        return f"Logged allergy in context. Note: memory service response: {e}"
