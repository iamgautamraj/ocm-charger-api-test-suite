# Open Charge Map API Test Suite

A QA project that tests the public [Open Charge Map](https://openchargemap.org) (OCM) API, the open database of EV charging stations used by many charging apps. It covers charger search, filters, response structure, data quality, authentication, and negative/boundary cases, using **Postman (run with Newman)** and **Python**.

> This is an independent testing project. It only sends read (GET) requests to the API and never submits or edits data.

## Why this API

Finding chargers, filtering by connector type and status, and trusting the data are core features of any EV charging app. OCM exposes all of these through a real, free API with Indian charger data, so the defects found here are real behaviours of a live service.

## What is tested

| Area | What is checked |
|---|---|
| Search | Search by country and by location + radius; `maxresults` respected; empty result for a location with no chargers |
| Structure | Every charger record has `ID`, `AddressInfo` (lat/long) and `Connections` |
| Data quality | No duplicate IDs, non-empty titles, coordinates inside India for `countrycode=IN` |
| Filters | `connectiontypeid`, `statustypeid`, `levelid` really narrow the results |
| Reference data | Lookup lists (connection types, status types, countries) are returned |
| Auth | Missing key, invalid key, key sent in `X-API-Key` header |
| Negative / boundary | `maxresults=0`, `-1`, `abc`; latitude `999` |
| Every request | No 5xx errors; response time under 3 s |

19 test cases in total (see `test_cases/test_cases.csv`).

## Tools

- Postman collection (generated and exported as JSON), run from the terminal with **Newman**
- **Python 3** with `requests` for quick standalone checks
- **GitHub Codespaces** as the dev environment
- Markdown bug reports

## Repository structure

```
ocm-charger-api-test-suite/
├── README.md
├── requirements.txt
├── .gitignore
├── test_cases/
│   └── test_cases.csv          # 19 test cases with expected and actual results
├── postman/
│   ├── build_collection.py     # builds the collection, environment and CSV from one list
│   ├── ocm_collection.json     # Postman collection (import into Postman or run with Newman)
│   └── ocm_environment.json    # environment (API key left blank)
├── scripts/
│   └── check_api.py            # 5 standalone Python checks
├── bug_reports/
│   ├── BUG-001.md
│   ├── BUG-002.md
│   └── evidence/               # saved API responses that prove each finding
└── screenshots/
```

## Setup (step by step)

### 1. Get an API key
1. Create a free account at [openchargemap.org](https://openchargemap.org).
2. Open **My Profile → My Apps** and generate an API key.

### 2. Clone and install
```bash
git clone https://github.com/<your-username>/ocm-charger-api-test-suite.git
cd ocm-charger-api-test-suite
pip install -r requirements.txt
npm install -g newman newman-reporter-htmlextra
```
Requirements: Python 3, Node.js and npm. Codespaces already includes them.

### 3. Set your key as an environment variable
```bash
export OCM_API_KEY="your-key-here"
```
The key is never stored in the repo. It must be set again in each new terminal session.

## Running the tests

### 1. Generate the Postman collection and test-case CSV
```bash
python postman/build_collection.py
```
All test cases live in one list inside `build_collection.py`. Each entry produces a Postman request, its test script, and a row in `test_cases/test_cases.csv`.

### 2. Run the Python checks
```bash
python scripts/check_api.py
```
Expected output: five lines marked `PASS` or `FAIL` and a total such as `5/5 checks passed`.

### 3. Run the Postman collection with Newman
```bash
mkdir -p reports
newman run postman/ocm_collection.json -e postman/ocm_environment.json \
  --env-var "api_key=$OCM_API_KEY" \
  -r cli,htmlextra --reporter-htmlextra-export reports/ocm_report.html
```
Each request shows a ✓ for each passed test and a numbered entry for each failed one. A summary table and a failure list appear at the end.

**Note:** `reports/` is git-ignored because the HTML report prints request URLs, which include your API key.

### 4. (Optional) Use the collection in Postman
Import `postman/ocm_collection.json` and `postman/ocm_environment.json` into Postman, set the `api_key` value in the environment, and run the collection with Collection Runner.

## Results

Last run: `<date>`

| Metric | Result |
|---|---|
| Requests executed | 19 |
| Assertions | 74 (72 passed, 2 failed) |
| Python checks | 5/5 passed |
| Response time | 31 ms to 1.7 s (average about 700 ms) |
| Server errors (5xx) | 0 |

![Newman summary](screenshots/newman_summary.png)

### Defects and findings

| ID | Test case | Type | Summary | Severity |
|---|---|---|---|---|
| [BUG-001](bug_reports/BUG-001.md) | TC-18 | API validation | An out-of-range latitude (`999`) returns `200 OK` with unrelated chargers (for example in Finland) instead of an error or an empty list. | Medium |
| [BUG-002](bug_reports/BUG-002.md) | TC-07 | Data quality | Charger ID 510821, listed in Ahmedabad, has a longitude of 53.32, which is outside India. | Low-Medium |

**Observation (not reported as a bug):** `maxresults=abc` is silently replaced with the default of 100 results. The API is lenient with invalid input and doesn't reject it. I'd recommend documenting this behaviour or returning a 400.

### What worked as expected
- Search by country and by radius, `maxresults`, and the connection type, status and level filters.
- No duplicate IDs and no empty titles in the 100 India records checked.
- Missing and invalid API keys are rejected with `403`, and the key also works in the `X-API-Key` header.

## How the tests were designed

- Each test case has an expected result written **before** running it, based on the OCM documentation.
- When a test failed, I reproduced it by hand with `curl` and checked the docs to decide whether it was a real defect or a wrong assumption of mine. One scripting error of mine (a variable name clashing with Newman's built-in `data`) was found and fixed this way.
- Negative cases check that invalid input is either rejected or handled safely, and never causes a server error.

## Limitations

- OCM is an external, community-maintained, read-only data source. Results change over time, so some findings may stop reproducing once the data is corrected. Evidence files in `bug_reports/evidence/` were captured on `<date>`.
- There is no login, session or payment flow here, because OCM does not provide them.
- Filter IDs (`33`, `50`, `3`) and the India bounding box (latitude 6-38, longitude 68-98) were taken from OCM reference data and are approximate.
- Response-time checks depend on network conditions and are indicative only.

## Security notes

- The API key is read from an environment variable and never committed.
- Only GET requests are used. No data is submitted or modified.
- Keep API usage light: results are cached by the tester during development and the suite is not meant to be run in loops.

## Ideas for future work

- A small mock EV charging service (login, start/stop session, payment) to test a full charging flow.
- More cities and filters through a data-driven Collection Runner file.
- Run the suite automatically on every push with GitHub Actions.