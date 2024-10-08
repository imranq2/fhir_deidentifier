import json

from fastapi.testclient import TestClient


def test_health_check(rest_client: TestClient):
    """Test the /health endpoint"""
    response = rest_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "Healthy"}


def test_anonymize_success(rest_client):
    print("")
    """Test the /anonymize endpoint with valid input"""
    config = {
        "fhirVersion": "R4",
        "processingError": "raise",
        "fhirPathRules": [
            {"path": "nodesByType('Extension')", "method": "redact"},
            {"path": "Organization.identifier", "method": "keep"},
            {"path": "nodesByType('Address').country", "method": "keep"},
            {"path": "Resource.id", "method": "cryptoHash"},
            {"path": "nodesByType('Reference').reference", "method": "cryptoHash"},
            {"path": "Group.name", "method": "redact"},
            {
                "path": "Patient.birthDate",
                "method": "dateshift"
            },
        ],
        "parameters": {
            "dateShiftKey": "3f49ef04-60a4-4c89-85a3-df2eae5489ae",
            "cryptoHashKey": "3f49ef04-60a4-4c89-85a3-df2eae5489ae",
            "encryptKey": "",
            "enablePartialAgesForRedact": True
        }
    }
    resource = {
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
    }

    response = rest_client.post("/anonymize", json={
        "config": config,
        "resource": resource
    })

    assert response.status_code == 200
    assert response.json() == {'birthDate': '1975-01-25',
                               'gender': 'male',
                               'id': '0d9b28fe8cc6aa8ab33f70305576fca5431b0d9339ac83d17e4d4ca882fae668',
                               'meta': {'security': [{'code': 'CRYTOHASH',
                                                      'display': 'cryptographic hash function',
                                                      'system': 'http://terminology.hl7.org/CodeSystem/v3-ObservationValue'},
                                                     {'code': 'PERTURBED',
                                                      'display': 'exact value is replaced with another exact '
                                                                 'value'}]},
                               'name': [{'family': 'Doe', 'given': ['John']}],
                               'resourceType': 'Patient'}


def test_anonymize_invalid_input(rest_client):
    print("")
    """Test the /anonymize endpoint with invalid input (expect failure)"""
    config = {}  # Empty configuration JSON
    resource = {}  # Empty FHIR resource

    response = rest_client.post("/anonymize", json={
        "config": config,
        "resource": resource
    })

    assert response.status_code == 500
    print(response.json())
    assert "AnonymizerConfigurationManager" in response.json()["detail"]
