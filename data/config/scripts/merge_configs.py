import json
import glob
import os

CONFIG_DIR = os.path.dirname(__file__)
RESOURCE_CONFIG_DIR = os.path.join(CONFIG_DIR, '../resources')
OUTPUT_FILE = os.path.join(CONFIG_DIR, '../merged/merged.json')

DEFAULT_CONFIG = "resource.json"

limit_to_configs = [
    "patient.json",
    "person.json",
]

# List all config files except the output and the merge script itself
config_files = sorted(
    [
        f for f in glob.glob(os.path.join(RESOURCE_CONFIG_DIR, '*.json'))
        if os.path.basename(f) != DEFAULT_CONFIG and (
            not limit_to_configs or os.path.basename(f) in limit_to_configs
    )
    ]
)

merged_rules = []
parameters = None
fhirVersion = None
processingErrors = None

for config_path in config_files:
    with open(config_path, 'r') as f:
        try:
            data = json.load(f)
            fhir_path_rules = data.get('fhirPathRules', [])
            # check that all rules begin with the resource type from the filename
            resource_type = os.path.splitext(os.path.basename(config_path))[0].capitalize()
            for rule in fhir_path_rules:
                if not rule['path'].startswith(resource_type):
                    raise ValueError(f"Rule path '{rule['path']}' does not start with resource type '{resource_type}' in file {config_path}")
            merged_rules.extend(fhir_path_rules)
            # Use parameters, fhirVersion, processingErrors from the first file
            if parameters is None:
                parameters = data.get('parameters', {})
            if fhirVersion is None:
                fhirVersion = data.get('fhirVersion', 'R4')
            if processingErrors is None:
                processingErrors = data.get('processingErrors', 'raise')
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from {config_path}: {e}")
            raise

# Add DEFAULT_CONFIG at the end
with open(os.path.join(RESOURCE_CONFIG_DIR, DEFAULT_CONFIG), 'r') as f:
    try:
        data = json.load(f)
        merged_rules.extend(data.get('fhirPathRules', []))
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {DEFAULT_CONFIG}: {e}")
        raise

# Redact all other resources
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
