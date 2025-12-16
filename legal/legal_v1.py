import re
import pandas as pd
import requests
from bs4 import BeautifulSoup
from time import sleep
import pickle
import os

# === CONFIG ===
excel_in = "C:/Users/vijay/OneDrive/Desktop/project/mapping/mapping.xlsx"
excel_out = "C:/Users/vijay/OneDrive/Desktop/mapping_filled_legal_full.xlsx"
cache_file = "bns_cache.pkl"
REQUEST_SLEEP = 0.25  # polite pause between requests

# Load cache if exists
if os.path.exists(cache_file):
    with open(cache_file, 'rb') as f:
        cache = pickle.load(f)
    print(f"Loaded {len(cache)} cached entries")
else:
    cache = {}

def parse_bns_reference(bns_ref):
    """Parse BNS reference -> list of (section, subsection) tuples."""
    bns_ref = re.sub(r'\s*\(\s*', '(', bns_ref)
    bns_ref = re.sub(r'\s*\)\s*', ')', bns_ref)
    results = []
    parts = bns_ref.split('&')
    for part in parts:
        part = part.strip()
        match = re.match(r'^(\d{1,3})(?:\((\d+)\))?$', part)
        if match:
            section = int(match.group(1))
            subsection = int(match.group(2)) if match.group(2) else None
            results.append((section, subsection))
    return results if results else None

