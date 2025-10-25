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
        validator_url: str = "http://localhost:8080/validate",
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
        print("Usage: python validate_fhir.py <path-to-fhir-json-file>")
        sys.exit(1)

    file_path = Path(sys.argv[1])

    try:
        result = validate_fhir_resource(file_path)
        print(json.dumps(result, indent=2))

        # Check if validation passed
        if result.get("valid", False):
            print("\n✓ Validation PASSED", file=sys.stderr)
            sys.exit(0)
        else:
            print("\n✗ Validation FAILED", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
