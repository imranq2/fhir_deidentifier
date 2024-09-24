from typing import Dict, Any, List, Union

from fastapi.testclient import TestClient

from deidentifier.fhir_deidentifier_checker import FHIRDeIdentificationChecker


def test_anonymize_bundle(rest_client: TestClient) -> None:
    print("")
    """Test the /anonymize endpoint with valid input"""

    # https://github.com/microsoft/Tools-for-Health-Data-Anonymization/blob/master/docs/FHIR-anonymization.md#fhir-path-rules
    config = {
        "fhirVersion": "R4",
        "processingError": "raise",
        "fhirPathRules": [
            # resource rules
            {"path": "nodesByType('Extension')", "method": "redact"},
            {"path": "Resource.id", "method": "cryptoHash"},
            {"path": "nodesByType('Reference').reference", "method": "cryptoHash"},
            {"path": "Group.name", "method": "redact"},
            # Patient rules
            {
                "path": "Patient.birthDate",
                "method": "generalize",
                "cases": {
                    "$this <= @1935-01-01": "@1935-01-01",
                    "$this >= @1935-01-01": "@2010-01-01"
                },
                "otherValues": "redact"
            },
            {"path": "Patient.gender", "method": "keep"},
            # HumanName rules
            {"path": "nodesByType('HumanName').use", "method": "keep"},
            {"path": "nodesByType('HumanName').family", "method": "cryptoHash"},
            {"path": "nodesByType('HumanName').given", "method": "cryptoHash"},
            # Address rules
            {"path": "nodesByType('Address').country", "method": "keep"},
            {"path": "nodesByType('Address').city", "method": "substitute", "replaceWith": "example city"},
            {
                "path": "nodesByType('Address').postalCode",
                "method": "generalize",
                "cases": {
                    "$this.startsWith('123') or $this.startsWith('234')": "$this.substring(0,2)+'0000'",
                },
                "otherValues": "redact"
            },
            # by default remove all fields
            {"path": "Resource", "method": "redact"},
        ],
        "parameters": {
            "dateShiftKey": "3f49ef04-60a4-4c89-85a3-df2eae5489ae",
            "cryptoHashKey": "3f49ef04-60a4-4c89-85a3-df2eae5489ae",
            "encryptKey": "",
            "enablePartialAgesForRedact": True
        }
    }
    resource = {
        "resourceType": "Bundle",
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "example",
                    "name": [
                        {
                            "use": "official",
                            "family": "Doe",
                            "given": ["John"]
                        }
                    ],
                    "gender": "male",
                    "birthDate": "1974-12-25",
                    "address": [
                        {
                            "use": "home",
                            "line": ["123 Main St"],
                            "city": "Anytown",
                            "state": "NY",
                            "postalCode": "12345",
                            "country": "US"
                        }
                    ]
                }
            }
        ]
    }

    response = rest_client.post("/anonymize", json={
        "config": config,
        "resource": resource
    })

    assert response.status_code == 200, response.text
    de_identified_resource: Dict[str, Any] = response.json()
    assert de_identified_resource == {
        'entry': [{'resource': {'address': [{'city': 'example city',
                                             'country': 'US',
                                             'postalCode': '120000'}],
                                'birthDate': '2010-01-01',
                                'gender': 'male',
                                'id': '0d9b28fe8cc6aa8ab33f70305576fca5431b0d9339ac83d17e4d4ca882fae668',
                                'meta': {'security': [{'code': 'REDACTED',
                                                       'display': 'redacted',
                                                       'system': 'http://terminology.hl7.org/CodeSystem/v3-ObservationValue'},
                                                      {'code': 'CRYTOHASH',
                                                       'display': 'cryptographic hash '
                                                                  'function',
                                                       'system': 'http://terminology.hl7.org/CodeSystem/v3-ObservationValue'},
                                                      {'code': 'SUBSTITUTED',
                                                       'display': 'exact value is '
                                                                  'replaced with a '
                                                                  'predefined value'},
                                                      {'code': 'GENERALIZED',
                                                       'display': 'exact value is '
                                                                  'replaced with a '
                                                                  'general value'}]},
                                'name': [{'family': 'bc537e047f20d40fc0b8ee30a078cc883e6acc4cbc4062c7fa588df228cbd94f',
                                          'given': ['29ffea82697f244f288787c73c40f12bcb5b7a54e45e4ae25c4ed92637bafe1c'],
                                          'use': 'official'}],
                                'resourceType': 'Patient'}}],
        'meta': {'security': [{'code': 'REDACTED',
                               'display': 'redacted',
                               'system': 'http://terminology.hl7.org/CodeSystem/v3-ObservationValue'},
                              {'code': 'CRYTOHASH',
                               'display': 'cryptographic hash function',
                               'system': 'http://terminology.hl7.org/CodeSystem/v3-ObservationValue'},
                              {'code': 'SUBSTITUTED',
                               'display': 'exact value is replaced with a predefined '
                                          'value'},
                              {'code': 'GENERALIZED',
                               'display': 'exact value is replaced with a general '
                                          'value'}]},
        'resourceType': 'Bundle'
    }

    # Check if the de-identified resource is properly de-identified by comparing sensitive fields
    checker = FHIRDeIdentificationChecker()
    matching_fields: Dict[str, Dict[str, Union[List[Any], None]]] = checker.compare_resources(
        source=resource,
        de_identified=de_identified_resource
    )
    assert not bool(matching_fields), matching_fields
