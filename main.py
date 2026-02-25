import argparse
import logging
import sys
from auth import KreedoAuth

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Kreedo Data Fetcher Login")
    parser.add_argument("--url", required=True, help="Base URL of the Kreedo instance")
    
    # Create a mutually exclusive group for login methods
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--token", help="Access token for login")
    group.add_argument("--credentials", nargs=2, metavar=('USER_ID', 'PASSWORD'), help="User ID and Password for login")
    
    parser.add_argument("--fetch-children", action="store_true", help="Fetch and store child data")
    parser.add_argument("--fetch-activities", action="store_true", help="Fetch activities for children")
    parser.add_argument("--child-name", help="Filter activities by child name (or 'all')")
    parser.add_argument("--school-id", help="School ID for fetching data")

    args = parser.parse_args()

    auth = KreedoAuth()
    
    # Try to use stored token first
    if not args.token and not args.credentials:
        if os.path.exists(".token"):
            try:
                with open(".token", "r") as f:
                    stored_token = f.read().strip()
                
                if stored_token:
                    if auth.validate_token(args.url, stored_token):
                        logger.info("Using stored token.")
                        auth.login_with_token(args.url, stored_token)
                    else:
                        logger.warning("Stored token is invalid or expired.")
            except Exception as e:
                logger.warning(f"Could not read stored token: {e}")

    if not auth.session.headers.get("Authorization"):
        if args.token:
            auth.login_with_token(args.url, args.token)
        elif args.credentials:
            token = auth.login_with_credentials(args.url, args.credentials[0], args.credentials[1])
            if token:
                logger.info(f"Logged in. Token: {token}")
                try:
                    with open(".token", "w") as f:
                        f.write(token)
                except IOError as e:
                    logger.error(f"Failed to save token to file: {e}")
            else:
                logger.error("Login failed.")
                sys.exit(1)
        else:
            logger.error("No valid token found and no credentials provided.")
            sys.exit(1)

    if args.fetch_children:
        if not args.school_id:
            logger.error("--school-id is required when fetching children.")
            sys.exit(1)
            
        from child_service import fetch_children, save_children_to_excel
        children = fetch_children(auth, args.url, args.school_id)
        save_children_to_excel(children)

    if args.fetch_activities:
        child_name = args.child_name
        if not child_name:
            try:
                child_name = input("Enter child name to fetch activities for (or type 'all'): ").strip()
            except EOFError:
                # Handle non-interactive environments
                logger.warning("No input provided and not interactive. Defaulting to 'all'.")
                child_name = 'all'
                
        from child_service import fetch_child_activities, save_activities_to_excel
        activities, child_map = fetch_child_activities(auth, args.url, child_name_filter=child_name)
        save_activities_to_excel(activities, child_map)

if __name__ == "__main__":
    main()
