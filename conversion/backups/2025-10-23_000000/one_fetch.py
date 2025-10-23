from scrape_profiles import fetch_profile

url = "https://www.cloudskillsboost.google/public_profiles/d6b7dfd0-f265-4709-b6a6-828bf0e8945f"
res = fetch_profile(url)
print('Fetched URL:', res.get('url'))
if res.get('error'):
    print('Error:', res.get('error'))
else:
    badges = res.get('badges', [])
    print('Badge count:', len(badges))
    for i, b in enumerate(badges, 1):
        print(f'{i}. {b}')
