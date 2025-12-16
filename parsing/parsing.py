import re

def parse(query, mode='ipc'):
    """
    Parse various section formats and extract section number and subsection.
    Returns: (section_number, subsection_number or None)
    
    Examples:
    "IPC 23(1)" → ("23", "1")
    "23 subsection 2" → ("23", "2")
    "section 420" → ("420", None)
    "23 (a)" → ("23", "a")
    "BNS 5" → ("5", None)
    "1(5)" → ("1", "5")
    "153AA" → ("153AA", None)  - treated as complete section number
    "29A" → ("29A", None)  - treated as complete section number
    """
    if not query:
        return (None, None)
    
    original_query = query.strip()
    query_lower = query.lower().strip()
    
    # Check if "subsection" or "sub" keywords are present BEFORE removing them
    has_subsection_keyword = (
        "subsection" in query_lower or 
        "sub-section" in query_lower or 
        re.search(r'\bsub\s', query_lower) or
        re.search(r'\bsubsec\b', query_lower)
    )
    
    # Remove common words but preserve the structure
    query_clean = query_lower
    query_clean = re.sub(r'\b(ipc|bns|IPC|Ipc|BNS|Bns|ipc section |bns section )\b', '', query_clean)
    query_clean = re.sub(r'\b(section|sec)\b', '', query_clean)
    query_clean = re.sub(r'\b(subsection|sub-section|subsec)\b', '', query_clean)
    query_clean = query_clean.strip()
    
    # Pattern 1: "23(1)" or "23 (1)" or "23(a)" - section with subsection in parentheses
    match = re.search(r'^([0-9]+[A-Za-z]*)\s*\(([A-Za-z0-9]+)\)$', query_clean)
    if match:
        return (match.group(1).upper(), match.group(2).upper())
    
    # Pattern 2: "23 1" or "23-1" (space or dash separated) - ONLY if subsection keyword was used
    if has_subsection_keyword:
        match = re.search(r'^([0-9]+[A-Za-z]*)[\s\-]+([A-Za-z0-9]+)$', query_clean)
        if match:
            return (match.group(1).upper(), match.group(2).upper())
    
    # Pattern 3: Complete section number like "153AA", "29A", "8", "420"
    match = re.search(r'^([0-9]+[A-Za-z]*)$', query_clean)
    if match:
        return (match.group(1).upper(), None)
    
    return (None, None)