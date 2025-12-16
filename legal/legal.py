import re
import pandas as pd
import requests
from bs4 import BeautifulSoup
from time import sleep
import pickle
import os

# === CONFIG ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

excel_in = os.path.join(BASE_DIR, "mapping", "mapping_v1.xlsx")
excel_out = os.path.join(BASE_DIR, "mapping_filled_legal_full.xlsx")
cache_file = os.path.join(BASE_DIR, "bns_cache.pkl")
REQUEST_SLEEP = 0.25

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
    text = re.sub(r'\u2019', "'", text)
    text = re.sub(r'\u2013', '-', text)
    text = re.sub(r'\u2014', '--', text)
    return text.strip()

def extract_section_content(td, section_num):
    """
    Extract section content preserving structure.
    Returns (section_dict, section_type)
    """
    section_dict = {}
    all_parts = []  # For building complete section
    subsections = {}
    
    # REMOVE IPC SECTION REFERENCE PARAGRAPHS
    for p in td.find_all('p', recursive=False):
        text = p.get_text(strip=True)
        if re.match(r'^\s*IPC\s*Section\s*\d+', text, re.I):
            p.decompose()
    
    # Process all paragraph elements
    for p in td.find_all('p', recursive=False):
        # Skip IPC/BNS reference paragraphs (double check)
        text = p.get_text(strip=True)
        if re.match(r'^\s*(IPC|BNS)\s+Section', text, re.I):
            continue
        
        # Check if this paragraph contains an ordered list (subsections)
        ol = p.find('ol', recursive=False)
        if ol:
            # Get text before the list
            intro_text = []
            for child in p.contents:
                if getattr(child, 'name', None) == 'ol':
                    break
                if hasattr(child, 'get_text'):
                    intro_text.append(child.get_text(" ", strip=True))
                else:
                    intro_text.append(str(child).strip())
            
            intro = clean_text(" ".join(filter(None, intro_text)))
            if intro:
                all_parts.append(intro)
            
            # Extract list items as subsections
            # Check if it's roman numeral or letter list
            ol_class = ol.get('class', [])
            ol_type = ol.get('type', '')
            is_roman = 'i' in ol_class or ol_type == 'i'
            
            lis = ol.find_all('li', recursive=False)
            for i, li in enumerate(lis, 1):
                li_text = li.get_text(" ", strip=True)
                
                if is_roman:
                    # Use roman numerals with proper spacing
                    roman_nums = ['i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x']
                    roman = roman_nums[i-1] if i <= len(roman_nums) else f'#{i}'
                    subsections[i] = clean_text(li_text)
                    all_parts.append(f"({roman}) {subsections[i]}")
                else:
                    # Use letters
                    subsections[i] = clean_text(li_text)
                    all_parts.append(f"({chr(96+i)}) {subsections[i]}")
        else:
            # Regular paragraph - just add it
            if text:
                all_parts.append(clean_text(text))
    
    # If we found subsections, this is a numbered section
    if subsections:
        section_type = 'numbered'
        # Store each subsection separately
        for i, text in subsections.items():
            section_dict[f"{section_num}({i})"] = text
        # Store complete section
        section_dict[str(section_num)] = "\n\n".join(all_parts)
    else:
        # No subsections - check if we have a definitions-style list
        ol_direct = td.find('ol', recursive=False)
        if ol_direct:
            section_type = 'definitions'
            lis = ol_direct.find_all('li', recursive=False)
            for i, li in enumerate(lis, 1):
                li_text = li.get_text(" ", strip=True)
                section_dict[f"{section_num}({i})"] = clean_text(li_text)
            # Join all for complete section
            section_dict[str(section_num)] = "\n\n".join(
                [section_dict[f"{section_num}({i})"] for i in range(1, len(lis)+1)]
            )
        else:
            section_type = 'paragraph'
            section_dict[str(section_num)] = "\n\n".join(all_parts) if all_parts else clean_text(td.get_text(" ", strip=True))
    
    return section_dict, section_type

def _sort_keys_for_printing(keys, section_num):
    """Return keys sorted so subsections come first in numeric order, then whole section."""
    def keyfn(k):
        m = re.match(rf'^{section_num}\((\d+)\)$', k)
        if m:
            return (0, int(m.group(1)))
        if k == str(section_num):
            return (1, 0)
        return (2, k)
    return sorted(keys, key=keyfn)

def _print_success_message(key, section_type):
    """Print success message."""
    m = re.match(r'^(\d{1,3})\((\d+)\)$', key)
    if m:
        idx = int(m.group(2))
        if section_type == 'numbered':
            print(f"[FETCH] {key}... OK [subsection {idx} successfully filled]")
        else:
            print(f"[FETCH] {key}... OK [definition {idx} successfully filled]")
        return
    
    m2 = re.match(r'^(\d{1,3})$', key)
    if m2:
        if section_type == 'numbered':
            print(f"[FETCH] {key}... OK [all subsections filled successfully]")
        elif section_type == 'definitions':
            print(f"[FETCH] {key}... OK [all definitions filled successfully]")
        else:
            print(f"[FETCH] {key}... OK [section filled successfully]")

def fetch_bns_section(section_num, subsection_num=None):
    """Fetch BNS section with proper subsection handling."""
    requested_key = f"{section_num}" if subsection_num is None else f"{section_num}({subsection_num})"
    
    # Check cache
    if requested_key in cache:
        print(f" [CACHE] {requested_key}")
        meta = cache.get(f"__meta__{section_num}")
        section_type = meta['type'] if meta and 'type' in meta else None
        if section_type:
            _print_success_message(requested_key, section_type)
        return cache[requested_key]
    
    # Fetch from web
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
        
        # Cache all parts
        for k, v in section_dict.items():
            cache[k] = v
        cache[f"__meta__{section_num}"] = {'type': section_type, 'keys': list(section_dict.keys())}
        
        # Print success
        ordered_keys = _sort_keys_for_printing(list(section_dict.keys()), section_num)
        for k in ordered_keys:
            _print_success_message(k, section_type)
            sleep(0.02)
        
        sleep(REQUEST_SLEEP)
        
        return cache.get(requested_key)
        
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
    
    if not bns_ref or bns_ref.upper() == 'R':
        df.at[idx, 'legal'] = None
        continue
    
    parsed = parse_bns_reference(bns_ref)
    if not parsed:
        print(f"Row {idx+1}: Invalid format '{bns_ref}'")
        invalid_count += 1
        continue
    
    section, subsection = parsed[0]
    legal_text = fetch_bns_section(section, subsection)
    
    if legal_text:
        df.at[idx, 'legal'] = legal_text
        filled_count += 1
    else:
        df.at[idx, 'legal'] = None
        empty_count += 1
    
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