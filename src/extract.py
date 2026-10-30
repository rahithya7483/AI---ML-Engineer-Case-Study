import json
import os
from datetime import date
from groq import Groq

MODEL = "openai/gpt-oss-20b"

# which file belongs to which scheme
SOURCES = [
    {"scheme_ref": "S1", "file": "s1_circular_en.txt"},
    {"scheme_ref": "S1", "file": "s1_myscheme_listing.txt"},
    {"scheme_ref": "S2", "file": "s2_circular_hi.txt"},
    {"scheme_ref": "S3", "file": "s3_scanned_ocr.txt"},
]

FIELDS = [
    "scheme_name", "department", "benefit_type", "benefit_amount",
    "benefit_frequency", "eligibility", "documents_required",
    "how_to_apply", "deadline", "official_link",
]

PROMPT = """You are helping a researcher fill a government scheme record.
Read the document below and extract these fields: {fields}

Rules:
1. For every field give: "value", "evidence", "page".
2. "evidence" must be copied EXACTLY, character by character, from the document. Do not fix spelling or OCR mistakes in the evidence.
3. "page" is the number from the nearest [Page N] marker above the evidence. If there is no page marker, use null.
4. If the document does not say it, set value, evidence and page to null. Never guess or fill from your own knowledge.
5. For eligibility and documents_required, "value" is a list of short items.
6. If the text has OCR errors (for example Scho1arship or 1,O00), write the CLEAN corrected text in "value" (Scholarship, 1,000), but keep the original noisy text in "evidence".
7. "benefit_type" is a short label for the kind of benefit (for example scholarship, one-time cash grant, subsidy). It is not a sentence and not an amount.
8. "benefit_frequency" must include details such as the number of installments, if the document says so.
9. Return only a JSON object with the field names as keys.

DOCUMENT:
{document}
"""


INPUT_PRICE = 0.075   # dollars per 1 million input tokens (Groq, checked 30 Oct 2026)
OUTPUT_PRICE = 0.30   # dollars per 1 million output tokens


def extract(client, text, tries=3):
    prompt = PROMPT.format(fields=", ".join(FIELDS), document=text)
    last_error = None
    for attempt in range(1, tries + 1):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_completion_tokens=4000,
                reasoning_effort="low",
                response_format={"type": "json_object"},
            )
            usage = {
                "input_tokens": resp.usage.prompt_tokens,
                "output_tokens": resp.usage.completion_tokens,
            }
            return json.loads(resp.choices[0].message.content), usage
        except Exception as e:
            last_error = e
            print("  attempt", attempt, "failed")
    raise last_error


def main():
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    os.makedirs("outputs", exist_ok=True)
    results = []
    total_in = total_out = 0

    for s in SOURCES:
        path = os.path.join("docs", s["file"])
        with open(path, encoding="utf-8") as f:
            text = f.read()
        print("Reading", s["file"])
        try:
            fields, usage = extract(client, text)
        except Exception as e:
            print("  failed:", e)
            fields, usage = {}, {"input_tokens": 0, "output_tokens": 0}
        total_in += usage["input_tokens"]
        total_out += usage["output_tokens"]
        results.append({
            "scheme_ref": s["scheme_ref"],
            "source_name": s["file"],
            "captured_on": str(date.today()),
            "model": MODEL,
            "usage": usage,
            "fields": fields,
        })

    with open("outputs/raw_extractions.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    cost = total_in * INPUT_PRICE / 1_000_000 + total_out * OUTPUT_PRICE / 1_000_000
    print("Saved outputs/raw_extractions.json")
    print("Tokens: input", total_in, "output", total_out)
    print("Estimated cost for", len(SOURCES), "documents: $" + format(cost, ".6f"))
    print("Average per document: $" + format(cost / len(SOURCES), ".6f"))


if __name__ == "__main__":
    main()

