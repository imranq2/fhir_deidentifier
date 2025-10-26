"""
Download all US Core StructureDefinition profiles and save them in a /profiles folder.

Usage:
    python download_profiles.py --version 6.1.0

This script downloads all StructureDefinition JSONs from the US Core Implementation Guide package for the specified version.
"""
import os
import sys
import argparse
import requests
from pathlib import Path

US_CORE_PACKAGE_URL = "https://packages.fhir.org/hl7.fhir.us.core/{version}"
US_CORE_RESOURCES_URL = "https://hl7.org/fhir/us/core/{version}/StructureDefinition-{name}.json"

# List of US Core profile names for version 6.1.0 (add more as needed)
US_CORE_PROFILE_NAMES = [
    "us-core-patient",
    "us-core-observation",
    "us-core-condition",
    "us-core-allergyintolerance",
    "us-core-medicationrequest",
    "us-core-medicationstatement",
    "us-core-documentreference",
    "us-core-composition",
    "us-core-person",
    # Add more as needed
]

def download_profile(profile_name: str, version: str, out_dir: Path):
    url = US_CORE_RESOURCES_URL.format(version=version, name=profile_name)
    out_path = out_dir / f"{profile_name}.json"
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(response.text)
            print(f"Downloaded: {profile_name}")
            return True
        else:
            print(f"Failed to download {profile_name}: {response.status_code} {response.text}", file=sys.stderr)
            return False
    except Exception as e:
        print(f"Error downloading {profile_name}: {e}", file=sys.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(description="Download US Core StructureDefinition profiles.")
    parser.add_argument('--version', default='6.1.0', help='US Core version (default: 6.1.0)')
    parser.add_argument('--out-dir', default='/profiles', help='Output directory for profiles (default: ./profiles)')
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # If /profiles is not empty (ignoring readme.md), do nothing and exit
    non_readme_files = [f for f in out_dir.iterdir() if f.name.lower() != 'readme.md']
    if non_readme_files:
        print(f"Directory {out_dir} is not empty (ignoring readme.md). Skipping download.")
        sys.exit(0)

    total = len(US_CORE_PROFILE_NAMES)
    success = 0
    for profile_name in US_CORE_PROFILE_NAMES:
        if download_profile(profile_name, args.version, out_dir):
            success += 1
    print(f"\nDownload complete: {success}/{total} profiles downloaded successfully.")
    if success < total:
        sys.exit(1)

if __name__ == "__main__":
    main()
