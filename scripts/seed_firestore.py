"""Seed script for populating the Firestore 'destinations' collection."""

from google.cloud import firestore

# CRITICAL: Hardcoded project ID (do NOT use google.auth.default() or GOOGLE_CLOUD_PROJECT)
PROJECT_ID = "qwiklabs-gcp-02-3a45c164a8f8"

SEED_DESTINATIONS = [
    {
        "id": "kyoto-japan",
        "name": "Kyoto, Japan",
        "category": "Culture & History",
        "description": "Japan's cultural heart filled with classical Buddhist temples, gardens, imperial palaces, and traditional wooden houses.",
        "best_time_to_visit": "Spring (March-May) & Autumn (October-November)",
        "average_daily_budget_usd": 180,
        "popular_attractions": ["Fushimi Inari Shrine", "Arashiyama Bamboo Grove", "Kinkaku-ji (Golden Pavilion)"],
    },
    {
        "id": "paris-france",
        "name": "Paris, France",
        "category": "Art & Culinary",
        "description": "The City of Light, world-renowned for art, gastronomy, fashion, and iconic landmarks.",
        "best_time_to_visit": "Spring (June-August) & Autumn (September-October)",
        "average_daily_budget_usd": 240,
        "popular_attractions": ["Eiffel Tower", "Louvre Museum", "Notre-Dame Cathedral", "Montmartre"],
    },
    {
        "id": "san-francisco-usa",
        "name": "San Francisco, USA",
        "category": "Coastal & Tech",
        "description": "A vibrant coastal hub known for the Golden Gate Bridge, steep rolling hills, and tech innovation.",
        "best_time_to_visit": "September-November",
        "average_daily_budget_usd": 260,
        "popular_attractions": ["Golden Gate Bridge", "Alcatraz Island", "Fisherman's Wharf"],
    },
    {
        "id": "pune-india",
        "name": "Pune, India",
        "category": "Culture & Nature",
        "description": "The cultural capital of Maharashtra, surrounded by green hills, historic forts, and rich heritage.",
        "best_time_to_visit": "October-March",
        "average_daily_budget_usd": 60,
        "popular_attractions": ["Shaniwar Wada", "Aga Khan Palace", "Sinhagad Fort"],
    },
]

def seed_firestore():
    db = firestore.Client(project=PROJECT_ID)
    collection_ref = db.collection("destinations")
    print(f"Seeding Firestore collection 'destinations' in project '{PROJECT_ID}'...")

    for item in SEED_DESTINATIONS:
        doc_id = item["id"]
        doc_ref = collection_ref.document(doc_id)
        doc_ref.set(item)
        print(f"  ✓ Added/updated destination: {item['name']} ({doc_id})")

    print("Seeding complete!")

if __name__ == "__main__":
    seed_firestore()
