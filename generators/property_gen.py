import json
import random
import uuid
from datetime import datetime, timedelta

count = 1_000
listings = []

for i in range(count):
    # 1. Randomize Location, clustered (within ~20km radius)
    centers = [
        (21.96, 96.09),   # anchor (your current main city)
        (21.70, 96.20),   # ~30–40 km away
        (22.30, 96.50),   # further
        (23.00, 97.20),   # FINAL BOSS (furthest)
    ]

    c_lat, c_lng = random.choice(centers)
    lat = c_lat + random.uniform(-0.03, 0.03)
    lng = c_lng + random.uniform(-0.03, 0.03)

    # 2. Randomize Age (0 to 30 days old)
    days_old = random.uniform(0, 30)
    created_at = (datetime.now() - timedelta(days=days_old)).isoformat()

    # 3. Boost Status (5% of posts are boosted)
    is_boosted = random.random() < 0.05
    tokens_spent = random.randint(10, 500) if is_boosted else 0
    boost_start = (datetime.now() - timedelta(hours=random.randint(0, 100))).isoformat() if is_boosted else None

    # 4. Trust & Quality
    rating = round(random.uniform(3.0, 5.0), 1)
    is_verified = random.random() < 0.30

    # 5. Features (For Implicit/Explicit match)
    property_type = random.choice(["condo", "house", "apartment", "land"])
    transcation_type = random.choice(["rent", "buy"])
    price = random.randint(200_000, 5_000_000_000)

    listing = {
        "id": str(uuid.uuid4())[:8],
        "title": f"Property {i} - {property_type.capitalize()}",
        "lat": lat,
        "lng": lng,
        "created_at": created_at,
        "price": price,
        "property_type": property_type,
        "transaction_type": transcation_type,
        "trust": {
            "rating": rating,
            "verified": is_verified
        },
        "boost": {
            "active": is_boosted,
            "tokens": tokens_spent,
            "start_time": boost_start,
            "duration_hours": 72
        }
    }
    listings.append(listing)

with open('./data/dummy_listings.json', 'w') as f:
    json.dump(listings, f, indent=2)

print(f"Successfully generated {count} listings in 'dummy_listings.json'")
