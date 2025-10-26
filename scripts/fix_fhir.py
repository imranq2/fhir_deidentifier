import os
import json

def prefix_urn_oid_system(obj):
    """
    Recursively traverse obj. If a dict has a key 'system' whose value is a string starting with a digit,
    prefix 'urn:oid:' if not already present.
    """
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "system" and isinstance(v, str) and v and v[0].isdigit() and not v.startswith("urn:oid:"):
                obj[k] = "urn:oid:" + v
            else:
                prefix_urn_oid_system(v)
    elif isinstance(obj, list):
        for item in obj:
            prefix_urn_oid_system(item)
    return obj

def process_json_files(input_dir, output_dir=None):
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.endswith('.json'):
                input_path = os.path.join(root, file)
                with open(input_path, 'r') as f:
                    try:
                        data = json.load(f)
                    except Exception as e:
                        print(f"Skipping {input_path}: {e}")
                        continue
                prefix_urn_oid_system(data)
                # Write back to the same file or to output_dir if specified
                if output_dir:
                    rel_path = os.path.relpath(input_path, input_dir)
                    output_path = os.path.join(output_dir, rel_path)
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                else:
                    output_path = input_path
                with open(output_path, 'w') as f:
                    json.dump(data, f, indent=2)
                print(f"Processed {input_path} -> {output_path}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Prefix 'urn:oid:' to system fields in JSON files under a directory.")
    parser.add_argument('--input', type=str, default='data/input', help='Input directory containing JSON files')
    parser.add_argument('--output', type=str, default=None, help='Optional output directory (if not set, overwrites input files)')
    args = parser.parse_args()
    process_json_files(args.input, args.output)

