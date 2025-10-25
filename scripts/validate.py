# !/usr/bin/env python3
"""
FHIR Resource Validator using validator-wrapper Docker container
"""

import json
import requests
from pathlib import Path
from typing import Dict, Any, Optional
import sys
import uuid


def validate_fhir_resource(
        file_path: Path,
        validator_url: str = "http://fhir-validator:3500/validate",
        profile: Optional[str] = None
) -> Dict[str, Any]:
    """
    Validate a FHIR JSON resource file.

    Args:
        file_path: Path to the FHIR JSON file
        validator_url: URL of the validator endpoint
        profile: Optional FHIR profile URL to validate against

    Returns:
        Validation response as dictionary
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        fhir_resource: Dict[str, Any] = json.load(f)
        fhir_resource_str = json.dumps(fhir_resource)

    headers: Dict[str, str] = {"Content-Type": "application/json"}

    cli_context = {
        "sv": "4.0.1",
        "igs": ["hl7.fhir.us.core#6.1.0"],
        "profiles": [profile] if profile else [],
        "locale": "en"
    }

    files_to_validate = [
        {
            "fileName": file_path.name,
            "fileContent": fhir_resource_str,
            "fileType": "json"
        }
    ]

    session_id = str(uuid.uuid4())

    validation_request = {
        "cliContext": cli_context,
        "filesToValidate": files_to_validate,
        "sessionId": session_id
    }

    max_retries = 5
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(
                validator_url,
                json=validation_request,
                headers=headers,
                timeout=30
            )
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

    total = len(files_to_validate)
    passed = 0
    failed = 0
    failed_files = []

    for file_path in files_to_validate:
        try:
            result = validate_fhir_resource(file_path)
            outcomes = result.get("outcomes", [])
            # A file is valid if there are no ERROR-level issues in any outcome
            has_error = any(
                any(issue.get('level', '').upper() == 'ERROR' for issue in outcome.get('issues', []))
                for outcome in outcomes
            )
            is_valid = not has_error
            status = "PASSED" if is_valid else "FAILED"
            print(f"{file_path}: {status}")
            if is_valid:
                passed += 1
            else:
                failed += 1
                failed_files.append(file_path)
                # Print only ERROR issues for each failed outcome
                for outcome in outcomes:
                    issues = outcome.get("issues", [])
                    error_issues = [issue for issue in issues if issue.get('level', '').upper() == 'ERROR']
                    if error_issues:
                        print(f"  ERROR Issues in {file_path}:")
                        for issue in error_issues:
                            print(f"    - {issue}")
        except Exception as e:
            print(f"{file_path}: ERROR - {e}", file=sys.stderr)
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
