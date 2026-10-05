"""
Five quick checks against the Open Charge Map API.
Usage:
    export OCM_API_KEY="your-key"
    python scripts/check_api.py
"""
import os
import sys
import time

import requests

BASE_URL = "https://api.openchargemap.io/v3/poi/"
API_KEY = os.environ.get("OCM_API_KEY")
if not API_KEY:
    sys.exit('Set your key first:  export OCM_API_KEY="your-key"')

results = []


def get(params, key=API_KEY):
    query = {"output": "json", **params}
    if key:
        query["key"] = key
    return requests.get(BASE_URL, params=query, timeout=30)


def check(name, passed, detail=""):
    results.append(passed)
    print(f"[{'PASS' if passed else 'FAIL'}] {name}" + (f"  ({detail})" if detail else ""))


# 1. A valid search returns 200 and a non-empty list
r = get({"countrycode": "IN", "maxresults": 10})
data = r.json() if r.status_code == 200 else []
check("Valid search returns 200 and a non-empty list",
      r.status_code == 200 and isinstance(data, list) and len(data) > 0,
      f"status={r.status_code}, results={len(data)}")

# 2. maxresults is respected
r = get({"countrycode": "IN", "maxresults": 5})
data = r.json() if r.status_code == 200 else []
check("maxresults=5 returns at most 5 results", r.status_code == 200 and len(data) <= 5,
      f"results={len(data)}")

# 3. Country filter is respected
r = get({"countrycode": "IN", "maxresults": 50})
data = r.json() if r.status_code == 200 else []
wrong = [p["ID"] for p in data
         if (p.get("AddressInfo") or {}).get("Country")
         and p["AddressInfo"]["Country"].get("ISOCode") != "IN"]
check("All results match countrycode=IN", r.status_code == 200 and not wrong,
      f"wrong-country IDs={wrong[:5]}")

# 4. An invalid key is rejected
r = get({"countrycode": "IN", "maxresults": 1}, key="invalid-key-123")
check("Invalid API key is rejected (401/403)", r.status_code in (401, 403),
      f"status={r.status_code}")

# 5. Response time is acceptable
start = time.time()
r = get({"countrycode": "IN", "maxresults": 10})
elapsed = time.time() - start
check("Response time under 3 seconds", r.status_code == 200 and elapsed < 3,
      f"{elapsed:.2f}s")

print(f"\n{sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)