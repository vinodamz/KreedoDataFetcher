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

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3 |
| HTTP | `requests` (session-based auth) |
| Data processing | `pandas` |
| Excel output | `openpyxl` |
| CLI | `argparse` |

## Architecture

| File | Role |
|---|---|
| `main.py` | CLI entry point — parses args, handles auth flow, dispatches to services |
| `auth.py` | `KreedoAuth` class — `login_with_token()`, `login_with_credentials()`, `validate_token()` |
| `child_service.py` | `fetch_children()`, `fetch_child_activities()`, and Excel export functions |
| `inspect_response.py` | Standalone debug script for inspecting raw API responses |
| `test_auth_mock.py` | Mock-based unit tests for auth |

### Data Flow

```
CLI args → KreedoAuth (JWT or credentials)
         → fetch_children()         [paginated GET + detail GET + subject POST]
         → save_children_to_excel() → child/children.xlsx
         → fetch_child_activities() [reads xlsx, POST per subject]
         → save_activities_to_excel() → child/child_activities.xlsx
```

### API Endpoints Used

| Endpoint | Method | Purpose |
|---|---|---|
| `/users/login` | POST | Credential login |
| `/users/logged_in_user_detail` | GET | Token validation |
| `/child/child_list_create` | GET | Paginated child list |
| `/child/child_retrive_update_delete/{id}` | GET | Child detail |
| `/plan/subject_list_by_child` | POST | Assigned subjects per child |
| `/activity/flag_based_activity` | POST | Completed activities per subject |
