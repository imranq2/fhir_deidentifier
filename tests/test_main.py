import pytest
from fastapi.testclient import TestClient



def test_health_check(rest_client: TestClient):
    """Test the /health endpoint"""
    response = rest_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "Healthy"}


def test_anonymize_success(rest_client):
    """Test the /anonymize endpoint with valid input"""
    config_json = """{
      "fhirVersion": "R4",
      "processingError":"raise",
      "fhirPathRules": [
        {"path": "nodesByType('Extension')", "method": "redact"},
        {"path": "Organization.identifier", "method": "keep"},
        {"path": "nodesByType('Address').country", "method": "keep"},
        {"path": "Resource.id", "method": "cryptoHash"},
        {"path": "nodesByType('Reference').reference", "method": "cryptoHash"},
        {"path": "Group.name", "method": "redact"}
      ],
      "parameters": {
        "dateShiftKey": "",
        "cryptoHashKey": "",
        "encryptKey": "",
        "enablePartialAgesForRedact": true
      }
    }"""
    json_content = """{
          "resourceType": "Patient",
          "id": "example",
          "name": [
            {
              "family": "Doe",
              "given": ["John"]
            }
          ],
          "gender": "male",
          "birthDate": "1974-12-25"
        }        """

    response = rest_client.post("/anonymize", json={
        "config_json": config_json,
        "json_content": json_content
    })

    assert response.status_code == 200
    assert response.json() == {"resourceType": "Patient", "id": "anonymized"}


def test_anonymize_invalid_input(rest_client):
    """Test the /anonymize endpoint with invalid input (expect failure)"""
    config_json = """{}"""  # Empty configuration JSON
    json_content = """{}"""  # Empty FHIR resource

    response = rest_client.post("/anonymize", json={
        "config_json": config_json,
        "json_content": json_content
    })

    assert response.status_code == 500
    assert "AnonymizerConfigurationManager" in response.json()["detail"]
