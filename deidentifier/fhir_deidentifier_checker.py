from typing import Any, Dict, List, Union, Optional

from fhirpathpy import evaluate


class FHIRDeIdentificationChecker:
    def __init__(self, sensitive_fields: Optional[List[str]] = None):
        # If no sensitive fields are provided, use a default list
        self.sensitive_fields: List[str] = sensitive_fields if sensitive_fields else [
            "Patient.name",
            "Patient.address",
            "Patient.telecom",
            "Patient.birthDate",
            "identifier",
            "Practitioner.name",
            "Practitioner.telecom"
        ]

    def extract_sensitive_data(self, resource: Dict[str, Any]) -> Dict[str, Union[List[Any], None]]:
        """Extract sensitive data from the resource based on predefined sensitive fields."""
        data: Dict[str, Union[List[Any], None]] = {}
        for path in self.sensitive_fields:
            result: List[Any] = evaluate(resource, path)
            data[path] = result if result else None
        return data

    def compare_resources(self, source: Dict[str, Any], de_identified: Dict[str, Any]) -> Dict[
        str, Dict[str, Union[List[Any], None]]]:
        """Compare sensitive data between the source and de-identified resources."""
        source_data: Dict[str, Union[List[Any], None]] = self.extract_sensitive_data(source)
        de_identified_data: Dict[str, Union[List[Any], None]] = self.extract_sensitive_data(de_identified)

        matching_data: Dict[str, Dict[str, Union[List[Any], None]]] = {}
        for path in source_data:
            if source_data[path] is not None and source_data[path] == de_identified_data[path]:
                matching_data[path] = {
                    "source": source_data[path],
                    "de_identified": de_identified_data[path]
                }

        return matching_data

    def is_de_identified(self, source: Dict[str, Any], de_identified: Dict[str, Any]) -> bool:
        """Check if the de-identified resource is properly de-identified by comparing sensitive fields."""
        matching_fields: Dict[str, Dict[str, Union[List[Any], None]]] = self.compare_resources(source, de_identified)
        return not bool(matching_fields)  # True if matching_fields are found, False otherwise
