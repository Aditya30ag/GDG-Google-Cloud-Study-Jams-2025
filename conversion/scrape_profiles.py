#!/usr/bin/env python3
"""
scrape_profiles.py

Polite crawler to fetch Cloud Skills Boost public profile pages and extract
skill badge names and counts. It reads an input JSON (default: main/data.json)
and updates the fields:

- '# of Skill Badges Completed'
- 'Names of Completed Skill Badges'

The script is heuristic: Cloud Skills Boost HTML structure may change, so it
tries several selectors and fallback strategies. Use --dry-run to preview
changes without writing the output file.

Usage examples:
  python conversion/scrape_profiles.py --input main/data.json --output main/data.json
  python conversion/scrape_profiles.py --input main/data.json --dry-run --delay 1.5

Notes:
 - Be respectful: default delay=1.0s between requests and optional concurrency.
 - If you want me to run this against your dataset now, tell me and I'll run
   it here (it will make outbound HTTP requests).
"""
import argparse
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import escape

try:
    import requests
    from bs4 import BeautifulSoup
except Exception:
    print("Missing dependencies. Install with: pip install -r conversion/requirements.txt", file=sys.stderr)
    raise


def extract_badges_from_html(text):
    soup = BeautifulSoup(text, "html.parser")
    badges = []

    # Helper to skip obvious negative messages (e.g. "hasn't earned any badges yet")
    def is_negative_phrase(s: str) -> bool:
        s2 = s.lower()
        return "hasn't earned" in s2 or "has not earned" in s2 or "no badges" in s2 or "no skill badges" in s2

    seen = set()

    # Primary targeted strategy: look for profile-badges/profile-badge blocks (observed on Cloud Skills Boost)
    # These blocks contain a title span and an earned-date span.
    try:
        blocks = soup.select('.profile-badges .profile-badge')
    except Exception:
        blocks = []

    for blk in blocks:
        # title is often in a span with class containing 'ql-title-medium'
        title_el = blk.find(lambda t: t.name == 'span' and t.get('class') and any('ql-title' in c for c in t.get('class')))
        if not title_el:
            # fallback: first text-bearing element after image/anchor
            title_el = blk.find(['span', 'div'], text=True)
        if title_el:
            title = title_el.get_text(separator=' ', strip=True)
        else:
            title = ''

        # earned date often in a sibling span with class containing 'ql-body-medium' or 'l-mbs'
        earned_el = blk.find(lambda t: t.name == 'span' and t.get('class') and (any('ql-body' in c for c in t.get('class')) or any('l-mbs' in c for c in t.get('class'))))
        earned = earned_el.get_text(separator=' ', strip=True) if earned_el else ''

        if title:
            # normalize badge name and attach [Skill Badge] for compatibility with existing data
            bnorm = re.sub(r'\s+', ' ', title).strip()
            if earned:
                # Optionally include earned date in parentheses to preserve that info
                bnorm = f"{bnorm} [Skill Badge]"
            else:
                bnorm = f"{bnorm} [Skill Badge]"
            if bnorm not in seen:
                seen.add(bnorm)
                badges.append(bnorm)

    # If we found targeted blocks, return them (they are authoritative)
    if badges:
        return badges

    # Primary strategy: find explicit badge containers by class name patterns and extract list items / anchors inside them.
    container_class_patterns = [r'badg', r'skill-badg', r'badge-list', r'badges-list', r'public-profile__badges', r'profile-badges']
    containers = []
    for pat in container_class_patterns:
        containers.extend(soup.find_all(class_=re.compile(pat, re.I)))

    for cont in containers:
        for el in cont.find_all(['a', 'li', 'div', 'span'], recursive=True):
            txt = el.get_text(separator=' ', strip=True)
            if not txt:
                continue
            if is_negative_phrase(txt):
                continue
            href = el.get('href', '') if el.name == 'a' else ''
            # Accept if it explicitly looks like a skill badge: contains '[Skill Badge]' or 'skill badge' or the anchor points to a badge-like path
            if '[Skill Badge]' in txt or 'skill badge' in txt.lower() or '/badges' in href or '/quests' in href or '/skill' in href:
                bnorm = re.sub(r'\s+', ' ', txt).strip()
                if bnorm and bnorm not in seen:
                    seen.add(bnorm)
                    badges.append(bnorm)

    # Secondary strategy: anchors that look like badge links anywhere on the page (be conservative)
    for a in soup.find_all('a', href=True):
        href = a['href']
        txt = a.get_text(separator=' ', strip=True)
        if not txt:
            continue
        if is_negative_phrase(txt):
            continue
        if '/badges' in href or 'badge' in href.lower() or '/quests' in href:
            bnorm = re.sub(r'\s+', ' ', txt).strip()
            if bnorm and bnorm not in seen:
                seen.add(bnorm)
                badges.append(bnorm)

    # Tertiary fallback: regex for bracketed badge names (rare but useful)
    for m in re.finditer(r"([A-Za-z0-9\-:,() '&]+\[Skill Badge\])", text):
        b = m.group(1).strip()
        if is_negative_phrase(b):
            continue
        if b not in seen:
            seen.add(b)
            badges.append(b)

    return badges


