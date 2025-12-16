import os
import re
import json
from parsing.parsing import parse
from ai.ai import explain_legal_term
from mapping.mapping import save_definition

def format_bnss_classification(legal_text):
    """
    Formats BNSS Classification text into neat bullet points.
    Returns formatted string if BNSS Classification exists, empty string otherwise.
    """
    if not legal_text or legal_text.strip() == "":
        return ""
    
    # Check if it contains BNSS Classification
    if "BNSSClassification" not in legal_text:
        return ""
    
    # Extract only the BNSS Classification part
    bnss_match = re.search(r'BNSSClassification(.+)', legal_text, re.DOTALL | re.IGNORECASE)
    if not bnss_match:
        return ""
    
    content = bnss_match.group(1).strip()
    
    # Initialize result
    formatted_lines = []
    
    # Pattern matching for different components
    found_items = []
    
    # Try to extract ALL punishment lines (for sections with multiple subsections like 64(1), 64(2))
    # First check if there are numbered subsections like "64(1) -" or "64(2) -"
    subsection_pattern = r'(\d+\([^\)]+\)\s*-\s*[^.]*?(?:imprisonment|death)[^.]*?(?:fine|\.))(?=\d+\(|Cognizable|Bailable|Triable|Non-|$)'
    subsection_matches = re.findall(subsection_pattern, content, re.IGNORECASE | re.DOTALL)
    
    if subsection_matches:
        # Found subsection-specific punishments
        for idx, punishment in enumerate(subsection_matches, 1):
            punishment = re.sub(r'\s+', ' ', punishment.strip())
            punishment = punishment.replace('or with death', '**or with death**')
            # Extract subsection number
            subsec_match = re.match(r'(\d+\([^\)]+\))', punishment)
            if subsec_match:
                subsec_num = subsec_match.group(1)
                punishment_text = punishment.replace(subsec_num + ' - ', '').strip()
                found_items.append(f"**Punishment ({subsec_num}):** {punishment_text}")
            else:
                found_items.append(f"**Punishment {idx}:** {punishment}")
    else:
        # No subsections, look for general punishment
        imprisonment_patterns = [
            r'(Rigorous imprisonment[^.]*?(?:years?|life)[^.]*?)(?=Cognizable|Bailable|Triable|Non-|$)',
            r'(Simple imprisonment[^.]*?(?:years?|life)[^.]*?)(?=Cognizable|Bailable|Triable|Non-|$)',
            r'(Imprisonment[^.]*?(?:years?|life)[^.]*?)(?=Cognizable|Bailable|Triable|Non-|$)'
        ]
        
        for pattern in imprisonment_patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                imprisonment_text = match.group(1).strip()
                # Clean up the text
                imprisonment_text = re.sub(r'\s+', ' ', imprisonment_text)
                imprisonment_text = imprisonment_text.replace('or with death', '**or with death**')
                found_items.append(f"**Punishment:** {imprisonment_text}")
                break
    
    # Extract fine information
    fine_match = re.search(r'(and (?:shall also be liable to )?fine[^.]*?)(?=Cognizable|Bailable|Triable|Non-|$)', content, re.IGNORECASE)
    if fine_match:
        fine_text = fine_match.group(1).strip()
        fine_text = re.sub(r'\s+', ' ', fine_text)
        if 'fine' not in str(found_items).lower() or 'and fine' not in str(found_items).lower():
            found_items.append(f"**Fine:** Yes - {fine_text.replace('and ', '').capitalize()}")
    
    # Extract Cognizable/Non-cognizable
    cognizable_match = re.search(r'((?:Non-)?Cognizable)', content, re.IGNORECASE)
    if cognizable_match:
        found_items.append(f"**Cognizable:** {cognizable_match.group(1)}")
    
    # Extract Bailable/Non-bailable
    bailable_match = re.search(r'((?:Non-)?[Bb]ailable)', content, re.IGNORECASE)
    if bailable_match:
        bail_text = bailable_match.group(1)
        # Check for conditions
        condition_match = re.search(r'((?:Non-)?[Bb]ailable[^.]*?(?:on the complaint|only if|only on).*?)(?=Cognizable|Triable|$)', content, re.IGNORECASE | re.DOTALL)
        if condition_match:
            bail_text = condition_match.group(1).strip()
            bail_text = re.sub(r'\s+', ' ', bail_text)
        found_items.append(f"**Bailable:** {bail_text}")
    
    # Extract Triable by information
    triable_match = re.search(r'(Triable by [^.]+)', content, re.IGNORECASE)
    if triable_match:
        triable_text = triable_match.group(1).strip()
        found_items.append(f"**Triable By:** {triable_text.replace('Triable by ', '')}")
    
    # Extract Compoundable information
    compoundable_match = re.search(r'((?:Non-)?Compoundable[^.]*?)(?=Cognizable|Bailable|Triable|$)', content, re.IGNORECASE | re.DOTALL)
    if compoundable_match:
        compoundable_text = compoundable_match.group(1).strip()
        compoundable_text = re.sub(r'\s+', ' ', compoundable_text)
        found_items.append(f"**Compoundable:** {compoundable_text}")
    
    # If no structured data found, try a simple split approach
    if not found_items:
        # Remove the word "BNSSClassification" and split by common patterns
        lines = re.split(r'(?=[A-Z][a-z]+:)|(?=Cognizable)|(?=Non-cognizable)|(?=Bailable)|(?=Non-bailable)|(?=Triable)', content)
        for line in lines:
            line = line.strip()
            if line and len(line) > 3:
                found_items.append(f"{line}")
    
    # Add all found items to formatted output
    formatted_lines = found_items
    
    return formatted_lines


