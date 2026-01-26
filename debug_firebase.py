import requests
import csv

FIREBASE_DB_URL = "https://strategyscience2026-default-rtdb.firebaseio.com"

print("Checking Firebase...")
try:
    resp = requests.get(f"{FIREBASE_DB_URL}/reviewers.json", timeout=10)
    print(f"Status: {resp.status_code}")
    print(f"Content: {resp.text[:500]}")
    data = resp.json()
    print(f"Parsed Count: {len(data) if data else 0}")
except Exception as e:
    print(f"Error: {e}")

print("\nChecking papers_real.csv...")
try:
    with open("papers_real.csv", "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        print(f"Row count: {len(rows)}")
        ids = [r['id'] for r in rows]
        print(f"IDs: {ids}")
except Exception as e:
    print(f"Error: {e}")
