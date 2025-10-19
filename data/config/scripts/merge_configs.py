import json
import glob
import os
from typing import List

CONFIG_DIR = os.path.dirname(__file__)
DATA_TYPES_CONFIG_DIR = os.path.join(CONFIG_DIR, '../data_types')
RESOURCE_CONFIG_DIR = os.path.join(CONFIG_DIR, '../resources')
OUTPUT_FILE = os.path.join(CONFIG_DIR, '../merged/merged.json')

DEFAULT_CONFIG = "resource.json"

# Replace the id on the person resource with this
SUBSTITUTE_PERSON_ID: str = "e00fe98c-1a5d-4ba9-a7b0-f10228498dc9"

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

merged_rules = []
parameters = None
fhirVersion = None
processingErrors = None

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
            # now iterate the fhir_path_rules and replace the trusted code systems placeholder if present
            for rule in fhir_path_rules:
                rule['path'] = rule['path'].replace('{{TRUSTED_CODE_SYSTEMS}}', trusted_code_system_regex)
                if "replaceWith" in rule:
                    rule['replaceWith'] = rule['replaceWith'].replace('{{SUBSTITUTE_PERSON_ID}}', SUBSTITUTE_PERSON_ID)
            merged_rules.extend(fhir_path_rules)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from {config_path}: {e}")
            raise

# Now read the data types config files and merge their fhirPathRules
# We do it after resoure files to allow resource files to override data type rules if needed
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
            for rule in fhir_path_rules:
                rule['path'] = rule['path'].replace('{{TRUSTED_CODE_SYSTEMS}}', trusted_code_system_regex)
                if "replaceWith" in rule:
                    rule['replaceWith'] = rule['replaceWith'].replace('{{SUBSTITUTE_PERSON_ID}}', SUBSTITUTE_PERSON_ID)
            merged_rules.extend(fhir_path_rules)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from {config_path}: {e}")
            raise

# Add DEFAULT_CONFIG from resource.json at the end
with open(os.path.join(RESOURCE_CONFIG_DIR, DEFAULT_CONFIG), 'r') as f:
    try:
        data = json.load(f)
        merged_rules.extend(data.get('fhirPathRules', []))
        # Use parameters, fhirVersion, processingErrors from the resource file
        if parameters is None:
            parameters = data.get('parameters', {})
        if fhirVersion is None:
            fhirVersion = data.get('fhirVersion', 'R4')
        if processingErrors is None:
            processingErrors = data.get('processingErrors', 'raise')
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {DEFAULT_CONFIG}: {e}")
        raise

# Redact all other fields that were not matched by previous rules
merged_rules.append({"path": "Resource", "method": "redact"})

# Write the merged config with defaultRule
with open(OUTPUT_FILE, 'w') as output_file:
    json.dump({
        'fhirVersion': fhirVersion,
        'processingErrors': processingErrors,
        'fhirPathRules': merged_rules,
        'parameters': parameters
    }, output_file, indent=2)

print(f"Merged {len(config_files)} configs into {OUTPUT_FILE} with defaultRule set to redact.")
