import csv
import json

import argparse
import os
import sys

def csv_to_json(csv_file, json_file):
    """Read data from CSV and convert it to a list of dictionaries, then write to JSON.

    This utility keeps values as strings so the frontend can interpret them
    the same way the author expected. It creates the output directory if
    necessary and writes UTF-8 JSON with indentation for readability.
    """
    raw_rows = []
    with open(csv_file, 'r', newline='', encoding='utf-8') as csvfile:
        csv_reader = csv.DictReader(csvfile)
        for row in csv_reader:
            raw_rows.append(row)

    def int_or_zero(val):
        try:
            return int(val)
        except Exception:
            return 0

    def contains_keyword(haystack, keywords):
        if not haystack:
            return False
        s = haystack.lower()
        for k in keywords:
            if k.lower() in s:
                return True
        return False

    mapped = []
    for r in raw_rows:
        # Try multiple possible header names for each expected frontend field
        name = r.get('User Name') or r.get('Name') or r.get('Full Name') or ''
        profile = r.get('Google Cloud Skills Boost Profile URL') or r.get('Profile URL') or r.get('Google Cloud Profile') or ''

        # Redemption / access code field may be named differently in your CSV
        redemption = r.get('Access Code Redemption Status') or r.get('Campaign Code Redemption Status') or r.get('Campaign Code Redemption Status') or r.get('Access Code Redemption') or ''

        # Arcade games
        arcade_count = int_or_zero(r.get('# of Arcade Games Completed') or r.get('Arcade Games Completed') or r.get('Number of Arcade Games') or r.get('Names of Completed Arcade Games', '').count('|'))
        gen_ai_arcade = '1' if arcade_count > 0 else '0'

        # Skill badges
        badges_count = int_or_zero(r.get('# of Skill Badges Completed') or r.get('Number of Skill Badges') or r.get('# of Skill Badges Completed') or r.get('# of Skill Badges Completed', 0))
        badges_names = r.get('Names of Completed Skill Badges') or r.get('Names of Completed Badges') or r.get('Names of Completed Arcade Games') or ''

        # Heuristic detection for specific pathway completions
        prompt_keywords = ['prompt', 'vertex']
        develop_keywords = ['gemini', 'streamlit', 'genai', 'gen ai', 'gen-ai']

        prompt_completion = '1' if contains_keyword(badges_names, prompt_keywords) else '0'
        develop_completion = '1' if contains_keyword(badges_names, develop_keywords) else '0'

        total_completed = badges_count + arcade_count

        all_three = r.get('All Skill Badges & Games Completed') or r.get('All 3 Pathways Completed - Yes or No') or r.get('All 3 Pathways Completed') or ''
        # Normalize yes/no values
        if isinstance(all_three, str):
            if all_three.strip().lower() in ['yes', 'y', 'true', '1']:
                all_three = 'Yes'
            else:
                all_three = 'No'

        # Preserve original CSV columns requested by the user when present
        preserved = {
            'Access Code Redemption Status': r.get('Access Code Redemption Status') or r.get('Access Code Redemption') or r.get('Access Code Redemption Status') or '',
            'All Skill Badges & Games Completed': r.get('All Skill Badges & Games Completed') or r.get('All Skill Badges & Games Completed') or r.get('All 3 Pathways Completed - Yes or No') or '',
            '# of Skill Badges Completed': r.get('# of Skill Badges Completed') or r.get('# of Skill Badges Completed', ''),
            'Names of Completed Skill Badges': r.get('Names of Completed Skill Badges') or r.get('Names of Completed Badges') or '',
            '# of Arcade Games Completed': r.get('# of Arcade Games Completed') or r.get('# of Arcade Games Completed', ''),
            'Names of Completed Arcade Games': r.get('Names of Completed Arcade Games') or r.get('Names of Completed Arcade Games', '')
        }

        mapped_row = {
            'User Name': name,
            'Google Cloud Skills Boost Profile URL': profile,
            'Campaign Code Redemption Status': redemption,
            'Gen AI Arcade Game Completion': gen_ai_arcade,
            'Prompt Design in Vertex AI Completion': prompt_completion,
            'Develop GenAI Apps with Gemini and Streamlit Completion': develop_completion,
            '# of Courses Completed': total_completed,
            'All 3 Pathways Completed - Yes or No': all_three
        }

        # Merge preserved columns so result contains both mapped fields and originals
        mapped_row.update(preserved)

        mapped.append(mapped_row)

    out_dir = os.path.dirname(json_file) or '.'
    os.makedirs(out_dir, exist_ok=True)
    with open(json_file, 'w', encoding='utf-8') as jsonfile:
        json.dump(mapped, jsonfile, indent=4, ensure_ascii=False)

    print(f"Wrote {len(mapped)} records to {json_file}")

def main():
    parser = argparse.ArgumentParser(description='Convert a CSV of student records to main/data.json')
    parser.add_argument('-i', '--input', default=os.path.join('conversion', 'input.csv'), help='Path to input CSV (default: conversion/input.csv)')
    parser.add_argument('-o', '--output', default=os.path.join('main', 'data.json'), help='Path to output JSON (default: main/data.json)')
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: input file '{args.input}' not found.", file=sys.stderr)
        sys.exit(2)

    csv_to_json(args.input, args.output)

if __name__ == '__main__':
    main()
