import json
import glob
import os
from typing import List, Dict, Any

CONFIG_DIR = os.path.dirname(__file__)
DATA_TYPES_CONFIG_DIR = os.path.join(CONFIG_DIR, '../data_types')
RESOURCE_CONFIG_DIR = os.path.join(CONFIG_DIR, '../resources')
OUTPUT_FILE = os.path.join(CONFIG_DIR, '../merged/merged.json')

DEFAULT_CONFIG = "resource.json"

trusted_code_systems: List[str] = [
    "http://loinc.org",
    "http://snomed.info/sct",
    "http://hl7.org/fhir/sid/icd-10",
    "http://hl7.org/fhir/sid/icd-9",
    "http://unitsofmeasure.org",
    "http://www.nlm.nih.gov/research/umls/rxnorm",
    "http://terminology.hl7.org",
    "http://www.ama-assn.org/go/cpt",
    "http://fhir.icanbwell.com/4_0_0/CodeSystem/medicationstatement",
    "http://www.whocc.no/atc",
    "http://hl7.org/fhir/us/core/CodeSystem/condition-category"
]

trusted_code_systems_list: str = '|'.join([cs.replace('http://', '').replace('https://', '').replace('.', r'.').replace('/', r'\/') for cs in trusted_code_systems])
trusted_code_system_regex = f"^https?://({trusted_code_systems_list})"
print(f"Using trusted code systems regex: {trusted_code_system_regex}")

placeholder_replacements: Dict[str, str] = {
    "SUBSTITUTE_PERSON_ID": "e00fe98c-1a5d-4ba9-a7b0-f10228498dc9",
    "SUBSTITUTE_PERSON_NAME": "Jane Doe",
    "TRUSTED_CODE_SYSTEMS": trusted_code_system_regex,
    "PRACTITIONER_NAME_1": "Doogie Howser, MD",
    "PRACTITIONER_NAME_2": "Gregory House, MD",
    "PRACTITIONER_NAME_3": "Meredith Grey, MD",
    "PRACTITIONER_NAME_4": "Christopher Turk, MD",
    "PRACTITIONER_NAME_5": "John Dorian, MD",
    "PRACTITIONER_UUID_1": "e985b181-ed44-42bf-94d0-f09a4fe72d10",
    "PRACTITIONER_UUID_2": "078e6f48-495d-4e80-843e-af3cd64b37d8",
    "PRACTITIONER_UUID_3": "5dcf1d7d-e880-44f3-8fa0-39edf02439a8",
    "PRACTITIONER_UUID_4": "2548693e-f44e-44b6-a905-002dd124bbb5",
    "PRACTITIONER_UUID_5": "e3112d92-ced0-42ad-bccf-ede4721adcf4",
    "ORGANIZATION_NAME_1": "South Medical Center",
    "ORGANIZATION_NAME_2": "City Medical Center",
    "ORGANIZATION_UUID_1": "2500b32e-88e1-4e65-af2b-0bddca822f09",
    "ORGANIZATION_UUID_2": "36cf9f91-4022-4d20-9dad-7ab0ebb3fe0e",
    "LOCATION_NAME_1": "South Medical Center Main Campus",
    "LOCATION_NAME_2": "City Medical Center Downtown Clinic",
    "LOCATION_UUID_1": "dbfb7108-1faf-4abd-a202-89fc3a1a18c5",
    "LOCATION_UUID_2": "3420266f-0e96-48b6-9996-fddd6d59b34f",
}



limit_to_configs = None

# List all config files except the output and the merge script itself
config_files = sorted(
    [
        f for f in glob.glob(os.path.join(RESOURCE_CONFIG_DIR, '*.json'))
        if os.path.basename(f) != DEFAULT_CONFIG and (
            not limit_to_configs or os.path.basename(f) in limit_to_configs
    )
    ]
)

config_names_text = '\n'.join([os.path.basename(f) for f in config_files])
print(f"Using following config files for merging:\n{config_names_text}")

