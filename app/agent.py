# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory.vertex_ai_memory_bank_service import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools.load_memory_tool import LoadMemoryTool
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from app.a2ui_utils import a2ui_callback

# Build A2UI System Prompt using A2uiSchemaManager (version 0.8) and BasicCatalog
schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

a2ui_instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are a Smart Travel Concierge assistant. Help users discover travel destinations, "
        "generate travel destination images/postcards, generate travel destination video previews, geocode addresses, find nearby places, "
        "check weather, plan itineraries, calculate budgets, convert currency, and manage their catalog. "
        "You can also safely execute Python code in a sandbox to perform calculations or data processing. "
        "ALWAYS call remember_user_allergy whenever the user mentions any food, environmental, or medical allergy or dietary restriction so it is safely stored in long-term memory. "
        "ALWAYS call remember_travel_preference whenever the user shares travel preferences (e.g. nature, quiet spots, budget limits, accommodation or dining choices). "
        "Use memory tools (PreloadMemoryTool, LoadMemoryTool) to recall past preferences and allergy constraints when making travel or dining recommendations."
    ),
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        '{"Image": {"url": {"literalString": "https://..."}}}. Never point an '
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)

# Configure Memory Service for deployment
MEMORY_BANK_ENGINE_ID = "3678730611050151936"
memory_service = VertexAiMemoryBankService(
    project="qwiklabs-gcp-02-3a45c164a8f8",
    location="us-east1",
    agent_engine_id=MEMORY_BANK_ENGINE_ID,
)

# Load Agent Engine Sandbox Code Executor from deployment_metadata.json
metadata_path = Path(__file__).parent.parent / "deployment_metadata.json"
code_executor = None

if metadata_path.exists():
    try:
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
        sandbox_resource = metadata.get("sandbox_resource_name")
        agent_engine_resource = metadata.get("remote_agent_runtime_id")

        if sandbox_resource:
            code_executor = AgentEngineSandboxCodeExecutor(
                sandbox_resource_name=sandbox_resource
            )
        elif agent_engine_resource:
            code_executor = AgentEngineSandboxCodeExecutor(
                agent_engine_resource_name=agent_engine_resource
            )
    except Exception as e:
        print(f"Warning: Failed to load sandbox code executor: {e}")

if code_executor is None:
    code_executor = AgentEngineSandboxCodeExecutor()


def get_weather(query: str) -> str:
    """Simulates a web search. Use it get information on weather.

    Args:
        query: A string containing the location to get weather information for.

    Returns:
        A string with the simulated weather information for the queried location.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        city: The name of the city to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


from app.tools import (
    add_destination,
    calculate_trip_budget,
    convert_currency,
    create_itinerary_plan,
    find_nearby_places,
    generate_destination_image,
    generate_destination_video,
    geocode_address,
    get_destination_details,
    get_real_city_weather,
    remember_travel_preference,
    remember_user_allergy,
    search_destinations,
)

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=a2ui_instruction,
    code_executor=code_executor,
    after_model_callback=a2ui_callback,
    tools=[
        get_weather,
        get_current_time,
        search_destinations,
        get_destination_details,
        add_destination,
        calculate_trip_budget,
        create_itinerary_plan,
        convert_currency,
        get_real_city_weather,
        geocode_address,
        find_nearby_places,
        generate_destination_image,
        generate_destination_video,
        remember_travel_preference,
        remember_user_allergy,
        PreloadMemoryTool(),
        LoadMemoryTool(),
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
