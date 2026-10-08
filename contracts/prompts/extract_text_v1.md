<!-- Shared extraction prompt. Used verbatim by android ExtractionPromptBuilder (Tier A/B)
     and backend llm/prompts loader (Tier C). Edit only in the BACKEND workspace on a contract/ branch. -->
You extract data from one Indian receipt or invoice. The text below came from OCR and may contain errors.

Return ONLY a JSON object that matches the schema provided. No prose, no markdown fences.
Rules:
- Copy values that appear in the text. Never invent a value. If a field is absent, omit it.
- Amounts: integer paise (₹1,640.00 -> 164000). Currency is always "INR".
- Dates: YYYY-MM-DD. Indian receipts usually write day first (13/10/26 -> 2026-10-13).
- doc_type: one of flight, rail, cab, hotel, meal, fuel, toll, telecom, broadband, other.
- conf: your confidence 0..1 that the value is exactly right as printed.
- gstin: 15 characters exactly as printed; do not correct it.
- If CGST and SGST are printed, fill both; if IGST is printed, fill igst_paise only.

Schema:
{{schema}}

OCR text:
<<<
{{ocr_text}}
>>>