def fetch_profile(url, timeout=15):
    headers = {
    'User-Agent': 'GDSC-Bennett-Completion-Tracker-Bot/1.0 (+https://github.com/Chitresh-code)'
    }
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
    except Exception as e:
        return {'url': url, 'error': str(e), 'badges': []}

    badges = extract_badges_from_html(r.text)
    return {'url': url, 'badges': badges}


def worker(entry, timeout=15, delay=1.0):
    url = entry.get('Google Cloud Skills Boost Profile URL') or entry.get('Profile URL')
    if not url:
        return (entry, None, 'no-url')
    result = fetch_profile(url, timeout=timeout)
    time.sleep(delay)
    return (entry, result, None)


def main():
    parser = argparse.ArgumentParser(description='Crawl Cloud Skills Boost profiles and update badge counts in JSON')
    parser.add_argument('--input', '-i', default='main/data.json')
    parser.add_argument('--output', '-o', default='main/data.json')
    parser.add_argument('--concurrency', '-c', type=int, default=10)
    parser.add_argument('--delay', '-d', type=float, default=1.0, help='Delay (s) between requests per worker')
    parser.add_argument('--timeout', type=int, default=15)
    parser.add_argument('--retries', '-r', type=int, default=1, help='Number of retry attempts for failed fetches (default 1)')
    parser.add_argument('--dry-run', action='store_true', help='Do not write output file; just show changes')
    parser.add_argument('--max', type=int, default=0, help='Maximum number of profiles to process (0 = all)')
    args = parser.parse_args()

    with open(args.input, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f'Loaded {len(data)} records from {args.input}')

    to_process = data if args.max <= 0 else data[:args.max]

    updated = 0
    errors = 0
    failed_fetches = []  # list of tuples: (entry, url, error_msg)

    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futures = [ex.submit(worker, entry, args.timeout, args.delay) for entry in to_process]
        for fut in as_completed(futures):
            entry, result, err = fut.result()
            if err == 'no-url':
                continue
            if result is None:
                errors += 1
                continue

            url = result.get('url')
            badges = result.get('badges', [])
            if not badges and result.get('error'):
                errors += 1
                err_msg = result.get('error')
                print(f'Error fetching {url}: {err_msg}')
                failed_fetches.append((entry, url, err_msg))
                continue

            # Find the original entry in data list and update fields
            # match by profile url
            matched = None
            for e in data:
                if (e.get('Google Cloud Skills Boost Profile URL') or e.get('Profile URL')) == url:
                    matched = e
                    break

            if not matched:
                # sometimes URL normalization differs; try contains
                for e in data:
                    u = e.get('Google Cloud Skills Boost Profile URL') or e.get('Profile URL')
                    if u and url in u or (u and u in url):
                        matched = e
                        break

            if not matched:
                print(f'Warning: fetched {url} but no matching record found in input')
                continue

            old_count = int(matched.get('# of Skill Badges Completed') or 0)
            new_count = len(badges)
            if new_count > old_count:
                print(f"Update {matched.get('User Name')}: badges {old_count} -> {new_count}")
                matched['# of Skill Badges Completed'] = new_count
                matched['Names of Completed Skill Badges'] = ' | '.join(badges)
                # Recalculate total courses completed (badges + arcade games)
                try:
                    arcade_count = int(matched.get('# of Arcade Games Completed') or 0)
                except Exception:
                    # fallback: try to parse numeric from string
                    try:
                        arcade_count = int(str(matched.get('# of Arcade Games Completed') or '0').strip())
                    except Exception:
                        arcade_count = 0

                matched['# of Courses Completed'] = new_count + arcade_count

                # Update completion flags according to business rule: >=19 skill badges AND >=1 arcade game
                completion_met = (new_count >= 19 and arcade_count >= 1)
                # preserve both possible keys used in data
                if 'All Skill Badges & Games Completed' in matched:
                    matched['All Skill Badges & Games Completed'] = 'Yes' if completion_met else 'No'
                matched['All 3 Pathways Completed - Yes or No'] = 'Yes' if completion_met else 'No'

                # Also update arcade completion short flag if present
                if 'Gen AI Arcade Game Completion' in matched:
                    matched['Gen AI Arcade Game Completion'] = '1' if arcade_count > 0 else '0'

                updated += 1

    # Retry failed fetches if requested
    if args.retries and failed_fetches:
        for attempt in range(1, args.retries + 1):
            if not failed_fetches:
                break
            print(f"Retry attempt {attempt} for {len(failed_fetches)} failed fetches...")
            remaining = []
            for entry, url, prev_err in failed_fetches:
                try:
                    result = fetch_profile(url, timeout=args.timeout)
                except Exception as e:
                    print(f"Retry error fetching {url}: {e}")
                    remaining.append((entry, url, str(e)))
                    time.sleep(args.delay)
                    continue

                if result.get('error'):
                    print(f"Retry error fetching {url}: {result.get('error')}")
                    remaining.append((entry, url, result.get('error')))
                    time.sleep(args.delay)
                    continue

                badges = result.get('badges', [])
                # find matched record by url again
                matched = None
                for e in data:
                    if (e.get('Google Cloud Skills Boost Profile URL') or e.get('Profile URL')) == url:
                        matched = e
                        break
                if not matched:
                    for e in data:
                        u = e.get('Google Cloud Skills Boost Profile URL') or e.get('Profile URL')
                        if u and (url in u or (u and u in url)):
                            matched = e
                            break

                if not matched:
                    print(f'Warning: retry fetched {url} but no matching record found in input')
                    continue

                old_count = int(matched.get('# of Skill Badges Completed') or 0)
                new_count = len(badges)
                if new_count > old_count:
                    print(f"Update (retry) {matched.get('User Name')}: badges {old_count} -> {new_count}")
                    matched['# of Skill Badges Completed'] = new_count
                    matched['Names of Completed Skill Badges'] = ' | '.join(badges)
                    # Recalculate totals and flags as above
                    try:
                        arcade_count = int(matched.get('# of Arcade Games Completed') or 0)
                    except Exception:
                        try:
                            arcade_count = int(str(matched.get('# of Arcade Games Completed') or '0').strip())
                        except Exception:
                            arcade_count = 0

                    matched['# of Courses Completed'] = new_count + arcade_count
                    completion_met = (new_count >= 19 and arcade_count >= 1)
                    if 'All Skill Badges & Games Completed' in matched:
                        matched['All Skill Badges & Games Completed'] = 'Yes' if completion_met else 'No'
                    matched['All 3 Pathways Completed - Yes or No'] = 'Yes' if completion_met else 'No'
                    if 'Gen AI Arcade Game Completion' in matched:
                        matched['Gen AI Arcade Game Completion'] = '1' if arcade_count > 0 else '0'

                    updated += 1
                time.sleep(args.delay)

            failed_fetches = remaining

        if failed_fetches:
            print(f"After {args.retries} retries, {len(failed_fetches)} fetches still failed.")

    print(f'Done. Updated {updated} records, errors: {errors}')

    if not args.dry_run and updated > 0:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f'Wrote updated data to {args.output}')


if __name__ == '__main__':
    main()
