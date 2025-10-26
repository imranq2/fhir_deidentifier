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
import re


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
                # Return a synthetic OperationOutcome issue for 400 errors
                return {
                    "issue": [
                        {
                            "severity": "error",
                            "code": "processing",
                            "details": {
                                "text": "400 Bad Request from validator"
                            },
                            "diagnostics": f"File: {file_path}. Response: {response.text}",
                            "location": [str(file_path)],
                            "expression": []
                        }
                    ]
                }
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            # Do not retry if status code is 400 (Bad Request)
            if hasattr(e, 'response') and e.response is not None and e.response.status_code == 400:
                # Return a synthetic OperationOutcome issue for 400 errors
                return {
                    "issue": [
                        {
                            "severity": "error",
                            "code": "processing",
                            "details": {
                                "text": "400 Bad Request from validator (exception)"
                            },
                            "diagnostics": f"File: {file_path}. Error: {e}",
                            "location": [str(file_path)],
                            "expression": []
                        }
                    ]
                }
            if attempt == max_retries:
                print(f"Error validating resource after {max_retries} attempts: {e}", file=sys.stderr)
                raise
            else:
                print(f"Attempt {attempt} failed: {e}. Retrying in {retry_wait} seconds...", file=sys.stderr)
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
        return f"http://hl7.org/fhir/us/core/StructureDefinition/{profile_name}"
    return None

def main() -> None:
    """Main entry point for CLI usage."""
    parser = argparse.ArgumentParser(description="FHIR Resource Validator using HAPI FHIR server $validate operation")
    parser.add_argument("input_path", help="Path to FHIR JSON file or directory")
    parser.add_argument("--profile", help="FHIR profile URL to validate against. If not provided, the script will use the US Core profile for each resource type by default.")
    parser.add_argument("--validator-base-url", default="http://hapi-fhir:8080/fhir", help="Base URL of the HAPI FHIR server")
    parser.add_argument("--exclude-code", action='append', default=[], help="Regex(es) for code(s) to exclude from error issues (compared to details.coding.code in OperationOutcome.issue). Can be specified multiple times. Supports regex.")
    parser.add_argument("--exclude-diagnostics", action='append', default=[], help="Regex(es) to exclude issues where diagnostics matches. Can be specified multiple times.")
    args = parser.parse_args()

    exclude_diagnostics_regexes = [re.compile(r) for r in args.exclude_diagnostics]
    exclude_code_regexes = [re.compile(r) for r in args.exclude_code]

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

    exclude_codes = set(args.exclude_code)

    def is_excluded(issue):
        details = issue.get('details', {})
        codings = details.get('coding', [])
        for coding in codings:
            code = coding.get('code', '')
            for regex in exclude_code_regexes:
                if regex.search(code):
                    return True
        diagnostics = issue.get('diagnostics', '')
        for regex in exclude_diagnostics_regexes:
            if regex.search(diagnostics):
                return True
        return False

    for file_path in files_to_validate:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                fhir_resource = json.load(f)
            # resource_type = fhir_resource.get("resourceType", "").lower()
            # Default to US Core profile if --profile is not set
            # profile_url = args.profile if args.profile else get_us_core_profile_url(resource_type)
            profile_url = args.profile
            result = validate_fhir_resource(file_path, validator_base_url=args.validator_base_url, profile=profile_url, session_id=session_id)
            # HAPI returns an OperationOutcome resource
            issues = result.get('issue', [])
            # A file is valid if there are no ERROR or FATAL issues, after excluding specified codes or diagnostics regexes
            error_issues = [issue for issue in issues if issue.get('severity', '').upper() in ('ERROR', 'FATAL') and not is_excluded(issue)]
            is_valid = not error_issues
            # Compute relative path and ensure subdirs exist in validation_result
            rel_path = file_path.relative_to(input_root)
            if len(error_issues) > 0:
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
