import json
from scrape_profiles import fetch_profile

NAME = 'Saransh Jain'

def find_profile_url(name, datafile='main/data.json'):
    with open(datafile, 'r', encoding='utf-8') as f:
        data = json.load(f)
    for entry in data:
        if entry.get('User Name', '').strip().lower() == name.strip().lower():
            return entry.get('Google Cloud Skills Boost Profile URL') or entry.get('Profile URL')
    return None

url = find_profile_url(NAME)
if not url:
    print('Profile URL not found for', NAME)
else:
    print('Fetching:', url)
    res = fetch_profile(url)
    if res.get('error'):
        print('Error:', res.get('error'))
    else:
        badges = res.get('badges', [])
        print('Badge count:', len(badges))
        for i, b in enumerate(badges, 1):
            print(f'{i}. {b}')
