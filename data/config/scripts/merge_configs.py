import json
import glob
import os

CONFIG_DIR = os.path.dirname(__file__)
RESOURCE_CONFIG_DIR = os.path.join(CONFIG_DIR, '../resources')
OUTPUT_FILE = os.path.join(CONFIG_DIR, '../merged/merged.json')

# List all config files except the output and the merge script itself
config_files = sorted(
    [
        f for f in glob.glob(os.path.join(RESOURCE_CONFIG_DIR, '*.json'))
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
            merged_rules.extend(data.get('fhirPathRules', []))
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
