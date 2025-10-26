"""
Download all US Core StructureDefinition profiles and save them in a /profiles folder.

Usage:
    python download_profiles.py --version 6.1.0

This script downloads the US Core Implementation Guide NPM package for the specified version,
extracts all StructureDefinition JSONs, and saves them in the output directory.
"""
import os
import sys
import argparse
import requests
from pathlib import Path
import tarfile
import tempfile
import shutil

NPM_PACKAGE_URL = "https://packages2.fhir.org/packages/hl7.fhir.us.core/{version}"  # Redirects to .tgz


def download_and_extract_profiles(version: str, out_dir: Path):
    # Download the NPM package
    url = NPM_PACKAGE_URL.format(version=version)
    print(f"Downloading US Core NPM package for version {version}...")
    response = requests.get(url, allow_redirects=True, timeout=60)
    if response.status_code != 200:
        print(f"Failed to download NPM package: {response.status_code} {response.text}", file=sys.stderr)
        return False
    with tempfile.TemporaryDirectory() as tmpdir:
        tgz_path = Path(tmpdir) / f"uscore-{version}.tgz"
        with open(tgz_path, "wb") as f:
            f.write(response.content)
        # Extract the tarball
        with tarfile.open(tgz_path, "r:gz") as tar:
            tar.extractall(path=tmpdir)
        # Find StructureDefinition JSONs
        structdef_dir = Path(tmpdir) / "package" / "StructureDefinition"
        if not structdef_dir.exists():
            print(f"No StructureDefinition directory found in package.", file=sys.stderr)
            return False
        files = list(structdef_dir.glob("*.json"))
        if not files:
            print(f"No StructureDefinition JSON files found in package.", file=sys.stderr)
            return False
        for file in files:
            shutil.copy(file, out_dir / file.name)
            print(f"Downloaded: {file.name}")
    return True

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

    if download_and_extract_profiles(args.version, out_dir):
        print("\nDownload complete: All StructureDefinition profiles downloaded successfully.")
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
