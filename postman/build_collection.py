"""
Builds postman/ocm_collection.json and test_cases/test_cases.csv from one list of test cases.
Run from the repo root:  python postman/build_collection.py
"""
import csv
import json

BASE = "{{base_url}}"
PATH = ["v3", "poi", ""]

# ---------- reusable JS snippets (Postman test scripts) ----------
STATUS_200 = 'pm.test("Status is 200", () => pm.response.to.have.status(200));'
IS_ARRAY = (
    'const body = pm.response.json();\n'
    'pm.test("Response is a non-empty array", () => {\n'
    '  pm.expect(body).to.be.an("array");\n'
    '  pm.expect(body.length).to.be.above(0);\n'
    '});'
)
PARSE = 'const body = pm.response.json();'


def tc(tc_id, area, name, params, expected, tests, key="param", path=None):
    """One test case = one Postman request + its tests + one CSV row."""
    return dict(id=tc_id, area=area, name=name, params=params, expected=expected,
                tests=tests, key=key, path=path or PATH)


CASES = [
    # ---------------- Search ----------------
    tc("TC-01", "Search", "Search chargers in India (maxresults=10)",
       [("output", "json"), ("countrycode", "IN"), ("maxresults", "10")],
       "200, non-empty array, at most 10 results, all in India",
       [STATUS_200, IS_ARRAY,
        'pm.test("Respects maxresults (<= 10)", () => pm.expect(body.length).to.be.at.most(10));',
        'pm.test("All results are in India", () => {\n'
        '  body.forEach(p => {\n'
        '    const c = p.AddressInfo && p.AddressInfo.Country;\n'
        '    if (c) pm.expect(c.ISOCode).to.equal("IN");\n'
        '  });\n'
        '});']),
    tc("TC-02", "Search", "Search within 10 km of a point in Bengaluru",
       [("output", "json"), ("latitude", "12.9716"), ("longitude", "77.5946"),
        ("distance", "10"), ("distanceunit", "KM"), ("maxresults", "20")],
       "200, non-empty array, every result within 10 km",
       [STATUS_200, IS_ARRAY,
        'pm.test("Every result is within 10 km", () => {\n'
        '  body.forEach(p => {\n'
        '    if (p.AddressInfo && typeof p.AddressInfo.Distance === "number")\n'
        '      pm.expect(p.AddressInfo.Distance).to.be.at.most(10);\n'
        '  });\n'
        '});']),
    tc("TC-03", "Search", "maxresults=5 is respected",
       [("output", "json"), ("countrycode", "IN"), ("maxresults", "5")],
       "200 and no more than 5 results",
       [STATUS_200, PARSE,
        'pm.test("At most 5 results", () => pm.expect(body.length).to.be.at.most(5));']),
    tc("TC-04", "Search", "Location with no chargers (mid-ocean)",
       [("output", "json"), ("latitude", "0"), ("longitude", "-30"),
        ("distance", "10"), ("distanceunit", "KM")],
       "200 and an empty array",
       [STATUS_200, PARSE,
        'pm.test("Empty array returned", () => {\n'
        '  pm.expect(body).to.be.an("array");\n'
        '  pm.expect(body.length).to.equal(0);\n'
        '});']),
    # ---------------- Response structure & data quality ----------------
    tc("TC-05", "Structure", "Required fields present in each charger record",
       [("output", "json"), ("countrycode", "IN"), ("maxresults", "50")],
       "Every record has ID, AddressInfo (lat/long) and a Connections array",
       [STATUS_200, IS_ARRAY,
        'pm.test("Each record has required fields", () => {\n'
        '  body.forEach(p => {\n'
        '    pm.expect(p.ID, "ID").to.be.a("number");\n'
        '    pm.expect(p.AddressInfo, "AddressInfo").to.be.an("object");\n'
        '    pm.expect(p.AddressInfo.Latitude, "Latitude").to.be.a("number");\n'
        '    pm.expect(p.AddressInfo.Longitude, "Longitude").to.be.a("number");\n'
        '    pm.expect(p.Connections, "Connections").to.be.an("array");\n'
        '  });\n'
        '});']),
    tc("TC-06", "Data quality", "No duplicate charger IDs in one response",
       [("output", "json"), ("countrycode", "IN"), ("maxresults", "100")],
       "All IDs are unique",
       [STATUS_200, PARSE,
        'pm.test("Charger IDs are unique", () => {\n'
        '  const ids = body.map(p => p.ID);\n'
        '  pm.expect(new Set(ids).size).to.equal(ids.length);\n'
        '});']),
    tc("TC-07", "Data quality", "India results have coordinates inside India",
       [("output", "json"), ("countrycode", "IN"), ("maxresults", "100")],
       "Latitude 6-38 and longitude 68-98 for every record",
       [STATUS_200, PARSE,
        'pm.test("Coordinates fall inside India bounding box", () => {\n'
        '  const bad = body.filter(p => {\n'
        '    const a = p.AddressInfo;\n'
        '    return a.Latitude < 6 || a.Latitude > 38 || a.Longitude < 68 || a.Longitude > 98;\n'
        '  }).map(p => p.ID + " (" + p.AddressInfo.Latitude + ", " + p.AddressInfo.Longitude + ")");\n'
        '  pm.expect(bad, "IDs outside India: " + bad.join("; ")).to.be.empty;\n'
        '});']),
    tc("TC-08", "Data quality", "Every record has a non-empty title",
       [("output", "json"), ("countrycode", "IN"), ("maxresults", "100")],
       "Title is not empty for every record",
       [STATUS_200, PARSE,
        'pm.test("Every record has a non-empty title", () => {\n'
        '  body.forEach(p => pm.expect(((p.AddressInfo || {}).Title || "").trim().length, "title of ID " + p.ID).to.be.above(0));\n'
        '});']),
    # ---------------- Filters ----------------
    tc("TC-09", "Filters", "Filter by connection type (33 = CCS, verify in reference data)",
       [("output", "json"), ("countrycode", "IN"), ("connectiontypeid", "33"), ("maxresults", "20")],
       "Every returned charger has at least one connection of type 33",
       [STATUS_200, PARSE,
        'pm.test("Each charger has a connection of type 33", () => {\n'
        '  body.forEach(p => pm.expect(p.Connections.some(c => c.ConnectionTypeID === 33), "ID " + p.ID).to.be.true);\n'
        '});']),
    tc("TC-10", "Filters", "Filter by status (50 = Operational, verify in reference data)",
       [("output", "json"), ("countrycode", "IN"), ("statustypeid", "50"), ("maxresults", "20")],
       "Every returned charger has status 50",
       [STATUS_200, PARSE,
        'pm.test("Each charger has status 50", () => {\n'
        '  body.forEach(p => {\n'
        '    if (p.StatusType) pm.expect(p.StatusType.ID, "ID " + p.ID).to.equal(50);\n'
        '  });\n'
        '});']),
    tc("TC-11", "Filters", "Filter by level (3 = DC fast, verify in reference data)",
       [("output", "json"), ("countrycode", "IN"), ("levelid", "3"), ("maxresults", "20")],
       "Every returned charger has a connection at level 3",
       [STATUS_200, PARSE,
        'pm.test("Each charger has a level 3 connection", () => {\n'
        '  body.forEach(p => pm.expect(p.Connections.some(c => c.LevelID === 3), "ID " + p.ID).to.be.true);\n'
        '});']),
    # ---------------- Reference data ----------------
    tc("TC-12", "Reference data", "Reference data endpoint returns lookup lists",
       [("output", "json")],
       "200 with ConnectionTypes, StatusTypes and Countries lists",
       [STATUS_200, PARSE,
        'pm.test("Has ConnectionTypes, StatusTypes, Countries", () => {\n'
        '  ["ConnectionTypes", "StatusTypes", "Countries"].forEach(k => {\n'
        '    pm.expect(body[k], k).to.be.an("array");\n'
        '    pm.expect(body[k].length, k).to.be.above(0);\n'
        '  });\n'
        '});'],
       path=["v3", "referencedata", ""]),
    # ---------------- Auth ----------------
    tc("TC-13", "Auth", "Request with no API key",
       [("output", "json"), ("countrycode", "IN"), ("maxresults", "1")],
       "401 or 403 (docs say a key is required)",
       ['pm.test("Missing key is rejected (401/403)", () => pm.expect([401, 403]).to.include(pm.response.code));'],
       key="none"),
    tc("TC-14", "Auth", "Request with an invalid API key",
       [("output", "json"), ("countrycode", "IN"), ("maxresults", "1")],
       "401 or 403",
       ['pm.test("Invalid key is rejected (401/403)", () => pm.expect([401, 403]).to.include(pm.response.code));'],
       key="invalid"),
    tc("TC-15", "Auth", "Valid key sent in X-API-Key header instead of query",
       [("output", "json"), ("countrycode", "IN"), ("maxresults", "1")],
       "200 and a non-empty array",
       [STATUS_200, IS_ARRAY],
       key="header"),
    # ---------------- Negative & boundary ----------------
    tc("TC-16", "Negative", "maxresults=0",
       [("output", "json"), ("countrycode", "IN"), ("maxresults", "0")],
       "400, or 200 with a valid array (never a server error)",
       ['pm.test("Handled gracefully (200 or 400)", () => pm.expect([200, 400]).to.include(pm.response.code));']),
    tc("TC-17", "Negative", "maxresults=-1",
       [("output", "json"), ("countrycode", "IN"), ("maxresults", "-1")],
       "400, or 200 with a valid array (never a server error)",
       ['pm.test("Handled gracefully (200 or 400)", () => pm.expect([200, 400]).to.include(pm.response.code));']),
    tc("TC-18", "Negative", "latitude=999 (out of range)",
       [("output", "json"), ("latitude", "999"), ("longitude", "77.5946"), ("distance", "10")],
       "Rejected with 4xx, or 200 with no results",
       ['pm.test("Invalid latitude rejected or returns no results", () => {\n'
        '  if (pm.response.code === 200) pm.expect(pm.response.json().length).to.equal(0);\n'
        '  else pm.expect(pm.response.code).to.be.within(400, 499);\n'
        '});']),
    tc("TC-19", "Negative", "maxresults=abc (text instead of number)",
       [("output", "json"), ("countrycode", "IN"), ("maxresults", "abc")],
       "400, or 200 with a valid array (never a server error)",
       ['pm.test("Handled gracefully (200 or 400)", () => pm.expect([200, 400]).to.include(pm.response.code));']),
]

