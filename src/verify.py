import json
import os
import re

FIELDS = [
    "scheme_name", "department", "benefit_type", "benefit_amount",
    "benefit_frequency", "eligibility", "documents_required",
    "how_to_apply", "deadline", "official_link",
]

# only these fields are compared across sources for conflicts
# (comparing free text like eligibility would give many false conflicts)
CONFLICT_FIELDS = ["benefit_amount", "deadline", "official_link"]


def norm(s):
    # collapse spaces and line breaks so a wrapped line still matches
    return " ".join(str(s).split())


def evidence_ok(evidence, source_text):
    if not evidence:
        return False
    items = evidence if isinstance(evidence, list) else [evidence]
    items = [i for i in items if i]
    if not items:
        return False
    src = norm(source_text)
    return all(norm(i) in src for i in items)


def same_value(field, a, b):
    if field == "benefit_amount":
        return re.sub(r"\D", "", str(a)) == re.sub(r"\D", "", str(b))
    return norm(a).lower() == norm(b).lower()


def main():
    with open("outputs/raw_extractions.json", encoding="utf-8") as f:
        raw = json.load(f)

    # group the sources by scheme
    schemes = {}
    for src in raw:
        schemes.setdefault(src["scheme_ref"], []).append(src)

    records = []
    for ref, sources in schemes.items():
        for field in FIELDS:
            good = []      # candidates whose evidence was verified
            notes = []
            for src in sources:
                item = src["fields"].get(field)
                if not isinstance(item, dict) or item.get("value") in (None, "", []):
                    continue
                with open(os.path.join("docs", src["source_name"]), encoding="utf-8") as f:
                    text = f.read()
                if not evidence_ok(item.get("evidence"), text):
                    notes.append("rejected from " + src["source_name"] +
                                 ": evidence text not found in the document")
                    continue
                if item.get("page") is None:
                    notes.append("no page marker for " + src["source_name"])
                good.append({
                    "value": item["value"],
                    "evidence": {
                        "text": item["evidence"],
                        "location": "page " + str(item.get("page")),
                        "source": src["source_name"],
                        "captured_on": src["captured_on"],
                    },
                })

            if not good:
                status, value, evidence, conf = "not found", None, None, None
                if not notes:
                    notes.append("not stated in any source document")
            else:
                status, conf = "found", "high"
                value, evidence = good[0]["value"], good[0]["evidence"]
                if field in CONFLICT_FIELDS and len(good) > 1:
                    first = good[0]["value"]
                    if any(not same_value(field, first, g["value"]) for g in good[1:]):
                        status, conf = "conflict", "low"
                        value = [g["value"] for g in good]
                        evidence = [g["evidence"] for g in good]
                        notes.append("sources disagree, a person must decide")

            records.append({
                "scheme_ref": ref, "field": field, "value": value,
                "evidence": evidence, "confidence": conf,
                "status": status, "note": "; ".join(notes) or None,
            })

    with open("outputs/records.json", "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print("Saved outputs/records.json")
    print()
    for r in records:
        print(r["scheme_ref"], r["field"].ljust(20), r["status"])
        if r["note"]:
            print("     note:", r["note"])


if __name__ == "__main__":
    main()