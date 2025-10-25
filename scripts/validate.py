# !/usr/bin/env python3
"""
FHIR Resource Validator using validator-wrapper Docker container
"""

import json
import requests
from pathlib import Path
from typing import Dict, Any, Optional
import sys


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

    headers: Dict[str, str] = {"Content-Type": "application/json"}
    params: Dict[str, str] = {}

    if profile:
        params["profile"] = profile

    try:
        response = requests.post(
            validator_url,
            json=fhir_resource,
            headers=headers,
            params=params,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error validating resource: {e}", file=sys.stderr)
        raise


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
            is_valid = result.get("valid", False)
            status = "PASSED" if is_valid else "FAILED"
            print(f"{file_path}: {status}")
            if is_valid:
                passed += 1
            else:
                failed += 1
                failed_files.append(file_path)
        except Exception as e:
            print(f"{file_path}: ERROR - {e}", file=sys.stderr)
            failed += 1
            failed_files.append(file_path)

    print(f"\nValidation complete. {passed}/{total} files PASSED, {failed} FAILED.")
    if failed > 0:
        print("Failed files:")
        for f in failed_files:
            print(f"  {f}")
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
