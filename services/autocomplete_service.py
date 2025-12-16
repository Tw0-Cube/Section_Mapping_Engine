import json
from parsing.parsing import parse

def autocomplete_service(query, search_mode, JSON_PATH):
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

        suggestions = []
        query_lower = query.lower()
        
        for item in data:
            title = item["titles"]
            ipc_sections = ", ".join(item["ipc_sec"])
            bns_sections = ", ".join(item["bns_section"])
            
            score = 0
            match_found = False
            
            # If search mode is BNS, prioritize BNS section matching
            if search_mode == "bns":
                clean_query = query_lower.replace("bns", "").replace("section", "").replace("sec", "").strip()
                
                # Parse the query to extract section and subsection
                section_num, subsec_num = parse(query, 'bns')
                
                if section_num:
                    # Check for exact section match
                    for bns in item["bns_section"]:
                        bns_clean = bns.strip()
                        
                        # If user specified subsection, match it precisely
                        if subsec_num:
                            # Normalize both for comparison (remove spaces and parens, uppercase)
                            bns_normalized = bns_clean.replace(" ", "").replace("(", "").replace(")", "").upper()
                            # Build expected pattern: section+subsection (e.g., "16" for section 1, subsec 6)
                            search_normalized = f"{section_num}{subsec_num}".replace(" ", "").replace("(", "").replace(")", "").upper()
                            
                            # Also check with parentheses format
                            search_with_parens = f"{section_num}({subsec_num})".upper()
                            bns_with_parens = bns_clean.upper()
                            
                            if (search_normalized == bns_normalized or 
                                search_with_parens == bns_with_parens or
                                bns_with_parens.startswith(search_with_parens + " ") or
                                bns_with_parens.startswith(search_with_parens + ",")):
                                score += 100
                                match_found = True
                                break
                        else:
                            # Exact match for section (including letters like 153AA)
                            if bns_clean.upper() == section_num.upper():
                                score += 100
                                match_found = True
                                break
                            # Check if it starts with the section number followed by space or comma
                            elif (bns_clean.upper().startswith(section_num.upper() + " ") or 
                                  bns_clean.upper().startswith(section_num.upper() + ",") or
                                  bns_clean.upper().startswith(section_num.upper() + "(")):
                                score += 90
                                match_found = True
                                break
                
                # Fallback: partial matching
                if not match_found:
                    for bns in item["bns_section"]:
                        if clean_query in bns.lower():
                            score += 60
                            match_found = True
                            break
            
            # If search mode is IPC or no BNS match, continue with normal matching
            if search_mode == "ipc" or not match_found:
                # Check IPC section match FIRST (highest priority)
                if search_mode == "ipc":
                    section_num, subsec_num = parse(query, 'ipc')
                    
                    if section_num:
                        for ipc in item["ipc_sec"]:
                            ipc_clean = ipc.strip()
                            
                            if subsec_num:
                                # Normalize both for comparison (remove spaces and parens, uppercase)
                                ipc_normalized = ipc_clean.replace(" ", "").replace("(", "").replace(")", "").upper()
                                # Build expected pattern: section+subsection
                                search_normalized = f"{section_num}{subsec_num}".replace(" ", "").replace("(", "").replace(")", "").upper()
                                
                                # Also check with parentheses format
                                search_with_parens = f"{section_num}({subsec_num})".upper()
                                ipc_with_parens = ipc_clean.upper()
                                
                                if (search_normalized == ipc_normalized or 
                                    search_with_parens == ipc_with_parens or
                                    ipc_with_parens.startswith(search_with_parens + " ") or
                                    ipc_with_parens.startswith(search_with_parens + ",")):
                                    score += 100
                                    match_found = True
                                    break
                            else:
                                # Exact match for section (including letters like 153AA, 29A)
                                if ipc_clean.upper() == section_num.upper():
                                    score += 100
                                    match_found = True
                                    break
                                # Check if it starts with the section number followed by delimiter
                                elif (ipc_clean.upper().startswith(section_num.upper() + " ") or 
                                      ipc_clean.upper().startswith(section_num.upper() + ",") or
                                      ipc_clean.upper().startswith(section_num.upper() + "(")):
                                    score += 90
                                    match_found = True
                                    break
                
                # Then check term matches (lower priority than section matches)
                if not match_found:
                    # Check exact term match
                    for term in item["terms"]:
                        if query_lower == term.lower():
                            score += 80
                            match_found = True
                            break
                    
                    # Check if term starts with query
                    if not match_found:
                        for term in item["terms"]:
                            if term.lower().startswith(query_lower):
                                score += 70
                                match_found = True
                                break
                    
                    # Check if title starts with query
                    if not match_found and title.lower().startswith(query_lower):
                        score += 60
                        match_found = True
                    
                    # Check if any term contains query
                    if not match_found:
                        for term in item["terms"]:
                            if query_lower in term.lower():
                                score += 50
                                match_found = True
                                break
                    
                    # Check if title contains query
                    if not match_found and query_lower in title.lower():
                        score += 40
                        match_found = True
            
            if match_found:
                # Penalize longer titles (they're usually less specific)
                length_penalty = len(title) / 100
                final_score = score - length_penalty
                
                suggestions.append({
                    "title": title,
                    "ipc": ipc_sections,
                    "bns": bns_sections,
                    "display": f"{title[:80]}{'...' if len(title) > 80 else ''} (IPC: {ipc_sections})",
                    "score": final_score
                })
        
        # Sort by score descending
        suggestions.sort(key=lambda x: x["score"], reverse=True)
        
        # Remove score from final output and limit to 10
        for s in suggestions:
            del s["score"]
        
        return suggestions