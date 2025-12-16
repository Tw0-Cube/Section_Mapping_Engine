import pandas as pd
import json

def generate_mapping(excel_path="mapping.xlsx", json_path="mapping.json"):
    df = pd.read_excel(excel_path)
    result = {}
    status = "Mapped"
    
    for _, row in df.iterrows():
        ipc = [i.strip() for i in str(row["ipc_sec"]).split(",")]
        ipc_sub = [i_s.strip() for i_s in str(row["ipc_subsec"]).split(",")] if pd.notna(row['ipc_subsec']) else []
        titles = str(row['title'])
        bns = [b.strip() for b in str(row["bns"]).split("&")]
        change = str(row["change"])
        terms = [t.strip().lower() for t in str(row["term"]).split("/")] 
        definition = str(row["definition"]) if pd.notna(row["definition"]) else None
        legal = str(row["legal"]) if pd.notna(row["legal"]) else None

        ipc = tuple(ipc)
        ipc_sub = tuple(ipc_sub)
        bns = tuple(bns)
        terms = tuple(terms)
    
        if ipc[0] == "A":
            status = "Added"
        elif bns[0] == "R":
            status = "Removed"    
        else:
            pass

        key = (ipc, ipc_sub, terms)
        result[key] = {
            "bns_section": bns,
            "titles": titles,
            "change": change,
            "status": status,
            "definition": definition,
            "legal": legal
        }

    # JSON keys cannot be tuples/lists, convert to string for saving
    json_ready = [
        {
            "ipc_sec": list(k[0]),
            "ipc_subsec": list(k[1]),
            "terms": list(k[2]),
            "bns_section": list(v["bns_section"]),
            **{key: v[key] for key in v if key != "bns_section"}
        }
        for k, v in result.items()
    ]

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_ready, f, indent=4, ensure_ascii=False)

    return json_ready


def save_definition(bns_term: str, explanation: str, excel_path="mapping.xlsx", json_path="mapping.json"):
    # Update Excel
    df = pd.read_excel(excel_path)
    
    def update_row(row):
        if pd.notna(row["bns"]):
            bns = [b.strip() for b in str(row["bns"]).split("&")]
            if bns_term in bns:
                row["definition"] = explanation
        return row
    
    df = df.apply(update_row, axis=1)
    df.to_excel(excel_path, index=False)

    # Update JSON
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for item in data:
        if item["bns_section"] and bns_term in item["bns_section"]:
            item["definition"] = explanation

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    return True