def clean_text(text):
    text = re.sub(r'\r', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()

def _sort_keys_for_printing(keys, section_num):
    """Return keys sorted so subsections come first numeric order, then whole section."""
    def keyfn(k):
        m = re.match(rf'^{section_num}\((\d+)\)$', k)
        if m:
            return (0, int(m.group(1)))
        if k == str(section_num):
            return (1, 0)
        # fallback (unlikely)
        return (2, k)
    return sorted(keys, key=keyfn)

def extract_section_content(td, section_num):
    """
    Parse <td> content of a section.
    Returns (section_dict, section_type)
    section_type in {'numbered', 'definitions', 'paragraph'}
    section_dict keys: "N" (whole) and "N(i)" for subsections as appropriate.
    """
    section_dict = {}

    # Helper: flatten li but annotate nested ol items as (a),(b)...
    def flatten_li_with_nested(li_tag):
        parts = []
        for child in li_tag.contents:
            if getattr(child, 'name', None) == 'ol':
                nested = child
                nested_lis = nested.find_all('li', recursive=False)
                for j, nli in enumerate(nested_lis, 1):
                    nested_text = nli.get_text(" ", strip=True)
                    parts.append(f"({chr(96+j)}) {nested_text}")
            else:
                # normal text node / tags
                t = child.get_text(" ", strip=True) if hasattr(child, 'get_text') else str(child).strip()
                if t:
                    parts.append(t)
        return clean_text(" ".join(parts))

    # 1) Check for <p> that contains an <ol> (definitions style, e.g. section 2)
    p_tags = td.find_all('p', recursive=False)
    for p in p_tags:
        ol_in_p = p.find('ol', recursive=False)
        if ol_in_p:
            # get intro text from the <p> *before* the ol
            intro_parts = []
            for child in p.contents:
                if getattr(child, 'name', None) == 'ol':
                    break
                else:
                    intro_parts.append(child.get_text(" ", strip=True) if hasattr(child, 'get_text') else str(child).strip())
            intro = clean_text(" ".join(filter(None, intro_parts)))
            if intro:
                section_dict[str(section_num)] = intro

            lis = ol_in_p.find_all('li', recursive=False)
            for i, li in enumerate(lis, 1):
                section_dict[f"{section_num}({i})"] = flatten_li_with_nested(li)
            return section_dict, 'definitions'

    # 2) If no p-with-ol, check for a top-level <ol> directly under td (numbered subsections style)
    ol_top = td.find('ol', recursive=False)
    if ol_top:
        lis = ol_top.find_all('li', recursive=False)
        for i, li in enumerate(lis, 1):
            section_dict[f"{section_num}({i})"] = flatten_li_with_nested(li)
        # join subsections into whole section
        ordered = _sort_keys_for_printing([k for k in section_dict.keys()], section_num)
        joined = "\n\n".join([section_dict[k] for k in ordered if k != str(section_num)])
        section_dict[str(section_num)] = clean_text(joined)
        return section_dict, 'numbered'

    # 3) Fallback: no ordered list -> whole paragraph(s) -> store as single section
    # gather direct <p> children (preserve paragraphs)
    if p_tags:
        parts = [p.get_text(" ", strip=True) for p in p_tags]
        full = "\n\n".join(parts)
    else:
        # final fallback: entire td text
        full = td.get_text(" ", strip=True)
    section_dict[str(section_num)] = clean_text(full)
    return section_dict, 'paragraph'

def _print_success_message(key, section_type):
    """Print success message in the formats you requested."""
    # subsection case
    m = re.match(r'^(\d{1,3})\((\d+)\)$', key)
    if m:
        sec = m.group(1)
        idx = int(m.group(2))
        if section_type == 'numbered':
            print(f"[FETCH] {key}... OK [subsection {idx} successfully filled]")
        elif section_type == 'definitions':
            print(f"[FETCH] {key}... OK [paragraph tag successfully filled]")
        else:
            # fallback
            print(f"[FETCH] {key}... OK [subsection {idx} successfully filled]")
        return

    # whole-section case
    m2 = re.match(r'^(\d{1,3})$', key)
    if m2:
        sec = m2.group(1)
        if section_type == 'definitions':
            print(f"[FETCH] {key}... OK [paragraph tag successfully filled]")
        elif section_type == 'numbered':
            print(f"[FETCH] {key}... OK [all subsections filled successfully]")
        else:
            print(f"[FETCH] {key}... OK [all text filled successfully with spacing]")
        return

    # fallback generic
    print(f"[FETCH] {key}... OK [filled]")

def fetch_bns_section(section_num, subsection_num=None):
    """
    Fetch BNS section text and handle subsections properly.
    - Caches each subsection as "N(i)" and the whole section as "N".
    - Stores metadata under "__meta__N" with {'type': section_type, 'keys': [...]}
    """
    requested_key = f"{section_num}" if subsection_num is None else f"{section_num}({subsection_num})"

    # If fully cached for this exact key -> return and print
    if requested_key in cache:
        print(f" [CACHE] {requested_key}")
        # try to get type from meta
        meta = cache.get(f"__meta__{section_num}")
        section_type = meta['type'] if meta and 'type' in meta else None
        if section_type:
            _print_success_message(requested_key, section_type)
        else:
            # unknown meta - generic hit
            print(f"[FETCH] {requested_key}... OK [cached]")
        return cache[requested_key]

    # Not cached -> fetch page and extract everything for that section
    url = f"https://devgan.in/bns/index.php?q={section_num}&a=10"
    try:
        print(f" [FETCH] {requested_key}...", end='')
        response = requests.get(url, timeout=12)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        content_row = soup.find('tr', class_='mys-desc')
        if not content_row:
            print(" FAILED - no mys-desc")
            return None
        td = content_row.find('td')
        if not td:
            print(" FAILED - no td")
            return None

        section_dict, section_type = extract_section_content(td, section_num)

        # Cache all parts and a meta entry
        for k, v in section_dict.items():
            cache[k] = v
        cache[f"__meta__{section_num}"] = {'type': section_type, 'keys': list(section_dict.keys())}

        # Print success messages for each cached piece (subsections first, then whole)
        ordered_keys = _sort_keys_for_printing(list(section_dict.keys()), section_num)
        for k in ordered_keys:
            _print_success_message(k, section_type)
            sleep(0.02)

        # polite pause
        sleep(REQUEST_SLEEP)

        # Return the requested piece if present
        if requested_key in cache:
            return cache[requested_key]
        else:
            # requested subsection not available
            print(" NOT FOUND subsection")
            return None

    except Exception as e:
        print(f" ERROR: {e}")
        return None


# === LOAD EXCEL ===
df = pd.read_excel(excel_in, dtype=str)

if 'legal' not in df.columns:
    df['legal'] = ''

# === PROCESS EACH ROW ===
filled_count = 0
empty_count = 0
invalid_count = 0

print("\nProcessing rows...")

for idx, row in df.iterrows():
    bns_ref = str(row.get('bns', '')).strip()

    # Skip empty or 'R' values
    if not bns_ref or bns_ref.upper() == 'R':
        df.at[idx, 'legal'] = None
        continue

    parsed = parse_bns_reference(bns_ref)
    if not parsed:
        print(f"Row {idx+1}: Invalid format '{bns_ref}'")
        invalid_count += 1
        continue

    # Take first reference (keeping original behavior)
    section, subsection = parsed[0]

    legal_text = fetch_bns_section(section, subsection)

    if legal_text:
        df.at[idx, 'legal'] = legal_text
        filled_count += 1
    else:
        df.at[idx, 'legal'] = None
        empty_count += 1

    # Save cache periodically
    if (idx + 1) % 10 == 0:
        with open(cache_file, 'wb') as f:
            pickle.dump(cache, f)
        print(f"Progress: {idx+1} rows processed")

# === FINAL SAVE ===
df.to_excel(excel_out, index=False)

with open(cache_file, 'wb') as f:
    pickle.dump(cache, f)

print(f"\n=== SUMMARY ===")
print(f"Rows filled: {filled_count}")
print(f"Rows empty: {empty_count}")
print(f"Invalid format: {invalid_count}")
print(f"Cache entries: {len(cache)}")
print(f"Saved to: {excel_out}")
