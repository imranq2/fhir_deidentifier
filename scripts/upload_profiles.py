"""
Upload FHIR StructureDefinition profiles (e.g., US Core) to a HAPI FHIR server.

Usage:
    python upload_profiles.py --profiles-dir /path/to/structuredefinitions --server-url http://localhost:8080/fhir

This script uploads all JSON files in the specified directory as StructureDefinition resources to the HAPI FHIR server.
"""
import os
import sys
import argparse
import json
import requests
import time
from pathlib import Path

RETRY_COUNT = 10
RETRY_WAIT_SECONDS = 5

def upload_profile(profile_path: Path, server_url: str):
    with open(profile_path, 'r', encoding='utf-8') as f:
        profile_json = json.load(f)
    profile_id = profile_json.get('id')
    if not profile_id:
        print(f"Skipping {profile_path}: No 'id' field found.", file=sys.stderr)
        return False
    url = f"{server_url.rstrip('/')}/StructureDefinition/{profile_id}"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/fhir+json"
    }
    for attempt in range(1, RETRY_COUNT + 1):
        try:
            response = requests.put(url, headers=headers, data=json.dumps(profile_json), timeout=30)
            if response.status_code in (200, 201):
                print(f"Uploaded: {profile_id} ({profile_path.name})")
                return True
            else:
                print(f"Failed to upload {profile_id} ({profile_path.name}): {response.status_code} {response.text}", file=sys.stderr)
                return False
        except Exception as e:
            if attempt == RETRY_COUNT:
                print(f"Error uploading {profile_id} ({profile_path.name}) after {RETRY_COUNT} attempts: {e}", file=sys.stderr)
                return False
            else:
                print(f"Attempt {attempt} failed for {profile_id} ({profile_path.name}): {e}. Retrying in {RETRY_WAIT_SECONDS} seconds...", file=sys.stderr)
                time.sleep(RETRY_WAIT_SECONDS)

def main():
    parser = argparse.ArgumentParser(description="Upload FHIR StructureDefinition profiles to a HAPI FHIR server.")
    parser.add_argument('--profiles-dir', required=True, help='Directory containing StructureDefinition JSON files')
    parser.add_argument('--server-url', required=True, help='Base URL of the HAPI FHIR server (e.g., http://localhost:8080/fhir)')
    args = parser.parse_args()

    profiles_dir = Path(args.profiles_dir)
    if not profiles_dir.is_dir():
        print(f"Profiles directory not found: {profiles_dir}", file=sys.stderr)
        sys.exit(1)

    json_files = list(profiles_dir.glob('*.json'))
    if not json_files:
        print(f"No JSON files found in {profiles_dir}", file=sys.stderr)
        sys.exit(1)

    total = len(json_files)
    success = 0
    for profile_path in json_files:
        if upload_profile(profile_path, args.server_url):
            success += 1
    print(f"\nUpload complete: {success}/{total} profiles uploaded successfully.")
    if success < total:
        sys.exit(1)

if __name__ == "__main__":
    main()
