import requests
import re

url = 'https://www.cloudskillsboost.google/public_profiles/a3415bd8-939a-4569-95b0-9458237b94d7'
headers = {'User-Agent': 'GDSC-Bennett-Completion-Tracker-Bot/1.0 (+https://github.com/Chitresh-code)'}
print('Fetching', url)
resp = requests.get(url, headers=headers, timeout=15)
resp.raise_for_status()
text = resp.text

# Print context lines that mention Earned, Skill Badge, badge, badges, /badges, Earned
patterns = [r'Earned', r'Skill Badge', r'\[Skill Badge\]', r'badge', r'/badges', r'Earned']
lines = text.splitlines()
for i, line in enumerate(lines):
    for p in patterns:
        if re.search(p, line, re.I):
            start = max(0, i-2)
            end = min(len(lines), i+3)
            print('--- Context lines', start, 'to', end)
            for j in range(start, end):
                print(j+1, lines[j].strip())
            print('\n')
            break
