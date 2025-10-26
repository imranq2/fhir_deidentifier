import os
import json
import uuid

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

def is_valid_uuid(val):
    try:
        uuid.UUID(str(val))
        return True
    except Exception:
        return False

def get_source_assigning_authority(meta):
    if not isinstance(meta, dict):
        return None
    security = meta.get('security')
    if isinstance(security, list):
        for sec in security:
            if isinstance(sec, dict) and sec.get('code') == 'sourceAssigningAuthority':
                # Try value, then system, then display
                return sec.get('value') or sec.get('system') or sec.get('display')
    return None


def fix_id_with_uuidv5(obj, namespace=uuid.NAMESPACE_OID):
    """
    Recursively traverse obj. If a dict has an 'id' that is not a UUID, replace it with a uuidv5
    using the id and the value of the sourceAssigningAuthority security tag from meta.
    """
    if isinstance(obj, dict):
        if 'id' in obj and isinstance(obj['id'], str) and not is_valid_uuid(obj['id']):
            source_assigning_authority = None
            if 'meta' in obj:
                source_assigning_authority = get_source_assigning_authority(obj['meta'])
            if source_assigning_authority:
                name = obj['id'] + str(source_assigning_authority)
            else:
                name = obj['id']
            obj['id'] = str(uuid.uuid5(namespace, name))
        for v in obj.values():
            fix_id_with_uuidv5(v, namespace)
    elif isinstance(obj, list):
        for item in obj:
            fix_id_with_uuidv5(item, namespace)
    return obj

def fix_reference_with_uuid_extension(obj):
    """
    Recursively traverse obj. If a dict has a 'reference' field containing {resourceType}/{id} and id is not a uuid,
    find the extension with id 'uuid' and use that value for 'id' in the reference.
    """
    import re
    uuid_regex = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')
    if isinstance(obj, dict):
        ref = obj.get('reference')
        if isinstance(ref, str):
            parts = ref.split('/')
            if len(parts) == 2:
                resource_type, ref_id = parts
                # Only act if id is not a uuid
                if not uuid_regex.match(ref_id):
                    # Look for extension with id 'uuid'
                    extensions = obj.get('extension')
                    if isinstance(extensions, list):
                        for ext in extensions:
                            if isinstance(ext, dict) and ext.get('id') == 'uuid' and 'value' in ext:
                                new_uuid = ext['value']
                                if uuid_regex.match(new_uuid):
                                    obj['reference'] = f"{resource_type}/{new_uuid}"
                                    break
        for v in obj.values():
            fix_reference_with_uuid_extension(v)
    elif isinstance(obj, list):
        for item in obj:
            fix_reference_with_uuid_extension(item)
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
                fix_id_with_uuidv5(data)
                fix_reference_with_uuid_extension(data)
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