def explain_service(query, selected_title, search_mode, EXCEL_PATH, JSON_PATH):
    # Check if file exists first
    if not os.path.exists(JSON_PATH):
        return {"error": "Mapping file not found. Please wait for initialization."}, 500

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    match = None
    query_lower = query.lower()
    
    # If user selected from dropdown, match by exact title
    if selected_title:
        for item in data:
            if item["titles"] == selected_title:
                match = item
                break
    
    # If no selection, proceed with smart search
    if not match:
        # Determine if query looks like a section number or a term
        is_section_query = bool(re.match(r'^(ipc|bns|section|sec|sub)?\s*\d+', query_lower.strip()))
        
        # If search mode is BNS and query looks like section
        if search_mode == "bns" and is_section_query:
            section_num, subsec_num = parse(query, 'bns')
            
            # Debug logging
            print(f"DEBUG: BNS Query: '{query}'")
            print(f"DEBUG: Parsed section_num: '{section_num}', subsec_num: '{subsec_num}'")
            
            if section_num:
                # Validate BNS section range (1-358)
                section_base = re.match(r'^(\d+)', section_num)
                if section_base:
                    try:
                        section_int = int(section_base.group(1))
                        if section_int < 1 or section_int > 358:
                            return {
                                "error": f"BNS section {section_num} is out of range. Valid BNS sections are 1-358."
                            }, 404
                    except ValueError:
                        pass
                
                section_matches = []
                for item in data:
                    for bns in item["bns_section"]:
                        bns_clean = bns.strip()
                        
                        # Debug: Print first 3 items
                        if len(section_matches) < 3:
                            print(f"DEBUG: Checking against bns_clean: '{bns_clean}'")
                        
                        if subsec_num:
                            # User wants specific subsection
                            # Normalize both sides
                            bns_normalized = bns_clean.replace(" ", "").replace("(", "").replace(")", "").upper()
                            search_normalized = f"{section_num}{subsec_num}".replace(" ", "").replace("(", "").replace(")", "").upper()
                            
                            # Also check with parentheses format
                            search_with_parens = f"{section_num}({subsec_num})".upper()
                            bns_with_parens = bns_clean.upper()
                            
                            # Debug output
                            if len(section_matches) < 3:
                                print(f"  Comparing: search_normalized='{search_normalized}' vs bns_normalized='{bns_normalized}'")
                                print(f"  Comparing: search_with_parens='{search_with_parens}' vs bns_with_parens='{bns_with_parens}'")
                            
                            if (search_normalized == bns_normalized or 
                                search_with_parens == bns_with_parens or
                                bns_with_parens.startswith(search_with_parens + " ") or
                                bns_with_parens.startswith(search_with_parens + ",")):
                                print(f"  ✓ MATCH FOUND!")
                                section_matches.append(item)
                                break
                        else:
                            # User wants main section (could be "5" or "153AA")
                            if bns_clean.upper() == section_num.upper():
                                section_matches.append(item)
                                break
                            # Also match if section starts the BNS (like "5 " or "5,")
                            elif (bns_clean.upper().startswith(section_num.upper() + " ") or 
                                  bns_clean.upper().startswith(section_num.upper() + ",") or
                                  bns_clean.upper().startswith(section_num.upper() + "(")):
                                section_matches.append(item)
                                break
                
                if section_matches:
                    match = section_matches[0]
                else:
                    # Check if the main section exists (without subsection requirement)
                    main_section_exists = False
                    available_subsections = []
                    
                    # Extract base section number for checking
                    base_section = re.match(r'^(\d+[A-Z]*)', section_num)
                    if base_section:
                        base_num = base_section.group(1)
                        
                        for item in data:
                            for bns in item["bns_section"]:
                                bns_clean = bns.strip()
                                # Match exact section number (e.g., "1" matches "1(1)" but not "10" or "106")
                                # Check for exact match with subsection in brackets
                                match_pattern = re.match(r'^(\d+[A-Z]*)\s*[\(,]', bns_clean.upper())
                                if match_pattern and match_pattern.group(1) == base_num.upper():
                                    main_section_exists = True
                                    available_subsections.append(bns_clean)
                                # Also check for exact match without brackets
                                elif bns_clean.upper() == base_num.upper():
                                    main_section_exists = True
                                    available_subsections.append(bns_clean)
                    
                    # Provide helpful error message
                    if main_section_exists:
                        if available_subsections:
                            subsec_list = ", ".join(sorted(set(available_subsections)))
                            if subsec_num:
                                return {
                                    "error": f"BNS section {section_num}({subsec_num}) not found. Available sections/subsections: {subsec_list}"
                                }, 404
                            else:
                                return {
                                    "error": f"BNS section {section_num} only exists with subsections. Available: {subsec_list}"
                                }, 404
                        else:
                            return {
                                "error": f"BNS section {section_num} exists but subsection ({subsec_num}) not found. Try searching for just section {section_num}."
                            }, 404
                    elif subsec_num:
                        return {
                            "error": f"BNS section {section_num}({subsec_num}) not found. Try searching without the subsection or use a different term."
                        }, 404
                    else:
                        return {
                            "error": f"BNS section {section_num} not found. Valid BNS sections are 1-358. Try a different section or search by term."
                        }, 404
        
        # If search mode is IPC and query looks like a section number
        elif search_mode == "ipc" and is_section_query:
            section_num, subsec_num = parse(query, 'ipc')
            
            if section_num:
                # Find all items matching the section number
                section_matches = []
                for item in data:
                    # Check if any IPC section matches
                    for ipc in item["ipc_sec"]:
                        ipc_clean = ipc.strip()
                        
                        if subsec_num:
                            # User wants specific subsection
                            # Normalize both sides
                            ipc_normalized = ipc_clean.replace(" ", "").replace("(", "").replace(")", "").upper()
                            search_normalized = f"{section_num}{subsec_num}".replace(" ", "").replace("(", "").replace(")", "").upper()
                            
                            # Also check with parentheses format
                            search_with_parens = f"{section_num}({subsec_num})".upper()
                            ipc_with_parens = ipc_clean.upper()
                            
                            if (search_normalized == ipc_normalized or 
                                search_with_parens == ipc_with_parens or
                                ipc_with_parens.startswith(search_with_parens + " ") or
                                ipc_with_parens.startswith(search_with_parens + ",")):
                                section_matches.append(item)
                                break
                        else:
                            # User wants main section (could be "8", "153AA", "29A")
                            if ipc_clean.upper() == section_num.upper():
                                section_matches.append(item)
                                break
                            # Also match if section starts the IPC (like "8 " or "8,")
                            elif (ipc_clean.upper().startswith(section_num.upper() + " ") or 
                                  ipc_clean.upper().startswith(section_num.upper() + ",") or
                                  ipc_clean.upper().startswith(section_num.upper() + "(")):
                                section_matches.append(item)
                                break
                
                if section_matches:
                    if subsec_num:
                        # User specified a subsection - the match is already correct from above
                        match = section_matches[0]
                    else:
                        # No subsection specified - return main section (one without subsection)
                        for item in section_matches:
                            if not item["ipc_subsec"] or len(item["ipc_subsec"]) == 0 or item["ipc_subsec"] == [""]:
                                match = item
                                break
                        
                        # If no main section, return first match
                        if not match:
                            match = section_matches[0]
                else:
                    # Section not found - check if subsections exist
                    available_subsecs = []
                    base_section = re.match(r'^(\d+[A-Z]*)', section_num)
                    if base_section:
                        base_num = base_section.group(1)
                        
                        for item in data:
                            for ipc in item["ipc_sec"]:
                                ipc_clean = ipc.strip()
                                # Match exact section number (e.g., "1" matches "1(1)" but not "10" or "106")
                                match_pattern = re.match(r'^(\d+[A-Z]*)\s*[\(,]', ipc_clean.upper())
                                if match_pattern and match_pattern.group(1) == base_num.upper():
                                    available_subsecs.append(ipc_clean)
                                # Also check for exact match without brackets
                                elif ipc_clean.upper() == base_num.upper():
                                    available_subsecs.append(ipc_clean)
                    
                    if available_subsecs:
                        subsec_list = ", ".join(sorted(set(available_subsecs)))
                        if subsec_num:
                            return {
                                "error": f"IPC section {section_num}({subsec_num}) not found. Available sections/subsections: {subsec_list}"
                            }, 404
                        else:
                            return {
                                "error": f"IPC section {section_num} only exists with subsections. Available: {subsec_list}"
                            }, 404
                    else:
                        if subsec_num:
                            return {
                                "error": f"IPC section {section_num}({subsec_num}) not found. Try searching without the subsection or use a different term."
                            }, 404
                        else:
                            # Check range only for pure numeric sections
                            try:
                                section_int = int(section_num)
                                if section_int < 1 or section_int > 511:
                                    return {
                                        "error": f"IPC section {section_num} out of range. IPC sections range from 1 to 511."
                                    }, 404
                            except ValueError:
                                pass
                            
                            return {
                                "error": f"IPC section {section_num} not found. Try a different section or search by term."
                            }, 404
        
        # If still no match and query doesn't look like a section, try term matching
        if not match and not is_section_query:
            for item in data:
                if any(query_lower in term.lower() for term in item["terms"]):
                    match = item
                    break
        
        # Try matching by title if still no match
        if not match:
            for item in data:
                if query_lower in item["titles"].lower():
                    match = item
                    break

    if not match:
        if search_mode == "bns":
            return {"error": "No matching law found. BNS sections range from 1-358. Try a different section or search by term."}, 404
        else:
            return {"error": "No matching law found. Try a different term or section number."}, 404

    # Check cached definition
    if match.get("definition") and match["definition"] != "None":
        explanation = match["definition"]
        source = "Cached"
    else:
        # Generate AI explanation
        term_for_ai = match["titles"]
        explanation = explain_legal_term(term_for_ai)
        save_definition(match["bns_section"][0], explanation, EXCEL_PATH, JSON_PATH)
        source = "AI Generated"

    # Format BNSS Classification if present in legal column (returns a list)
    bnss_classification_list = format_bnss_classification(match.get("legal", ""))
    
    # Get the FULL legal text (keep everything including BNSS Classification for Legal Meaning section)
    legal_text = match.get("legal", "")

    return {
        "title": match["titles"],
        "ipc_sections": ", ".join(match["ipc_sec"]),
        "ipc_subsections": ", ".join(match["ipc_subsec"]) if match["ipc_subsec"] else "",
        "bns_sections": ", ".join(match["bns_section"]),
        "status": match.get("status", "N/A"),
        "terms": match["terms"],
        "explanation": explanation,
        "legal": legal_text,  # Keep FULL legal text for Legal Meaning section
        "change": match.get("change", ""),
        "source": source,
        "bnss_classification": bnss_classification_list  # Send formatted classification separately for Summary
    }, 200