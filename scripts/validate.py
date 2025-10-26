# !/usr/bin/env python3
"""
FHIR Resource Validator using HAPI FHIR server $validate operation
"""

import json
import requests
from pathlib import Path
from typing import Dict, Any, Optional
import sys
import uuid
import argparse
import time


def validate_fhir_resource(
        file_path: Path,
        validator_base_url: str = "http://hapi-fhir:8080/fhir",
        profile: Optional[str] = None,
        session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Validate a FHIR JSON resource file using HAPI FHIR server $validate operation.

    Args:
        file_path: Path to the FHIR JSON file
        validator_base_url: Base URL of the HAPI FHIR server
        profile: Optional FHIR profile URL to validate against (sent as a parameter)
        session_id: Optional session ID (unused, for compatibility)

    Returns:
        Validation response as dictionary
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        fhir_resource: Dict[str, Any] = json.load(f)

    # Determine resourceType for endpoint
    resource_type = fhir_resource.get("resourceType")
    if not resource_type:
        raise ValueError(f"No resourceType found in file: {file_path}")
    validator_url = f"{validator_base_url.rstrip('/')}/{resource_type}/$validate"

    headers: Dict[str, str] = {"Content-Type": "application/fhir+json", "Accept": "application/fhir+json"}

    params = {}
    if profile:
        params['profile'] = profile

    # Send the FHIR resource directly as the body for $validate
    request_body = json.dumps(fhir_resource)

    retry_wait = 5
    max_retries = 10
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(
                validator_url,
                params=params,
                data=request_body,
                headers=headers,
                timeout=30
            )
            if response.status_code == 400:
                print("\nDEBUG: 400 Bad Request. Request payload:")
                print(json.dumps(fhir_resource, indent=2))
                print("Headers:", headers)
                print("URL:", validator_url)
                print("Params:", params)
                print("Response:", response.text)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if attempt == max_retries:
                print(f"Error validating resource after {max_retries} attempts: {e}", file=sys.stderr)
                raise
            else:
                print(f"Attempt {attempt} failed: {e}. Retrying in {retry_wait} seconds...", file=sys.stderr)
                import time
                time.sleep(retry_wait)
    return {}

def get_us_core_profile_url(resource_type: str) -> Optional[str]:
    """
    Return the canonical US Core 6.1.0 profile URL for a given resource type, if known.
    """
    resource_type = resource_type.lower()
    # Map resourceType to US Core profile name
    us_core_profiles = {
        "patient": "us-core-patient",
        "observation": "us-core-observation",
        "condition": "us-core-condition",
        "allergyintolerance": "us-core-allergyintolerance",
        "medicationrequest": "us-core-medicationrequest",
        "medicationstatement": "us-core-medicationstatement",
        "documentreference": "us-core-documentreference",
        "composition": "us-core-composition",
        "person": "us-core-person",
        # Add more as needed
    }
    profile_name = us_core_profiles.get(resource_type)
    if profile_name:
        return f"https://hl7.org/fhir/us/core/StructureDefinition/{profile_name}"
    return None

def install_us_core_ig(validator_base_url: str, version: str = "6.1.0", max_retries: int = 10, retry_wait: int = 10):
    """
    Install the US Core IG package on the HAPI FHIR server using the IG installer endpoint.
    Retries if the server is not yet online or install takes time.
    """
    ig_installer_url = validator_base_url.rstrip("/fhir/").rstrip("/") + "/write/install/by-param"
    params = {
        "fetchDependencies": "true",
        "installMode": "STORE_AND_INSTALL",
        "name": "hl7.fhir.us.core",
        "version": version
    }
    print(f"Ensuring US Core IG {version} is installed on HAPI FHIR server...")
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(ig_installer_url, params=params, timeout=120)
            if response.status_code in (200, 201):
                print("US Core IG installed successfully.")
                return True
            else:
                print(f"Attempt {attempt}: Failed to install US Core IG: {response.status_code} {response.text}")
        except Exception as e:
            print(f"Attempt {attempt}: Error installing US Core IG: {e}")
        if attempt < max_retries:
            print(f"Retrying in {retry_wait} seconds...")
            time.sleep(retry_wait)
    print("Failed to install US Core IG after multiple attempts.")
    return False

def main() -> None:
    """Main entry point for CLI usage."""
    parser = argparse.ArgumentParser(description="FHIR Resource Validator using HAPI FHIR server $validate operation")
    parser.add_argument("input_path", help="Path to FHIR JSON file or directory")
    parser.add_argument("--profile", help="FHIR profile URL to validate against. If not provided, the script will use the US Core profile for each resource type by default.")
    parser.add_argument("--validator-base-url", default="http://hapi-fhir:8080/fhir", help="Base URL of the HAPI FHIR server")
    args = parser.parse_args()

    input_path = Path(args.input_path)
    files_to_validate = []

    if input_path.is_file():
        files_to_validate = [input_path]
    elif input_path.is_dir():
        files_to_validate = list(input_path.rglob('*.json'))
        if not files_to_validate:
            print(f"No JSON files found in directory: {input_path}", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"File or directory not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    # # Always infer US Core profile if --profile is not set
    # needs_us_core = False
    # if args.profile:
    #     needs_us_core = args.profile.startswith("https://hl7.org/fhir/us/core/StructureDefinition/")
    # else:
    #     # If any file is a US Core resource type, we need US Core IG
    #     for file_path in files_to_validate:
    #         with open(file_path, 'r', encoding='utf-8') as f:
    #             fhir_resource = json.load(f)
    #         resource_type = fhir_resource.get("resourceType", "").lower()
    #         if get_us_core_profile_url(resource_type):
    #             needs_us_core = True
    #             break
    # if needs_us_core or not args.profile:
    #     # Always install US Core IG if defaulting to US Core profiles
    #     install_us_core_ig(args.validator_base_url, version="6.1.0")

    # Create validation_result directory if it does not exist
    validation_result_dir = Path("/validation_result")
    validation_result_dir.mkdir(exist_ok=True)

    # Determine the root for relative paths
    input_root = input_path if input_path.is_dir() else input_path.parent

    # Create a single session_id for all validations (not used for HAPI, but kept for compatibility)
    session_id = str(uuid.uuid4())

    total = len(files_to_validate)
    passed = 0
    failed = 0
    failed_files = []

    for file_path in files_to_validate:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                fhir_resource = json.load(f)
            resource_type = fhir_resource.get("resourceType", "").lower()
            # Default to US Core profile if --profile is not set
            profile_url = args.profile if args.profile else get_us_core_profile_url(resource_type)
            result = validate_fhir_resource(file_path, validator_base_url=args.validator_base_url, profile=profile_url, session_id=session_id)
            # HAPI returns an OperationOutcome resource
            issues = result.get('issue', [])
            # A file is valid if there are no ERROR or FATAL issues
            error_issues = [issue for issue in issues if issue.get('severity', '').upper() in ('ERROR', 'FATAL')]
            is_valid = not error_issues
            # Compute relative path and ensure subdirs exist in validation_result
            rel_path = file_path.relative_to(input_root)
            result_file = validation_result_dir / rel_path
            result_file.parent.mkdir(parents=True, exist_ok=True)
            with open(result_file, 'w', encoding='utf-8') as rf:
                json.dump(error_issues, rf, indent=2)
            # Print only the relative file path and status
            if is_valid:
                print(f"{rel_path} PASSED")
                passed += 1
            else:
                print(f"{rel_path} FAILED ({len(error_issues)})")
                failed += 1
                failed_files.append(file_path)
        except Exception as e:
            rel_path = file_path.relative_to(input_root)
            print(f"{rel_path} FAILED (error: {e})", file=sys.stderr)
            failed += 1
            failed_files.append(file_path)

    if failed > 0:
        # Print just the list of failed files at the end
        print("\nFAILED FILES LIST:")
        for f in failed_files:
            print(f"{f} FAILED")
        print(f"\n----- Validation complete. {passed}/{total} files PASSED, {failed} FAILED ----")
        sys.exit(1)
    else:
        print(f"\n----- Validation complete. {passed}/{total} files PASSED, {failed} FAILED ----")
        sys.exit(0)


if __name__ == "__main__":
    main()
