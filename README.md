# KreedoDataFetcher

A CLI tool to authenticate with the Kreedo REST API and export child and activity records to Excel.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
# Login with a JWT token and fetch children for a school
python main.py --url <base_url> --token <jwt_token> --fetch-children --school-id <id>

# Login with credentials (token is cached to .token for reuse)
python main.py --url <base_url> --credentials <user_id> <password> --fetch-children --school-id <id>

# Fetch completed activities for all children
python main.py --url <base_url> --token <jwt_token> --fetch-activities --child-name all

# Fetch activities for a specific child (partial name match)
python main.py --url <base_url> --token <jwt_token> --fetch-activities --child-name "John"
```

## Output

| File | Contents |
|------|---------|
| `child/children.xlsx` | Children, Parents, Subjects sheets |
| `child/child_activities.xlsx` | One sheet per child with completed activities |

## Architecture

- `auth.py` — `KreedoAuth` class; supports JWT token or credential login, validates token against the API.
- `child_service.py` — fetches children (paginated), enriches with subjects, exports to Excel; fetches completed activities per subject.
- `main.py` — argparse CLI entry point.
- `inspect_response.py` — debug script to inspect raw API responses.
