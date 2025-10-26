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
    arcade_games = []

    # Helper to skip obvious negative messages (e.g. "hasn't earned any badges yet")
    def is_negative_phrase(s: str) -> bool:
        s2 = s.lower()
        return "hasn't earned" in s2 or "has not earned" in s2 or "no badges" in s2 or "no skill badges" in s2

    # Helper to check if a title is an arcade game
    def is_arcade_game(title: str) -> bool:
        title_lower = title.lower()
        # Arcade games on Cloud Skills Boost are usually explicit "Level X:" items
        # Avoid classifying any title that merely mentions "generative ai" as an
        # arcade game (e.g. "Develop Gen AI Apps with Gemini and Streamlit").
        # Only treat titles containing an explicit "Level <number>" marker as
        # arcade games.
        # Match examples: "Level 1: ...", "Level 2 - ...", "level 3: Generative AI"
        if re.search(r"\blevel\s*\d+\b", title_lower):
            return True
        return False

    seen_badges = set()
    seen_arcade = set()

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
            # normalize badge name
            bnorm = re.sub(r'\s+', ' ', title).strip()
            
            # Check if this is an arcade game or a skill badge
            if is_arcade_game(bnorm):
                # This is an arcade game
                bnorm_game = f"{bnorm} [Game]"
                if bnorm_game not in seen_arcade:
                    seen_arcade.add(bnorm_game)
                    arcade_games.append(bnorm_game)
            else:
                # This is a skill badge
                bnorm_badge = f"{bnorm} [Skill Badge]"
                if bnorm_badge not in seen_badges:
                    seen_badges.add(bnorm_badge)
                    badges.append(bnorm_badge)

    # If we found targeted blocks, return them (they are authoritative)
    if badges or arcade_games:
        return {'badges': badges, 'arcade_games': arcade_games}

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
                # Check if it's an arcade game
                if is_arcade_game(bnorm):
                    bnorm_game = f"{bnorm} [Game]" if '[Game]' not in bnorm else bnorm
                    if bnorm_game not in seen_arcade:
                        seen_arcade.add(bnorm_game)
                        arcade_games.append(bnorm_game)
                else:
                    if bnorm and bnorm not in seen_badges:
                        seen_badges.add(bnorm)
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
            # Check if it's an arcade game
            if is_arcade_game(bnorm):
                bnorm_game = f"{bnorm} [Game]" if '[Game]' not in bnorm else bnorm
                if bnorm_game not in seen_arcade:
                    seen_arcade.add(bnorm_game)
                    arcade_games.append(bnorm_game)
            else:
                if bnorm and bnorm not in seen_badges:
                    seen_badges.add(bnorm)
                    badges.append(bnorm)

    # Tertiary fallback: regex for bracketed badge names (rare but useful)
    for m in re.finditer(r"([A-Za-z0-9\-:,() '&]+\[Skill Badge\])", text):
        b = m.group(1).strip()
        if is_negative_phrase(b):
            continue
        if b not in seen_badges:
            seen_badges.add(b)
            badges.append(b)
    
    # Also look for arcade game patterns
    for m in re.finditer(r"([A-Za-z0-9\-:,() '&]+\[Game\])", text):
        g = m.group(1).strip()
        if is_negative_phrase(g):
            continue
        if g not in seen_arcade:
            seen_arcade.add(g)
            arcade_games.append(g)

    return {'badges': badges, 'arcade_games': arcade_games}


def fetch_profile(url, timeout=15):
    headers = {
    'User-Agent': 'GDSC-Bennett-Completion-Tracker-Bot/1.0 (+https://github.com/Chitresh-code)'
    }
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
    except Exception as e:
        return {'url': url, 'error': str(e), 'badges': [], 'arcade_games': []}

    result = extract_badges_from_html(r.text)
    return {'url': url, 'badges': result.get('badges', []), 'arcade_games': result.get('arcade_games', [])}


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
            arcade_games = result.get('arcade_games', [])
            if not badges and not arcade_games and result.get('error'):
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

            old_badge_count = int(matched.get('# of Skill Badges Completed') or 0)
            old_arcade_count = int(matched.get('# of Arcade Games Completed') or 0)
            new_badge_count = len(badges)
            new_arcade_count = len(arcade_games)
            
            # Update if we found more badges or arcade games
            if new_badge_count > old_badge_count or new_arcade_count > old_arcade_count:
                print(f"Update {matched.get('User Name')}: badges {old_badge_count} -> {new_badge_count}, arcade {old_arcade_count} -> {new_arcade_count}")
                
                # Update skill badges
                matched['# of Skill Badges Completed'] = new_badge_count
                matched['Names of Completed Skill Badges'] = ' | '.join(badges)
                
                # Update arcade games
                matched['# of Arcade Games Completed'] = new_arcade_count
                matched['Names of Completed Arcade Games'] = ' | '.join(arcade_games)
                
                # Recalculate total courses completed (badges + arcade games)
                matched['# of Courses Completed'] = new_badge_count + new_arcade_count

                # Update completion flags according to business rule: >=19 skill badges AND >=1 arcade game
                completion_met = (new_badge_count >= 19 and new_arcade_count >= 1)
                # preserve both possible keys used in data
                if 'All Skill Badges & Games Completed' in matched:
                    matched['All Skill Badges & Games Completed'] = 'Yes' if completion_met else 'No'
                matched['All 3 Pathways Completed - Yes or No'] = 'Yes' if completion_met else 'No'

                # Also update arcade completion short flag if present
                if 'Gen AI Arcade Game Completion' in matched:
                    matched['Gen AI Arcade Game Completion'] = '1' if new_arcade_count > 0 else '0'

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
                arcade_games = result.get('arcade_games', [])
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

                old_badge_count = int(matched.get('# of Skill Badges Completed') or 0)
                old_arcade_count = int(matched.get('# of Arcade Games Completed') or 0)
                new_badge_count = len(badges)
                new_arcade_count = len(arcade_games)
                
                if new_badge_count > old_badge_count or new_arcade_count > old_arcade_count:
                    print(f"Update (retry) {matched.get('User Name')}: badges {old_badge_count} -> {new_badge_count}, arcade {old_arcade_count} -> {new_arcade_count}")
                    
                    # Update skill badges
                    matched['# of Skill Badges Completed'] = new_badge_count
                    matched['Names of Completed Skill Badges'] = ' | '.join(badges)
                    
                    # Update arcade games
                    matched['# of Arcade Games Completed'] = new_arcade_count
                    matched['Names of Completed Arcade Games'] = ' | '.join(arcade_games)
                    
                    # Recalculate totals and flags
                    matched['# of Courses Completed'] = new_badge_count + new_arcade_count
                    completion_met = (new_badge_count >= 19 and new_arcade_count >= 1)
                    if 'All Skill Badges & Games Completed' in matched:
                        matched['All Skill Badges & Games Completed'] = 'Yes' if completion_met else 'No'
                    matched['All 3 Pathways Completed - Yes or No'] = 'Yes' if completion_met else 'No'
                    if 'Gen AI Arcade Game Completion' in matched:
                        matched['Gen AI Arcade Game Completion'] = '1' if new_arcade_count > 0 else '0'

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
