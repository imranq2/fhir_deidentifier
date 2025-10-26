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
                print(f"Attempt {attempt} failed: {e}. Retrying in 3 seconds...", file=sys.stderr)
                import time
                time.sleep(3)
    return {}

def main() -> None:
    """Main entry point for CLI usage."""
    if len(sys.argv) < 2:
        print("Usage: python validate.py <path-to-fhir-json-file-or-directory>")
        sys.exit(1)

    input_path = Path(sys.argv[1])
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

    for file_path in files_to_validate:
        try:
            result = validate_fhir_resource(file_path, session_id=session_id)
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

    print(f"\nValidation complete. {passed}/{total} files PASSED, {failed} FAILED.")
    if failed > 0:
        # Print just the list of failed files at the end
        print("\nFAILED FILES LIST:")
        for f in failed_files:
            print(f)
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
