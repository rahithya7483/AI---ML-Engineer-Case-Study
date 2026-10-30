# Scheme Field Extraction with Evidence (Case Study A1)

Haqdarshak AI/ML Engineer case study. Problem chosen: A1, field extraction with evidence.

## What this project does

It reads a government scheme document and pulls out 10 fields: scheme name, department, benefit type, benefit amount, benefit frequency, eligibility, documents required, how to apply, deadline and official link.

Every value comes with the exact text it was taken from, the page, the source file name and the date it was captured. If the source does not say something, the field is left empty and marked "not found". If two sources disagree, both values are kept and the field is marked "conflict".

Everything the AI produces is only a draft. A person has to check it before it is used.

## How to run
1. Install the library: `pip install -r requirements.txt`
2. Set your Groq key in PowerShell (do not write it inside any file):
   `$env:GROQ_API_KEY="your_key_here"`
3. Run these from the main folder, in this order:
   - `python src/extract.py` (asks the model, saves `outputs/raw_extractions.json`)
   - `python src/verify.py` (checks the evidence, finds conflicts, saves `outputs/records.json`)
   - `python src/evaluate.py` (compares with `gold/gold.json` and prints the scores)

## Folder

- `docs/` : 4 synthetic sample documents
- `gold/gold.json` : answer key for checking accuracy
- `src/` : the three scripts
- `outputs/` : created when the scripts run

## Sample documents (all synthetic)

- S1: English state circular (`s1_circular_en.txt`) and a made-up MyScheme listing (`s1_myscheme_listing.txt`). The two disagree on the amount (Rs. 25,000 vs Rs. 30,000) and the deadline (31 March 2027 vs 31 December 2026).
- S2: Hindi circular (`s2_circular_hi.txt`).
- S3: a text file made to look like bad OCR output (`s3_scanned_ocr.txt`), with errors like "1,O00" and "Scho1arship". It has no deadline and no link on purpose.

No real government documents or real URLs are used.

## How it works

1. **extract.py** sends each document to the model and asks for each field with its value, exact evidence text and page. The prompt tells the model not to guess and to leave a field empty if the document does not say it. If the model returns an empty answer, the script retries up to 3 times.
2. **verify.py** checks whether the evidence text really exists in the source document (ignoring line breaks and extra spaces). If it does not, the value is thrown away and the field becomes "not found" with a note. It then compares sources of the same scheme. If benefit amount, deadline or official link differ, the status becomes "conflict" and every value is kept with its own source.
3. **evaluate.py** compares the final records with the answer key.

Output format for each field: scheme_ref, field, value, evidence (text, location, source, captured_on), confidence, status, note.

Confidence is not taken from the model. It is "high" when the evidence was found in the document and "low" when there is a conflict. I did this because a model can say it is sure even when it is wrong.

## Model and cost

Model: `openai/gpt-oss-20b` on Groq.

I measured the cost on my 4 sample files. Total tokens: 2,185 input and 1,412 output. At Groq's price (about $0.075 per 1 million input tokens and $0.30 per 1 million output tokens, checked on 30 October 2026), this is about $0.0006 for 4 documents, or about $0.00015 per document.

My sample files are very short. A real government document is longer, so my guess for a real document is about 2,000 input and 1,000 output tokens, which is about $0.00045. For 5,000 schemes with 1-2 documents each, that is roughly $2 to $5. Retries and long scanned documents will cost more. The cost is printed every time `extract.py` runs.

## Results

On the 4 sample documents (3 schemes, 30 fields):

- Status (found / not found / conflict): 30 out of 30 correct
- Benefit amount value: 3 out of 3 correct
- Deadline value: 2 out of 2 correct
- No value was rejected by the evidence check

**This score is weak and I do not trust it fully.** The status check only asks whether the AI said found / not found / conflict. It does not check if the text is right. When I read the text fields myself I found mistakes.

My first run had 4 mistakes. I then changed the prompt (clean OCR errors in values, a short label for benefit type, keep installment details). Three were fixed: S1 benefit_type, S2 benefit_frequency and S3 benefit_type.

Still wrong after the change:
- S3 scheme_name and department still have the OCR mistakes in the value ("Scho1arship", "Schoo1"). The prompt asked for clean text but the model did not do it.
- S2 land record is written as "khusra" instead of "khasra". The model translated the Hindi word and spelled it wrong.
- S2 values now come back in English, but my prompt does not say which language to use.

I changed the prompt after looking at the results of these same 3 documents, so these results are better than what I would expect on new documents. A reviewer would notice the remaining mistakes only by reading the text fields next to the documents.

## Assumptions

- The documents are synthetic, so real documents will be messier (tables, stamps, many schemes in one PDF).
- The scanned document is simulated as OCR text. I did not run real OCR on an image.
- The answer key was drafted with help from Claude and then checked by me against the documents. It is only 3 schemes, so it is a very small test.
- I compare only benefit amount, deadline and official link across sources. Comparing free text like eligibility would give many false conflicts because the same thing can be worded differently.
- A missing page marker (like in the MyScheme listing) is noted instead of guessed.

## What I left out on purpose

- Real OCR on scanned images or PDFs
- Documents that contain several schemes
- Scoring text fields by code (wording differs too much, and Hindi vs English makes it harder). They are printed for a person to read.
- Checking Hindi answer quality properly (I only checked the evidence text matches the source)
- Cleaning OCR errors in values
- A review screen for researchers
- Cost tracking
- Deciding the quality bar for running on 5,000 schemes (see below)

## When is it good enough for 5,000 schemes?

My suggestion, not something I have tested:

1. A researcher checks a random sample of about 200 schemes by hand, covering different document types, languages and states.
2. Measure accuracy for each field separately, not one overall number.
3. Set a higher bar for risky fields. Amount, deadline and eligibility should be nearly always right, because a wrong value can reach a citizen. Less risky fields can have a lower bar.
4. Fields that fail the bar go to a person for checking on every scheme.
5. Keep sampling after launch to see if quality drops.

## What "field-level accuracy" means

It means we mark each field separately, like marking each question on a form, instead of giving one score to a whole scheme. For example, for 100 schemes we count how many had the benefit amount right, how many had the deadline right, and so on. This tells the team which fields can be trusted and which need a person to check.

## Where AI tools were used

I used Claude to help plan the steps, write the code and draft the answer key and this README structure. I ran the code myself, checked the outputs and checked the answer key against the documents.
