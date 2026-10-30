import json
import re

CHECKED_VALUE_FIELDS = ["benefit_amount", "deadline"]
TEXT_FIELDS = ["scheme_name", "department", "benefit_type", "benefit_frequency",
               "eligibility", "documents_required", "how_to_apply"]


def flat(v):
    # turn None / text / nested lists into a flat list of strings
    if v is None:
        return []
    if isinstance(v, list):
        out = []
        for x in v:
            out += flat(x)
        return out
    return [str(v)]


def amount_key(values):
    # biggest number in each value, e.g. "Rs. 25,000" -> 25000
    keys = set()
    for v in values:
        nums = [int(n.replace(",", "")) for n in re.findall(r"\d[\d,]*", v)]
        if nums:
            keys.add(max(nums))
    return keys


def date_key(values):
    # only the numbers in the date, e.g. "31 March 2027" -> ("31", "2027")
    return {tuple(re.findall(r"\d+", v)) for v in values}


def main():
    with open("gold/gold.json", encoding="utf-8") as f:
        gold = json.load(f)
    with open("outputs/records.json", encoding="utf-8") as f:
        records = json.load(f)

    rec = {(r["scheme_ref"], r["field"]): r for r in records}

    status_score = {}   # field -> [correct, total]
    value_score = {}
    problems = []

    for ref, fields in gold.items():
        for field, g in fields.items():
            r = rec.get((ref, field))
            got_status = r["status"] if r else "missing"

            status_score.setdefault(field, [0, 0])
            status_score[field][1] += 1
            if got_status == g["status"]:
                status_score[field][0] += 1
            else:
                problems.append(ref + " " + field + ": status should be '" +
                                g["status"] + "' but got '" + got_status + "'")

            if field in CHECKED_VALUE_FIELDS and g["status"] != "not found":
                value_score.setdefault(field, [0, 0])
                value_score[field][1] += 1
                key = amount_key if field == "benefit_amount" else date_key
                gold_k = key(g["values"])
                got_k = key(flat(r["value"])) if r else set()
                if gold_k == got_k:
                    value_score[field][0] += 1
                else:
                    problems.append(ref + " " + field + ": value wrong. gold=" +
                                    str(g["values"]) + " got=" + str(flat(r["value"]) if r else None))

    print("STATUS accuracy (found / not found / conflict)")
    total_c = total_n = 0
    for field, (c, n) in status_score.items():
        print("  ", field.ljust(20), str(c) + "/" + str(n))
        total_c += c
        total_n += n
    print("   OVERALL".ljust(23), str(total_c) + "/" + str(total_n))

    print()
    print("VALUE accuracy (amount and deadline only)")
    for field, (c, n) in value_score.items():
        print("  ", field.ljust(20), str(c) + "/" + str(n))

    print()
    print("PROBLEMS")
    if problems:
        for p in problems:
            print("  -", p)
    else:
        print("  none")

    print()
    print("TEXT FIELDS - a person should read these (gold vs extracted)")
    for ref, fields in gold.items():
        for field in TEXT_FIELDS:
            r = rec.get((ref, field))
            print(ref, field)
            print("    gold:     ", fields[field]["values"])
            print("    extracted:", flat(r["value"]) if r else None)


if __name__ == "__main__":
    main()