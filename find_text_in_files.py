import os
import re
import sys

def find_text_in_files(folder, search_text):
    found = False

    # Walk through the folder and its subfolders
    for root, _, files in os.walk(folder):
        for file in files:
            if file.endswith(".json"):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    # print(f"Searching for '{search_text}' in {file_path}")
                    for i, line in enumerate(f, start=1):
                        if re.search(search_text, line, re.IGNORECASE):
                            print(f"'{search_text}' found in {file_path} on line {i}")
                            found = True

    if not found:
        print(f"'{search_text}' not found in any file.")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python find_text.py <folder> <search_text>")
        sys.exit(1)

    input_folder = sys.argv[1]
    input_search_text = sys.argv[2]
    find_text_in_files(folder=input_folder, search_text=input_search_text)