# Runs on EVERY request (collection-level tests)
COLLECTION_TESTS = [
    'pm.test("No server error (status < 500)", () => pm.expect(pm.response.code).to.be.below(500));',
    'pm.test("Response time under 3000 ms", () => pm.expect(pm.response.responseTime).to.be.below(3000));',
]


def build_item(c):
    query = [{"key": k, "value": v} for k, v in c["params"]]
    headers = []
    if c["key"] == "param":
        query.append({"key": "key", "value": "{{api_key}}"})
    elif c["key"] == "invalid":
        query.append({"key": "key", "value": "invalid-key-123"})
    elif c["key"] == "header":
        headers.append({"key": "X-API-Key", "value": "{{api_key}}"})
    raw_q = "&".join(f"{q['key']}={q['value']}" for q in query)
    raw = f"{BASE}/" + "/".join(c["path"]) + "?" + raw_q
    return {
        "name": f"{c['id']}: {c['name']}",
        "event": [{"listen": "test", "script": {"type": "text/javascript",
                                                "exec": "\n".join(c["tests"]).split("\n")}}],
        "request": {
            "method": "GET", "header": headers,
            "url": {"raw": raw, "host": [BASE], "path": c["path"], "query": query},
        },
    }


folders = {}
for c in CASES:
    folders.setdefault(c["area"], []).append(build_item(c))

collection = {
    "info": {
        "name": "Open Charge Map API Test Suite",
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
    },
    "event": [{"listen": "test", "script": {"type": "text/javascript", "exec": COLLECTION_TESTS}}],
    "item": [{"name": area, "item": items} for area, items in folders.items()],
}

with open("postman/ocm_collection.json", "w") as f:
    json.dump(collection, f, indent=2)

env = {
    "name": "OCM Environment",
    "values": [
        {"key": "base_url", "value": "https://api.openchargemap.io", "enabled": True},
        {"key": "api_key", "value": "", "type": "secret", "enabled": True},
    ],
}
with open("postman/ocm_environment.json", "w") as f:
    json.dump(env, f, indent=2)

with open("test_cases/test_cases.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["ID", "Area", "Scenario", "Request", "Expected Result", "Actual Result", "Status", "Bug ID"])
    for c in CASES:
        q = "&".join(f"{k}={v}" for k, v in c["params"])
        w.writerow([c["id"], c["area"], c["name"], "GET /" + "/".join(c["path"]) + "?" + q,
                    c["expected"], "", "", ""])

print(f"Built {len(CASES)} test cases -> postman/ocm_collection.json, postman/ocm_environment.json, test_cases/test_cases.csv")