def replace_placeholders(*, fhir_path_rules: List[Dict[str,Any]]) -> List[Dict[str,Any]]:
    # now iterate the fhir_path_rules and replace the trusted code systems placeholder if present
    for rule in fhir_path_rules:
        for placeholder, placeholder_value in placeholder_replacements.items():
            rule['path'] = rule['path'].replace('{{' + placeholder + '}}', placeholder_value)
            if "replaceWith" in rule:
                if isinstance(rule["replaceWith"], str):
                    rule['replaceWith'] = rule['replaceWith'].replace('{{' + placeholder + '}}', placeholder_value)
                elif isinstance(rule["replaceWith"], dict):
                    for key in rule['replaceWith']:
                        rule['replaceWith'][key] = rule['replaceWith'][key].replace('{{' + placeholder + '}}', placeholder_value)
            if "cases" in rule:
                cases: Dict[str, str] = rule['cases']
                for case_key in cases:
                    cases[case_key] = cases[case_key].replace('{{' + placeholder + '}}', placeholder_value)

    return fhir_path_rules

def load_configs():
    merged_rules = []
    parameters = None
    fhir_version = None
    processing_errors = None

    # Read resource config files and merge their fhirPathRules
    for config_path in config_files:
        with open(config_path, 'r') as f:
            try:
                data = json.load(f)
                fhir_path_rules = data.get('fhirPathRules', [])
                # check that all rules begin with the resource type from the filename
                resource_type_upper = os.path.splitext(os.path.basename(config_path))[0].upper()
                for rule in fhir_path_rules:
                    if not rule['path'].upper().startswith(resource_type_upper):
                        raise ValueError(
                            f"Rule path '{rule['path']}' does not start with resource type '{resource_type_upper}' in file {config_path}."
                            " If you are defining global rules then add them to resource.json instead."
                        )
                fhir_path_rules = replace_placeholders(fhir_path_rules=fhir_path_rules)
                merged_rules.extend(fhir_path_rules)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON from {config_path}: {e}")
                raise

    # Now read the data types config files and merge their fhirPathRules
    # We do it after resource files to allow resource files to override data type rules if needed
    data_type_config_files = sorted(
        glob.glob(os.path.join(DATA_TYPES_CONFIG_DIR, '*.json'))
    )
    data_type_config_names_text = '\n'.join([os.path.basename(f) for f in data_type_config_files])
    print(f"Using following data_type config files for merging:\n{data_type_config_names_text}")
    for config_path in data_type_config_files:
        with open(config_path, 'r') as f:
            try:
                data = json.load(f)
                fhir_path_rules = data.get('fhirPathRules', [])
                fhir_path_rules = replace_placeholders(fhir_path_rules=fhir_path_rules)
                merged_rules.extend(fhir_path_rules)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON from {config_path}: {e}")
                raise

    # Add DEFAULT_CONFIG from resource.json at the end
    with open(os.path.join(RESOURCE_CONFIG_DIR, DEFAULT_CONFIG), 'r') as f:
        try:
            data = json.load(f)
            fhir_path_rules = data.get('fhirPathRules', [])
            fhir_path_rules = replace_placeholders(fhir_path_rules=fhir_path_rules)
            merged_rules.extend(fhir_path_rules)
            # Use parameters, fhir_version, processing_errors from the resource file
            if parameters is None:
                parameters = data.get('parameters', {})
            if fhir_version is None:
                fhir_version = data.get('fhirVersion', 'R4')
            if processing_errors is None:
                processing_errors = data.get('processingErrors', 'raise')
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from {DEFAULT_CONFIG}: {e}")
            raise

    # Redact all other fields that were not matched by previous rules
    merged_rules.append({"path": "Resource", "method": "redact"})

    # Write the merged config with defaultRule
    with open(OUTPUT_FILE, 'w') as output_file:
        json.dump({
            'fhirVersion': fhir_version,
            'processingErrors': processing_errors,
            'fhirPathRules': merged_rules,
            'parameters': parameters
        }, output_file, indent=2)

    print(f"Merged {len(config_files)} configs into {OUTPUT_FILE} with defaultRule set to redact.")

if __name__ == "__main__":
    load_configs()