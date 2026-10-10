# Kharcha PRD — text version for Claude Code
<!-- Generated from docs/PRD.pdf with pdftotext -layout. Read THIS file, never the PDF.
     Sections are marked "## PRD §n". Diagrams and tables are flattened, so prefer docs/SPEC.md,
     docs/TASKS.md, docs/schema.sql and contracts/ for exact values.
     Superseded by docs/SPEC.md for this VM: no Caddy (host nginx instead), no MinIO (local storage),
     no local LLM (NVIDIA hosted only), no micro VMs (single kh-core server). -->

## PRD §1 — Executive summary

Filing an expense claim is low-value work that every employee does and nobody enjoys. People
collect paper and digital bills, retype amounts and dates, guess the right category, check a
policy they half remember, and then wait for a claim to bounce back because a GST number
was missing or a hotel exceeded a cap. Finance teams then repeat much of the same
checking by hand.

Kharcha is an AI-native reimbursement assistant on Android with a chat-style interface. The employee drops in
photos, PDFs, screenshots or forwarded e-bills. On-device AI reads each document, extracts structured fields,
checks whether the document looks genuine, applies policy rules, spots duplicates, groups expenses into trips
or categories, asks only the questions it truly cannot answer itself, and produces a claim that is ready to submit
to a (mocked) finance system.

     <2 min                       ≤2                        ≥95%                        -60%
     User time from 10 receipts   Median questions asked    Field accuracy on amount,   Finance review time per
     to a submit-ready claim      per claim                 date, vendor (golden set)   claim (target)
     (target)

Why this design
• On-device first. Receipts carry personal data (names, phone numbers, card digits, locations). Reading them
  on the phone keeps raw images local until the user submits, works offline in a cab or airport, and removes
  per-receipt cloud inference cost.
• Agent, not form. The assistant owns the claim. It tracks what is complete, missing or questionable and drives
  the conversation to "ready" with the fewest possible taps.
• Trust is explainable. Every flag (possible edit, duplicate, policy breach) carries evidence and a
  plain-language reason. The system never auto-rejects; people decide.
• Mock the edges, build the core. The finance/ERP system, SSO and payouts are mocked so the build effort
  goes into extraction, verification and the experience.

  One-line pitch
  Kharcha turns a pile of receipts into a verified, policy-checked, submit-ready claim in under two minutes, and
  gives finance a claim they can approve without re-checking every bill.

                WHY THIS MATTERS

## PRD §2 — Problem and opportunity

Where time and money leak today
 Stage               What happens today                                         Cost of the problem

 Collecting          Paper bills fade or get lost; e-bills are scattered        Claims filed late or never; out-of-pocket loss for
                     across email, cab apps and WhatsApp.                       employees.

 Data entry          Employee retypes vendor, date, amount, GST,                Typically 2 to 4 minutes per receipt; typos in
                     category for each bill.                                    amounts and dates.

 Policy              Employee guesses limits; policy PDF is long and            Claims returned for avoidable reasons; frustration
                     rarely read.                                               on both sides.

 Verification        Finance eyeballs each bill for edits, duplicates and       Slow approvals; inconsistent checks; fraud and
                     missing GSTIN.                                             duplicates slip through.

 Follow-up           Back-and-forth emails for missing details, often           Long cycle time; context lost; poor employee
                     days later.                                                experience.

Illustrative value model
The numbers below are planning assumptions for a mid-sized organisation, not measured data. The prototype will measure actual
time saved on a synthetic test set and replace these assumptions.

 Assumption                                           Value                 Notes

 Employees filing claims                              1,000                 Sales, field and travelling staff file most claims

 Claims per employee per month                        2                     Average of ~5 receipts per claim

 Employee time saved per claim                        20 min                From ~23 min manual to ~3 min with Kharcha

 Finance time saved per claim                         6 min                 Pre-verified fields, evidence-backed flags

 Loaded cost per hour                                 ₹600                  Blended assumption

 Monthly hours saved                                  ~870 h                667 h employees + 200 h finance

 Monthly value                                        ~₹5.2 lakh            Before leakage recovered from duplicates and
                                                                            over-limit claims

                WHAT WE WILL AND WILL NOT DO

## PRD §3 — Goals, non-goals and success metrics

Goals
• G1. Minimise user effort from receipts to a submit-ready claim, measured in time and taps.
• G2. Produce structured, reliable claim data with field-level confidence and evidence.
• G3. Detect likely tampered, recaptured or duplicate documents and explain why.
• G4. Apply policy before submission so claims are right first time.
• G5. Keep personal data on the device by default and degrade gracefully on low-end phones.

Non-goals for the prototype
• Integration with a real ERP or payroll system (a mock finance API stands in).
• Corporate card feed reconciliation, multi-currency FX and per-country tax regimes beyond India GST.
• Final fraud determination. Kharcha raises risk signals; humans decide.
• iOS app and full web app for employees (a light approver console is in scope).

Success metrics
 Metric                  Definition                                      Target              How measured

 Time to ready           User active time from first drop to "Ready to   < 2 min             Instrumented timestamps in app
                         submit" for 10 receipts

 Questions per           Agent questions that need a user answer         Median ≤ 2          Agent event log
 claim

 Key-field accuracy      Exact match on total, date, vendor, GSTIN       ≥ 95%               Golden set of 300 documents

 Category accuracy       Correct expense category vs label               ≥ 92%               Golden set

 Tamper detection        Recall on tampered set at ≤ 10% false           ≥ 80% recall        Synthetic tampered variants
                         positives

 Duplicate               Recall on planted duplicates                    ≥ 95%               Planted pairs in dataset
 detection

 First-pass approval     Claims approved without being returned          +30 pts vs          Mock approver flow
                                                                         baseline

 Over-limit leakage      Over-limit amounts submitted without a          0                   Planted over-limit scenarios
                         flag or exception

 On-device latency       Per-receipt extraction, mid-range phone         p50 < 3 s           Benchmark harness

              WHO WE ARE BUILDING FOR

## PRD §4 — Users and personas

 Persona                         Context                                              Needs from Kharcha

 Priya, field sales executive    Travels 3 to 4 days a week. 30+ small receipts       Wants one place to throw everything and be
                                 a month: cabs, meals, tolls, fuel, hotel. Files      told what is missing. Hates retyping and
                                 claims in batches on Sunday nights.                  getting claims returned.

 Arjun, software engineer        Claims rarely: broadband, an offsite hotel, a        Wants it to just work and to know upfront
                                 conference ticket. Does not remember the             whether something is reimbursable.
                                 policy.

 Meera, approving manager        Approves 40 claims a month for her team,             Wants a short summary with anything
                                 mostly on mobile between meetings.                   unusual highlighted and the evidence one
                                                                                      tap away.

 Vikram, finance reviewer        Audits claims before payout. Looks for               Wants structured data, consistent checks
                                 duplicates, edits, missing GST invoices, policy      and an audit trail he can defend.
                                 breaches.

Jobs to be done
• "When I get back from a trip, help me turn everything I collected into one correct claim without retyping
  anything."

• "Tell me before I submit if something will be rejected, and what I can do about it."
• "When I approve, show me only what needs my judgement, with proof."

                    USER-FACING CHALLENGE

## PRD §5 — The experience: pile to ready

The core interaction is a chat thread with a drop zone. Everything else (cards, checklists, chips) appears inside
that thread so the user never has to learn a form. Processing starts the instant a file lands; the user can keep
dropping more while earlier receipts are being read.

END-TO-END JOURNEY

           1                              2                               3                     4                             5                                 6

     Capture                        Understand                         Verify               Clarify                     Assemble                       Submit
 Snap, share, forward               On-device OCR +             Authenticity, policy,   Only the questions             Grouped, totalled,          Mock finance API,
    or drop PDFs                     LLM extraction                 duplicates             that matter                  policy-checked               live status

                                     Target: pile of 10 receipts to ready-to-submit claim in under 2 minutes of user time

                                  Figure 1. Six stages; the user is only actively involved in Capture, Clarify and Submit.

  Kharcha                                      Review                                    Assistant                                    Ready to submit

   Hi Priya, drop your                           Pune client visit
   receipts here.                                                                          Hotel was ₹4,900/night,
                                                 12 to 14 Oct | 6 items
                                                                                           policy cap for Pune is
                                                                                           ₹4,500. Reason?
                                                      Flight IndiGo        ₹8,420

                                                      Hotel 2 nights       ₹9,800
        Drop photos / PDFs
        or scan, share, forward
                                                      Cabs x3                 ₹1,265           Client-booked venue
                                                                                                                                               ₹22,124
                                                      Dinner                  ₹1,640
                                                                                                No cheaper option                            7 items | 2 claims

                                                                                                                                              Receipts verified
                                                                                               Pay difference myself
                                                 Home broadband Oct                                                                         Policy checks passed
   Uber_12Oct.pdf
                                                 1 item | ₹999
                                                                                                                                            1 flagged with reason
   IMG_2231.jpg                                   Within policy                                  No cheaper option
                                                                                                 near client site                              No duplicates
   Hotel_inv.pdf
                                                                                                                                      Approver: Meera S.
   IMG_2240.jpg                                  Possible duplicate
                                                                                           Got it. Was dinner with                    Est. payout: next cycle
                                                 Cab ₹412 claimed in Sep
                                                                                           a client? Yes / No
   12 receipts | 8 read on device

                                                        2 things need you                                                                     Submit claim
    Message...                                                                             1 of 2 questions

                 1 Drop                                        2 Review                             3 Clarify                                   4 Submit

                                                 Figure 2. Low-fidelity wireframes of the four key screens.

Experience principles
 Principle                        What it means in the product

 Do the work, then ask            Extract, infer and default everything possible before asking. A question is a last resort, not a
                                  form field.

 Ask once per context             Business purpose is asked once per trip, not per receipt. Attendees are asked only where
                                  policy requires them.

 One-tap answers                  Every question offers suggested answers as chips, with free text as a fallback. Voice input is
                                  supported.

 Show status, not steps           Each receipt and claim shows a clear state: Done, Needs you, Flagged. A single counter
                                  says how many things need attention.

 Explain every flag               "We could not verify this hotel invoice: the PDF was modified after it was issued" rather than
                                  "Suspicious document".

 Non-accusatory tone              Flags are framed as checks the system could not complete, giving the employee a chance
                                  to explain or re-upload.

 Always reversible                Every auto-filled value is editable in place; the original document and highlighted source
                                  region are one tap away.

Capture channels
 Channel                     Behaviour                                                                                     Pri

 Camera scan                 ML Kit Document Scanner with auto edge detection, deskew and multi-page capture.              P0

 Gallery / file picker       Multi-select images and PDFs; bulk drop of 20+ files.                                         P0

 Android share sheet         Share a cab receipt PDF or screenshot from any app straight into Kharcha.                     P0

 Email forward               Forward e-bills to a personal claims address; backend parses attachments (mocked              P2
                             mailbox).

 Long receipts               Stitch multiple photos of a long thermal receipt into one document.                           P2

             WHAT THE SYSTEM MUST DO

## PRD §6 — Functional requirements

6.1 Ingestion and understanding
 ID         Requirement                                         Pri   Acceptance criteria

 ING-1      Accept JPG, PNG, HEIC, WEBP and PDF (single         P0    20 mixed files queue without blocking UI; progress shown
            and multi-page), up to 20 files per drop.                 per file.

 ING-2      Run a quality gate for blur, glare, cut-off         P0    Blurred test images trigger a retake prompt within 1 s.
            edges and low resolution before OCR.

 ING-3      Use the embedded text layer for digital PDFs;       P0    Digital PDFs skip OCR; text matches source.
            OCR only when it is missing.

 EXT-1      Classify each document: cab, flight, rail, hotel,   P0    ≥ 92% category accuracy on golden set.
            meal, fuel, toll, telecom, other.

 EXT-2      Extract vendor, date, time, total, tax lines,       P0    Fields returned as typed JSON with per-field confidence
            GSTIN, invoice number, payment mode, city,                and source box.
            line items.

 EXT-3      Handle multiple receipts in one photo and           P1    Two receipts in one image become two expense lines.
            multi-receipt PDFs by splitting them.

 EXT-4      Support English and Hindi text; mixed scripts       P1    Hindi vendor names extracted on test set.
            on the same bill.

 EXT-5      Normalise values: dates to ISO, amounts to          P0    "Ola Cabs", "OLA" and "ANI Technologies" map to one
            paise integers, vendor names to canonical                 vendor.
            form.

6.2 Verification and policy
 ID         Requirement                                         Pri   Acceptance criteria

 VER-1      Compute a trust score (0 to 100) per                P0    Score and top reasons visible on each receipt card.
            document from authenticity signals (Section
            11).

 VER-2      Validate GSTIN format and checksum;                 P0    Bad checksum or mismatched math raises a flag with
            validate tax arithmetic (CGST + SGST or IGST              the numbers shown.
            vs total).

 VER-3      Detect duplicates within a claim, across the        P0    Planted duplicates flagged with link to the original claim.
            user's past claims and across employees.

 POL-1      Evaluate each line against policy rules held as     P0    Rule changes in JSON apply without an app release.
            data (limits, eligibility, receipts needed).

 POL-2      Show the reason and the rule for every              P0    Each breach has rule ID, limit, actual and remedy options.
            breach, and offer remedies (justify, split, pay
            difference).

 POL-3      Show "will this be reimbursed?" before              P1    Answer appears within 1 s of extraction.
            submission for any single receipt.

 ENT-1      Check every line against the employee's own         P0    Exhausted, partly covered and not-entitled states shown
            per-category and overall limits fetched from              per line (Section 9).
            the (mock) ERP.

6.3 Agent, grouping and claim assembly
 ID          Requirement                                       Pri      Acceptance criteria

 AGT-1       Group expenses into trips or categories using     P0       Flight + hotel + cabs in same city and dates become one
             dates, cities and travel bookings.                         trip.

 AGT-2       Track claim completeness: complete, missing,      P0       A single "N things need you" counter that reaches zero.
             questionable, for every line and the claim.

 AGT-3       Ask only questions required by policy or by       P0       Median ≤ 2 questions per claim on test scenarios.
             low confidence; batch them; offer chips.

 AGT-4       Accept natural-language edits ("the dinner        P1       Attendee and purpose fields updated correctly.
             was with two clients from Acme").

 CLM-1       Generate a submission-ready claim with            P0       Claim JSON passes mock finance schema validation.
             summary, lines, attachments and flag notes.

 CLM-2       Submit to the mock finance API and show live      P0       Status changes from mock API appear in the thread.
             status (submitted, in review, approved, paid).

 CLM-3       Approver console: summary, flags with             P1       Returned claim reopens in the employee's thread with
             evidence, approve / return / reject with                   the comment.
             comment.

 CLM-4       Export claim as a PDF report with receipts        P2       PDF includes summary table and all images.
             appended.

              THE QUESTION POLICY

## PRD §7 — Asking only what is necessary

The agent decides whether to ask a question with a simple, inspectable rule rather than leaving it to the LLM. A
question is asked only when a field is required (by policy or by the finance schema) and it is either missing or
below its confidence threshold and it cannot be inferred from other documents in the same claim.

  ask(field) = required(field, line, policy)
            AND (missing(field) OR confidence(field) < threshold(field))
            AND NOT inferable(field, claim_context)

  priority    =   blocking_submit * 3 + policy_breach * 2 + low_confidence * 1
  batch       =   group questions by trip / context; max 3 per turn

 Situation                                  Asked?            Example question

 Total extracted at 0.98 confidence         No                (auto-filled)

 Business purpose missing for a 3-day       Once per trip     "What was the Pune trip for?" [Client visit] [Training] [Internal
 trip                                                         meeting]

 Meal above per-person limit                Yes               "Was this dinner with clients? How many people?" [Just me] [2] [3+]

 Hotel above city cap                       Yes               "Hotel was ₹4,900 a night vs ₹4,500 cap. Reason?" [Client venue]
                                                              [No cheaper option] [I'll pay the difference]

 Cab receipt city unclear but flight        No                (inferred from trip context)
 shows Pune

 Total at 0.62 confidence, smudged          Yes, with crop    "Is the total ₹1,640?" shown with highlighted crop [Yes] [Edit]

             RULES AS DATA

## PRD §8 — Sample policy for the prototype

The prototype ships with a synthetic policy so rules can be demonstrated end to end. Rules are stored as JSON
and evaluated by the backend policy engine; a cached copy runs on device for instant feedback.

 Rule ID       Category         Rule                                                             On breach

 P-HTL-1       Hotel            Tier-1 metro ≤ ₹6,000 / night; other cities ≤ ₹4,500 / night     Justify or pay difference

 P-MEAL-1      Meals            ≤ ₹1,000 per person per day when travelling; client meals need   Justify; attendees required
                                attendees

 P-CAB-1       Local travel     Economy cab classes only; premium class needs a reason           Justify

 P-GST-1       All              Bills above ₹5,000 need a GST invoice with company GSTIN         Flag; request proper invoice

 P-AGE-1       All              Receipts older than 60 days are not reimbursable                 Block submit; route to
                                                                                                 manager exception

 P-EXCL-1      All              Alcohol, fines, personal items and loyalty-point redemptions     Exclude line; show reason
                                excluded

 P-TEL-1       Telecom          Broadband needs a bill in the employee's name or address;        Request proper bill; apply
                                amount capped by the employee's entitlement (Section 9)          entitlement

  {
      "id": "P-HTL-1",
      "applies_to": { "category": "hotel" },
      "limit": { "per": "night", "amount_paise": {
          "city_tier == 1": 600000, "default": 450000 } },
      "on_breach": { "severity": "amber",
          "remedies": ["justify", "pay_difference"], "requires": ["reason"] }
  }

             PER-PERSON BALANCES FROM FINANCE

## PRD §9 — Employee entitlements and claim limits

Policy rules (Section 8) apply to every employee and judge a single expense: is this hotel night too expensive?
Entitlements are different. They are each employee's own budget for a category over a period, such as ₹15,000
a year for broadband or ₹4,000 a month for travel meals. They vary by grade, role, location and individual
approvals, so Kharcha never hard-codes them. It reads them from the finance / ERP system (mocked for the
prototype) and tracks how much is used.

EMPLOYEE ENTITLEMENTS (FROM MOCK ERP, FY 2026-27)

Broadband
                                                                                                                         Exhausted
₹15,000 / year
                                            ₹999 over limit

Meals (travel)
                                                                                                                        Partly covered
₹4,000 / month
                                            ₹40 over limit

Hotel
                                                                                                                          Available
₹60,000 / year
                                            ₹32,200 left after this claim

Mobile bill
                                                                           no balance for this category                  Not entitled
Not in entitlement

    Paid / approved             Pending (submitted)           This draft                       Over limit   Remaining

                                       Available = Limit - Paid - Pending - Reserved by other drafts

                      Figure 3. How a draft claim is checked against each employee's balances. Values are synthetic.

How the balance is calculated
For each category and period, the ERP supplies the limit and the amount already paid. Kharcha adds what it
knows that the ERP may not yet show: claims submitted but not yet paid (pending) and amounts reserved by
the employee's other open drafts. Available = limit - paid - pending - reserved. The server recalculates this at
submit time with the latest ERP data; the value on the phone is a preview with an "as of" time.

Order of checks for each expense line
1. Eligibility. Is this category in the employee's entitlement at all? If not, the line is marked "Not entitled".
2. Policy rule. Company-wide rule for the single expense (cap per night, GST invoice, receipt age).
3. Category entitlement. Does the amount fit in the remaining category balance for the period of the expense
   date?
4. Overall cap. If the ERP sets a total reimbursement cap across categories, check that too.
5. Reimbursable amount. The lowest of the bill amount, the policy cap and the available balances becomes
   the claimable amount; the rest is shown as not reimbursable.

States shown to the employee
 State             When                       What the assistant says (example)                              Options

 Available         Amount fits with room      "Broadband ₹999 is covered. ₹2,001 of ₹15,000 left this        None needed
                   left                       year."

 Nearly used       80% or more of the limit   "After this, only ₹400 is left for travel meals this month."   None needed
                   used after this claim

 Partly            Bill is more than the      "₹1,600 of this ₹1,640 dinner can be claimed; ₹40 is           Claim covered part /
 covered           remaining balance          over your monthly meal limit."                                 Request exception

 Exhausted         Balance is zero for the    "Your broadband limit of ₹15,000 for FY 2026-27 is fully       Remove / Keep for
                   period                     used. It resets on 1 Apr 2027."                                records / Request
                                                                                                             exception

 Not entitled      Category not in the        "Mobile bills are not part of your reimbursement plan."        Remove / Ask
                   employee's entitlement                                                                    manager

 Unknown           ERP unreachable and        "I could not check your balance; it will be checked            Continue
                   no cached data             when you submit."

  Tell the user early, not at submit
  The balance is shown as soon as a receipt is read, and the chat home shows a small "limits" strip for the
  categories the employee claims most. An exhausted category is mentioned before the employee spends time
  answering questions about that receipt. The assistant never asks for a business purpose on a line that cannot
  be reimbursed.

Requirements
 ID         Requirement                                         Pri   Acceptance criteria

 ENT-1      Fetch each employee's entitlements from the         P0    Mock ERP returns different limits for different employees;
            mock ERP: category, limit, period (month,                 app shows them.
            quarter, financial year, per trip), period dates,
            paid amount, overall cap.

 ENT-2      Compute available balance including                 P0    Two drafts cannot both use the same ₹2,000.
            pending claims and reservations from other
            drafts.

 ENT-3      Show per-line state (available, nearly used,        P0    Exhausted broadband shows the message and reset
            partly covered, exhausted, not entitled) with             date.
            the reset date.

 ENT-4      Split a line into reimbursable and                  P0    Claim total equals the covered amount; excess listed
            non-reimbursable parts when partly covered.               separately.

 ENT-5      Use the period that contains the expense            P0    A March bill submitted in April uses the March balance.
            date, not the submission date.

 ENT-6      Re-check balances on the server at submit; if       P0    Stale cache never lets an over-limit claim through
            they changed, update the claim and tell the               unflagged.
            user before sending.

 ENT-7      Release reservations when a claim is                P1    Balance increases immediately in the app.
            returned, rejected or a line is deleted.

 ENT-8      Exception request: send the over-limit part to      P1    Approver console shows exception separately from the
            the manager with a reason.                                main claim.

 ENT-9      Cache entitlements on device with a                 P1    Offline mode shows "as of" time.
            fetched-at time for offline use; refresh at app
            open and before submit.

Edge cases
• Pro-rata limits for joiners, leavers and grade changes come from the ERP; Kharcha does not calculate them.
• Multi-period bills (a quarterly broadband bill) are counted in the period of the bill date unless the ERP says
  otherwise.
• Refunds and credit notes reduce the paid amount and free up balance when the ERP reports them.
• Same bill, two people (shared hotel room) is a duplicate check, not an entitlement split, in the prototype.

             BACKEND CHALLENGE, PART 1

## PRD §10 — AI pipeline and on-device models

Extraction is a hybrid of a generative model and deterministic code. The model reads messy layouts and
normalises them into a strict schema; code then validates everything it can (checksums, arithmetic, dates) so
the model is never the only source of truth for a number.

ON-DEVICE EXTRACTION PIPELINE

                        ask to retake

           Input                        Quality gate                          Read                   Classify                   Extract
        Image / PDF /                     Blur, glare,                     OCR or native          Cab, meal, hotel,            LLM to JSON
         screenshot                        crop, DPI                         PDF text               flight, fuel...          schema + bbox

        High: auto-fill, show as done
                                                         Confidence gate                   Trust signals                     Validate
                                                            per field vs                   EXIF, metadata,                GSTIN checksum,
                                                             threshold                       edit traces                  tax math, dates
      Low: ask user or cloud fallback

      Figure 4. Each receipt flows through the same pipeline; low-confidence fields become questions or go to a cloud fallback.

Device tiering
On-device LLM support varies widely across Android hardware, so the app picks a path at runtime based on
capability checks, available RAM and thermal state.

 Tier      Device profile                          Extraction path                                  Notes

 A         Devices supporting ML Kit               ML Kit Text Recognition v2 + Gemini Nano         Best latency, no model download. Check
           GenAI (Gemini Nano via                  Prompt API with JSON-schema prompt               feature availability at runtime; supported
           AICore)                                                                                  device list is limited.

 B         ≥ 6 GB RAM, recent SoC, no              OCR + small open model (e.g. Gemma               One-time model download (~0.5 to 1 GB).
           AICore                                  family, 1B-class int4) via LiteRT-LM             Run only when charging or thermal
                                                                                                    headroom allows for large batches.

 C         Low-end or thermally                    On-device OCR only; redacted text sent to        User consent required; PII redaction
           throttled                               backend LLM                                      before upload.

     Thermal and memory guardrails
     Batch extraction checks the Android thermal status before each document and pauses or downgrades to Tier
     C when the device reports moderate or higher throttling. Only one model instance is kept in memory; OCR runs
     while the LLM is idle to keep peak memory low. These limits are measured in the benchmark harness on at least
     one mid-range device.

Extraction contract
The model is prompted with the OCR text (and, on multimodal tiers, the image) plus a strict JSON schema.
Output that fails schema validation is retried once with the error message, then falls back.

  {
      "doc_id": "d_8f21", "doc_type": "meal", "lang": ["en"],
      "vendor":   { "value": "Barbeque Nation, Koregaon Park", "conf": 0.97, "bbox": [42,18,310,44] },
      "date":     { "value": "2026-10-13", "conf": 0.99 },
      "total":    { "value_paise": 164000, "currency": "INR", "conf": 0.96 },
      "tax":      { "cgst_paise": 3905, "sgst_paise": 3905, "rate": 5, "conf": 0.91 },
      "gstin":    { "value": "27ABCDE1234F1Z0", "checksum_ok": true },
      "invoice_no": { "value": "KP/26/04412", "conf": 0.88 },
      "payment_mode": { "value": "UPI", "conf": 0.80 },
      "line_items": [ { "desc": "Veg buffet x2", "amount_paise": 156190 } ],
      "trust": { "score": 86, "signals": ["camera_capture", "exif_consistent", "tax_math_ok"] }
  }

                                                  Example values are synthetic.

Evaluation plan
• Golden set: 300 documents (200 synthetic generated from templates with randomised vendors, layouts,
  lighting and fold artefacts, plus 100 from public receipt datasets such as SROIE and CORD, subject to their
  licences).
• Tampered set: edited totals, altered dates, pasted logos, screenshots of screens, re-saved PDFs, and exact
  and near duplicates.
• Metrics: per-field exact match, category accuracy, tamper precision and recall, questions per claim, latency
  p50 and p95 per tier.
• Regression: evaluation runs in CI on every prompt or model change, with a results table committed to the
  repository.

              IS THIS DOCUMENT GENUINE?

## PRD §11 — Authenticity and fraud signals

No single check proves a receipt is genuine. Kharcha combines many weak signals into a trust score and shows
the strongest reasons. Cheap checks run on device at capture time; heavier forensics run on the backend after
submission.

 Signal                 What it checks                                                      Where     Weight

 Capture source         Live camera scan vs gallery vs screenshot vs downloaded PDF         Device    Low

 EXIF consistency       Capture time vs receipt date; editing software tags; missing EXIF   Device    Med
                        on a "photo"

 PDF metadata           Producer/creator tool, modification after creation, incremental     Device    High
                        updates, mixed fonts in text layer

 Arithmetic             Line items, tax and total add up; GST rate matches category         Device    High

 GSTIN validity         Format, state code, checksum; (mock) lookup that GSTIN belongs      Both      High
                        to the vendor name

 Screen recapture       Moiré patterns and screen bezels suggesting a photo of a screen     Backend   Med

 Error level analysis   JPEG recompression differences around the total or date region      Backend   Med

 Template match         Layout compared with known vendor templates (cab apps,              Backend   Med
                        airlines, hotel chains)

 Duplicate              SHA-256 exact, perceptual hash near-duplicate, and vendor +         Backend   High
                        date + amount fuzzy key

 Signal                       What it checks                                                                  Where            Weight

 Behavioural                  Round-number totals, sequences just under limits, many receipts                 Backend          Low
                              from one small vendor

TRUST SCORE BANDS (PER DOCUMENT)

0 to 49 Hold                                                            50 to 79 Flag                                    80 to 100 Clear
Needs justification + reviewer                                          Submitted with visible flag                      No friction for employee

                            Figure 5. Bands are tuned on the tampered set to keep false positives at or below 10%.

  Fairness guardrail
  Low-trust documents are never auto-rejected. Thermal paper fades, small vendors issue handwritten bills, and
  genuine PDFs are sometimes re-saved. The employee always sees why a document was flagged and can add
  a note, upload a better copy or attach supporting evidence. Every override is recorded in the audit log.

                 HOW THE PIECES FIT

## PRD §12 — System architecture

  ANDROID APP (ON-DEVICE)                                                    BACKEND (CLOUD)
                                                           extracted
                                                             JSON
    Chat UI (Jetpack Compose)
    Drop zone, receipt cards, one-tap answers
                                                                               API Gateway + Auth (mock SSO / JWT)
                                                                               Upload, sync, rate limits, audit log

    Capture & Ingest                                       questions,
                                                                               Agent Orchestrator
    ML Kit Doc Scanner, PdfRenderer, share-sheet             flags
                                                                               LLM with tools: group, check_policy, find_dupes,
                                                                               ask_user, build_claim. Tracks claim completeness.

    Quality Gate
    Blur, glare, crop, resolution checks
                                                                               Policy Engine                          Duplicate Svc
                                                                               Rules as data                          Hash + pHash + fuzzy

    OCR / Text Layer
    ML Kit Text Recognition v2; PDF text
                                                                               Trust Service                          Claim Service
                                                                               Deep forensics                         State machine

    Extraction LLM
    Gemini Nano (ML Kit GenAI) / LiteRT-LM

                                                                               PostgreSQL                             Object Storage
                                                            originals
                                                           on submit           claims, lines, flags,                  originals (on submit),
    Validators + Trust Signals                                                 audit events                           encrypted, retention
    GSTIN, arithmetic, EXIF, PDF metadata

    Local Store
    Room + encrypted files, offline queue
                                                                             Mock Finance / ERP                         Approver Console
                                                                             Accepts claims, returns                    Web view for managers
                                                                             ID, simulates approval                     and finance: flags with
                                                                             and payout status                          evidence, one-click act

   AI component                Mocked external system                                         Raw images stay on device until the employee submits.

Figure 6. Reading and first-pass checks happen on the phone; the backend owns the claim, policy, duplicates and deep forensics.

Suggested technology choices
 Layer                         Choice                                                            Reason

 Android app                   Kotlin, Jetpack Compose, Coroutines/Flow, Hilt, Room,             Modern stack; background batch
                               WorkManager                                                       processing survives app kills

 Capture & OCR                 ML Kit Document Scanner, ML Kit Text Recognition v2,              Free, on-device, well-supported
                               PdfRenderer

 On-device LLM                 ML Kit GenAI Prompt API (Gemini Nano); LiteRT-LM with a           Covers capable devices and a broader
                               small Gemma model as fallback                                     fallback tier

 Backend                       Python + FastAPI, PostgreSQL, Redis + RQ, S3-compatible           One language for API, forensics and
                               storage (MinIO)                                                   gateway; light on 1 GB VMs (Section 20)

 Agent                         LLM with tool calling through the LLM gateway (Section            Provider can change by config; tools keep
                               13); tools are backend functions                                  numbers deterministic

 Policy engine                 JSON rules evaluated with JsonLogic-style evaluator               Rules editable without code changes

 Forensics                     Python service: Pillow/OpenCV for ELA and pHash, pypdf            Mature libraries
                               for metadata

 Mock finance                  Small REST service with simulated approval timeline and           Demonstrates submission and status end
                               webhooks                                                          to end

 Approver console              React web app (or Compose for web)                                Light; reads the same claim API

                  NVIDIA HOSTED MODELS

## PRD §13 — Model provider and LLM gateway

All cloud AI in the prototype runs on NVIDIA's hosted models from build.nvidia.com, which are free for
prototyping through the NVIDIA Developer Program and use an OpenAI-compatible API. No model runs on the
Oracle VM; the VM only hosts the backend and the gateway. The backend never calls NVIDIA directly: it asks a
small LLM gateway (LiteLLM) for a task alias, and the gateway picks a primary NVIDIA model, falls back to a
second NVIDIA model, and reports failure so the backend can switch to a no-LLM mode.

LLM GATEWAY: NVIDIA PRIMARY, NVIDIA FALLBACK, THEN NO-LLM MODE

                                                                                                          NVIDIA primary model
                                                                                                     1    build.nvidia.com, per task
                                                       LLM Gateway                                        e.g. nemotron-nano-12b-v2-vl
                                                     LiteLLM on 127.0.0.1:4000

     Kharcha backend
                                                       kh-extract-image                                   NVIDIA fallback model
    api + worker on kh-core
                                                         kh-extract-text                             2    second model, same key
         calls a task alias,
                                                                                                          on 429, 5xx, timeout, bad JSON
     never NVIDIA directly
                                                            kh-agent

                                                            kh-parse

                                                                                                          No-LLM degraded mode
                                                                                                     3    deterministic code in backend
                                                                                                          confirm fields, template replies

         Every call: timeout, one retry on 429, JSON-schema check, then the next step. All calls logged to llm_calls. No model runs on the VM.

                  Figure 7. Task aliases map to NVIDIA models; when both fail, deterministic code keeps the user moving.

Routing by task
 Task alias        Used for                         Primary (NVIDIA)         Fallback (NVIDIA)          If both fail

 kh-extract-im     Tier C phones: receipt image     nemotron-nano-12b-       llama-3.1-nemotron-na      User confirms total,
 age               straight to JSON                 v2-vl                    no-vl-8b-v1                date, vendor

 kh-extract-text   OCR text to receipt JSON         nvidia-nemotron-na       mistral-nemotron           User confirms total,
                                                    no-9b-v2                                            date, vendor

 kh-agent          Agent turns with tool calling    mistral-nemotron         nvidia-nemotron-nano       Template replies from
                                                                             -9b-v2                     the question planner

 kh-parse          Free-text answers ("dinner       nvidia-nemotron-na       mistral-nemotron           Ask again with chips
                   with 2 clients")                 no-9b-v2                                            only

   Model ids are those listed on build.nvidia.com when this PRD was written; confirm each on its model page (task H-05) before
                                                             building.

What to expect from the free endpoints
• Free for prototyping: a Developer Program key (it starts with nvapi-) unlocks the hosted endpoints.
  Production use would need an NVIDIA AI Enterprise licence.
• Limits vary: rate limits depend on the model and account and are not guaranteed. A second model helps
  when a single model is busy; if the limit is account-wide, the no-LLM mode takes over.
• Language: the Nemotron vision models list English only, so Hindi or mixed-script receipts go through
  on-device OCR first and are confirmed by the user when unsure.
• Speed: throughput can drop at peak times. Warm the endpoints before the demo and keep a recorded
  backup run.
• One key, two users: the dev runner and the hosted stack on the same VM share the key. Development stays
  in stub mode unless a task needs live calls.

Gateway rules
• Timeouts: 20 s for extraction, 8 s for agent turns, 5 s for parsing. A timeout counts as a failure.
• Retries: one retry with backoff on HTTP 429 or 5xx, then the fallback model. After 3 failures a model is cooled
  down for 5 minutes.
• Same contract for both models: the same versioned prompt and JSON schema from contracts/; output
  must validate or it counts as a failure.
• Logging: every call writes model, task, latency, tokens and outcome to llm_calls; the metrics slide is built
  from it.
• Key on the server only: NVIDIA_API_KEY lives in the hosted .env on kh-core. The Android app only talks to
  Kharcha's API.
• Swappable later: another provider can be added by gateway config alone; the prototype uses NVIDIA only.

  No-LLM degraded mode
  If both models fail, nothing blocks the employee. Phones on Tier A or B keep their on-device extraction.
  Otherwise the backend stores the OCR text, pre-fills total, date and vendor with simple pattern matching, and
  asks the user to confirm them. The assistant replies from templates driven by the question planner, and the
  app shows a small "assistant in basic mode" banner while /v1/healthz reports llm: degraded.

   Data note
   Only synthetic or public receipts are sent to NVIDIA during the prototype. A production rollout would move to an
   enterprise agreement with data-processing terms or to self-hosted models.

               CORE ENTITIES

## PRD §14 — Data model

 Entity                  Key fields                                                                 Notes

 Employee                id, name, grade, cost_centre, manager_id, home_city                        Synthetic seed data

 Policy                  id, version, rules[] (JSON), effective_from                                Versioned; each check stores the
                                                                                                    version used

 Claim                   id, employee_id, title, trip_id?, status, total_paise, created_at,         State machine in Section 15
                         submitted_at

 ExpenseLine             id, claim_id, document_id, category, date, vendor_id,                      One line per receipt (or split
                         amount_paise, tax, purpose, attendees[]                                    receipt)

 Document                id, sha256, phash, mime, pages, capture_source, storage_uri,               Original stored only after submit
                         trust_score

 ExtractedField          document_id, name, value, confidence, bbox, source                         Full provenance for every value
                         (ocr|llm|user|inferred)

 Entitlement             employee_id, category, period, period_start, period_end,                   Copied from mock ERP; ERP is the
                         limit_paise, paid_paise, overall_cap_paise?, fetched_at                    source of truth

 Reservation             id, entitlement_id, claim_id, line_id, amount_paise, status                Prevents two drafts using the same
                         (held|released|consumed)                                                   balance

 Flag                    id, target (line|doc|claim), type, severity, rule_id?, evidence, status,   Types: policy, entitlement, duplicate,
                         resolution_note                                                            authenticity, missing

 Question                id, claim_id, field, prompt, options[], answer, asked_at,                  Feeds the questions-per-claim
                         answered_at                                                                metric

 AuditEvent              id, actor, action, target, before, after, at                               Append-only

               CONTRACTS

## PRD §15 — APIs and claim lifecycle

CLAIM LIFECYCLE

              user answers

     Draft              Needs info             Ready               Submitted          In review           Approved               Paid

                                  returned by approver with a comment
                                                                                                            Rejected

                                      Figure 8. Claim states. Only "Ready" claims can be submitted.

 Method & path                                 Purpose

 POST /v1/documents                            Register a document (hash, metadata, on-device extraction JSON). Image upload
                                               deferred until submit.

 POST /v1/documents/{id}/extract               Server-side extraction for Tier C devices (redacted text) or re-extraction.

 GET /v1/claims/draft                          Current draft claims with completeness state and open questions.

 POST /v1/agent/messages                       Send a user message or answer; returns agent reply, updated claim and next
                                               questions.

 POST /v1/claims/{id}/validate                 Run policy, duplicate and trust checks; returns flags with evidence.

 POST /v1/claims/{id}/submit                   Upload originals, freeze the claim, forward to mock finance.

 GET /v1/claims/{id}                           Full claim with lines, flags, audit trail and status.

 POST /v1/approvals/{id}                       Approver action: approve, return (with comment) or reject.

 GET /v1/entitlements                          Employee's balances by category with paid, pending, reserved and available
                                               amounts.

 GET /mock-erp/employees/{id}/entitle          Mock ERP source of per-employee limits, periods and paid amounts.
 ments

 POST /mock-erp/reimbursements                 Mock finance intake; returns reference, updates paid amounts and drives status
                                               webhooks.

Agent tools
The agent never computes money or policy itself. It calls deterministic tools and narrates the results:
group_expenses, check_policy, find_duplicates, get_trust_report, get_entitlements, ask_user, update_line,
build_claim and submit_claim. Tool calls and results are logged for audit and evaluation.

                 QUALITY BAR

## PRD §16 — Non-functional requirements

 Area                    Requirement

 Performance             On-device extraction p50 < 3 s, p95 < 6 s per receipt on a mid-range phone; batch of 10 < 30 s; UI stays
                         at 60 fps during processing.

 Offline                 Capture, extraction, policy pre-check and drafting work fully offline; sync when online via WorkManager.

 Privacy                 Raw images stay on device until submit. Card numbers and phone numbers are masked before any
                         upload. Data minimisation in line with India's DPDP Act, 2023.

 Security                Encrypted local storage (Android Keystore-backed keys), TLS 1.2+, short-lived JWTs, signed upload URLs,
                         role-based access for approvers.

 Reliability             Idempotent uploads keyed by document hash; retries with backoff; no claim lost on app kill.

 Explainability          Every auto-filled value links to its source region; every flag lists the signals and rule behind it.

 Auditability            Append-only audit log of extraction, edits, answers, overrides and approvals with policy version.

 Accessibility           TalkBack labels, dynamic type, minimum 48 dp targets, colour-independent status (icons and text, not
                         colour alone).

 Footprint               App < 40 MB excluding optional model; model downloaded on Wi-Fi with user consent.

               HACKATHON EXECUTION

## PRD §17 — Build plan and demo

 Phase               Scope                                                            Exit criteria

 0. Foundations      Repo, CI, docker-compose backend, synthetic data                 300 labelled docs; CI runs eval script
                     generator, golden and tampered sets

 1. Read             Capture, quality gate, OCR, on-device extraction with            ≥ 90% key-field accuracy on golden set
                     schema, device tiering

 2. Check            Validators, policy engine, entitlement service with mock ERP     Planted duplicates, breaches and
                     limits, duplicate service, trust score v1                        exhausted limits flagged

 3. Converse         Agent orchestrator with tools, grouping, question policy, chat   10-receipt scenario reaches Ready with ≤
                     UI                                                               2 questions

 4. Submit           Mock finance API, status updates, approver console               Submit, return and approve paths work
                                                                                      end to end

 5. Polish           Forensics v2, metrics dashboard, demo script, README and         Demo under 3 minutes, metrics slide
                     architecture notes                                               from real eval run

A day-by-day breakdown of these phases is in Section 28.

Demo storyline (3 to 4 minutes)
1. Priya drops 12 files from a Pune trip, including a crumpled meal bill, two cab PDFs and a broadband bill.
   Airplane mode is on to show on-device reading.
2. Within seconds, cards fill in. Kharcha groups six items into "Pune client visit" and keeps broadband as a
   separate claim, showing ₹2,001 of her ₹15,000 broadband limit left after it.
3. Two things need her: the hotel is over the city cap, and a cab receipt was already claimed last month. She
   answers the hotel question with one tap and removes the duplicate.
4. A hotel PDF that was edited in a PDF tool is flagged amber with the reason shown. She adds a note.
5. Switch to Arjun: his broadband limit is already used up, so Kharcha says so the moment the bill is read and
   offers to keep it for records instead.
6. She taps Submit. The mock finance system returns a reference; Meera approves from the console; the
   status updates to Approved in Priya's thread.
7. Close with the metrics slide: time to ready, questions per claim and accuracy from the evaluation run.

Repository layout

   kharcha/
     android/              Compose app, ML Kit + LiteRT-LM integration, benchmark module
     backend/              API, agent orchestrator, policy engine, claim service
     forensics/            Python trust service (ELA, pHash, PDF metadata)
     mock-erp/             Mock finance API with simulated approvals
     console/              Approver web console
     data/                 Synthetic generator, golden + tampered sets, labels
     eval/                 Evaluation scripts, results history
     docs/                 PRD, architecture, demo script

             WHAT COULD GO WRONG

## PRD §18 — Risks and mitigations

 Risk                            Impact                  Mitigation

 On-device LLM unavailable on    Core feature does not   Three-tier fallback; test on target device early; keep cloud path
 demo device                     run                     ready

 Model invents a field value     Wrong amounts           Deterministic validators; values must appear in OCR text; low
                                 reimbursed              confidence becomes a question

 False fraud flags               Employee trust          Tune on tampered set; amber not red by default; explainable
                                 damaged                 reasons; no auto-reject

 Thermal throttling on batches   Slow, hot phone         Thermal checks per document; pause and resume; defer to
                                                         charging

 Handwritten or faded bills      Low extraction          Retake prompts; crop-and-confirm questions; manual entry as
                                 accuracy                last resort

 Privacy or data leakage         Compliance breach       Synthetic data only; on-device by default; PII masking; no real
                                                         company data in personal accounts

 Free-tier limits change         Demo breaks or slows    NVIDIA fallback model; no-LLM degraded mode; dev in stub
 (Oracle, NVIDIA)                                        mode; check limits the week before the demo

 Stale or wrong ERP balances     Over- or                Server re-check at submit; show "as of" time; ERP stays source of
                                 under-reimbursement     truth

 Scope creep in a time-boxed     Unfinished demo         P0 list is the demo; P1 and P2 only after Phase 4 passes
 build

             NEXT STEPS

## PRD §19 — Open questions and future scope

Open questions
• Which demo devices are available, and do any support ML Kit GenAI on-device features?
• Should the agent conversation run on device as well for Tier A, or always on the backend?
• What is the minimum evidence needed for an approver to override a red trust score?
• Should per-diem be modelled as an allowance (no receipts) or as capped actuals?

Future scope
• Corporate card feed matching and automatic receipt chasing for card transactions without a bill.
• Mileage claims from trip GPS traces with privacy controls.
• Real ERP connectors and payout integration once the prototype is validated.
• Org-level analytics: spend by category, policy breach hotspots, leakage recovered.
• Multi-currency travel and per-country tax rules.

  Data and compliance note for the build
  All development uses synthetic, anonymised or publicly available receipts. No real employee receipts,
  company policy documents or credentials are used in personal accounts or repositories. Public datasets are
  used only under their published licences, and the finance system is a mock built for this prototype.

       PART B

       Development guide
       Everything needed to build, deploy and run Kharcha: technology decisions,
       Android and backend class design, the database schema, step-by-step
       Oracle Cloud setup, Docker and model installation, provider keys, CI/CD, a
       day-by-day plan, and a task board that Claude Code can execute.

       20 Engineering setup                        21 Android app design

       22 Backend design                           23 Database design

       24 Oracle Cloud setup                       25 Installing the stack

       26 Model provider setup                     27 CI/CD and operations

       28 Day-by-day plan                          29 Building with Claude Code

       30 Two-workspace development                A Appendix: task board

             DECISIONS AND CONVENTIONS

## PRD §20 — Engineering setup and repository

Final technology decisions
 Area               Decision                                               Why

 Android            Kotlin, Jetpack Compose, Hilt, Room, WorkManager,      Standard modern stack; batch work survives
                    Retrofit + kotlinx.serialization, Coroutines/Flow      process death

 On-device AI       ML Kit Document Scanner, ML Kit Text Recognition v2,   Three device tiers (Section 10)
                    ML Kit GenAI Prompt API (Gemini Nano), LiteRT-LM

 Backend            Python 3.12 + FastAPI, SQLAlchemy 2, Alembic,          One language for API, forensics (OpenCV, pypdf,
 language           Pydantic v2                                            imagehash) and LiteLLM; small memory footprint
                                                                           next to Claude Code on one VM

 Jobs               Redis 7 + RQ workers                                   Simple queue; easy to inspect

 Data               PostgreSQL 16, MinIO (S3 API)                          Relational claims data; originals in object storage

 LLM                NVIDIA hosted models (build.nvidia.com) only, via a    Free for prototyping; no model on the VM (Section
                    LiteLLM gateway with task aliases and NVIDIA           13)
                    fallback models

 Hosting            One Oracle VM (kh-core) for development and            Fits in 12 GB without a local model (Sections 24 to
                    hosting; Docker Compose stack built on the VM          25)

 Edge               Caddy 2 with automatic HTTPS on kh-core                TLS with two lines of config

 Console            React + Vite, built to static files served by Caddy    No server process needed

 CI/CD              GitHub Actions for tests; deploy is make deploy on     Simple and visible; no image registry needed
                    the VM

 Dev tool           Claude Code terminal CLI on both machines              Same workflow on laptop and VM (Section 30)

Repository layout

  kharcha/
    android/                         Android Studio project
      app/src/main/java/ai/kharcha/ packages listed in Section 21
      benchmark/                     macrobenchmark + extraction latency harness
    backend/
      app/
        api/          FastAPI routers (documents, claims, agent, entitlements, approvals, auth)
        core/         settings, security, logging, errors
        db/           SQLAlchemy base, session, Alembic migrations
        models/       ORM models (Section 23)
        schemas/      Pydantic request/response + receipt JSON schema
        services/     claim, policy, entitlement, duplicate, trust, extraction, erp client
        agent/        orchestrator, tool registry, question planner, prompts/
        llm/          gateway client, prompt templates, schema validation
        workers/      RQ jobs
      tests/          pytest (unit + API)
      Dockerfile
    forensics/        FastAPI internal service: ELA, pHash, PDF metadata (Dockerfile)
    mock-erp/         FastAPI mock finance: employees, entitlements, intake, status (Dockerfile)
    console/          React approver console (built to console/dist)
    contracts/        openapi.yaml, receipt.schema.json, test-vectors/, prompts/ (shared, Section 30)
    scripts/          laptop helpers: mock-api.sh, tunnel.sh, app-dev-connect.sh
    gateway/          litellm.config.yaml, Dockerfile
    deploy/
      server/docker-compose.yml   server/Caddyfile    server/initdb/
      scripts/ (bootstrap_server, deploy, backup, llm_smoke)
    data/             seed/, generator, golden + tampered sets, labels.csv
    eval/             run_eval.py, results/
    .github/workflows/ android.yml backend.yml eval.yml deploy.yml
    .env.example      hosted stack variables       .env.dev.example   dev runner variables

Conventions
• Trunk-based: short-lived branches, pull requests with CI green before merge, conventional commit
  messages.
• Secrets never committed. .env.example lists variables; real values live in each VM's .env (chmod 600) and in
  GitHub Actions secrets.
• Money is always an integer in paise; dates are ISO 8601; IDs are UUIDv7 strings (time-ordered).
• Prompts and JSON schemas are versioned files; every extraction stores the prompt version it used.

Developer machine prerequisites
 Tool                                              Use

 Laptop: Android SDK (Studio or command-line       Android app; a physical test phone for ML Kit and on-device model tests
 tools), JDK 17, Claude Code CLI

 On kh-core: Docker, uv, tmux, Claude Code         Installed by deploy/scripts/bootstrap_server.sh

 Git, GitHub account, SSH key pair                 Code hosting and SSH access to Oracle VMs

 Node.js LTS                                       Build the approver console

 Oracle Cloud account (Always Free), NVIDIA        The one VM and the model provider (Sections 24 to 26)
 Developer key

             PACKAGES AND CLASSES

## PRD §21 — Android app design

The app follows a three-layer structure: ui (Compose screens and ViewModels), domain (use cases and pure
logic such as validators) and data (Room, network, files). AI components sit in their own ai package behind
interfaces so the device tier can be switched at runtime.

  ai.kharcha
    KharchaApp.kt                  @HiltAndroidApp
    MainActivity.kt                single activity, KharchaNavHost
    ui/
      chat/       ChatScreen, ChatViewModel, ChatUiState, ReceiptCard, QuestionChips
      review/     ReviewScreen, ReviewViewModel, TripGroupCard, FlagBanner, EntitlementStrip
      submit/     SubmitScreen, SubmitViewModel
      capture/    CaptureCoordinator (scanner, picker, share intent)
      theme/      KharchaTheme, tokens
    domain/
      model/      Receipt, ExtractedField<T>, ExpenseLine, ClaimDraft, Flag, Question, Entitlement
      usecase/    IngestDocumentsUseCase, ExtractReceiptUseCase, GroupExpensesUseCase,
                  PreviewPolicyUseCase, AnswerQuestionUseCase, SubmitClaimUseCase
      validate/ GstinValidator, TaxMathValidator, DateSanityValidator, AmountNormalizer
    ai/
      tier/       DeviceTierResolver, DeviceTier, ThermalGuard
      ocr/        OcrEngine (ML Kit), PdfTextExtractor, QualityGate
      extract/    ReceiptExtractor (interface), GeminiNanoExtractor, LiteRtLmExtractor,
                  ServerExtractor, ExtractionPromptBuilder, ReceiptJsonParser
      trust/      TrustSignalCollector, ExifInspector, PdfMetadataInspector, CaptureSourceDetector
    data/
      db/         KharchaDatabase, entities, DAOs, Converters
      net/        KharchaApi (Retrofit), AuthInterceptor, dto/
      repo/       DocumentRepository, ClaimRepository, EntitlementRepository, PolicyRepository
      files/      SecureFileStore (Keystore-backed AES-GCM)
      work/       ExtractionWorker, SyncWorker, EntitlementRefreshWorker
    di/           AppModule, AiModule, DataModule, NetworkModule

Key classes
 Class                              Responsibility

 CaptureCoordinator                 Launches the ML Kit Document Scanner, the multi-select picker and handles
                                    ACTION_SEND / SEND_MULTIPLE intents; returns content URIs.

 IngestDocumentsUseCase             Copies each file into SecureFileStore, computes SHA-256, renders PDF pages with
                                    PdfRenderer, creates DocumentEntity rows and enqueues ExtractionWorker.

 QualityGate                        Laplacian variance for blur, highlight ratio for glare, minimum short edge for resolution;
                                    returns Pass or Retake(reason).

 OcrEngine                          Wraps ML Kit TextRecognizer (Latin + Devanagari); returns text blocks with bounding
                                    boxes.

 DeviceTierResolver                 Checks GenAI feature status, total RAM (ActivityManager.MemoryInfo) and whether a
                                    LiteRT-LM model is downloaded; returns Tier A, B or C.

 ThermalGuard                       Listens to PowerManager thermal status; exposes canRunHeavyWork() used by
                                    ExtractionWorker before every document.

 ReceiptExtractor                   Interface: suspend fun extract(input: ExtractionInput): ExtractionResult. Implementations
                                    per tier; the worker picks one via the resolver.

 ExtractionPromptBuilder            Builds the prompt from OCR text, the receipt JSON schema and two short examples;
                                    versioned (prompt_version).

 ReceiptJsonParser                  Parses model output with kotlinx.serialization, validates required fields, and on failure
                                    retries once with the error message.

 GstinValidator /                   Deterministic checks: 15-character GSTIN pattern, state code and checksum; CGST +
 TaxMathValidator                   SGST or IGST matching rate and total.

 TrustSignalCollector               Runs ExifInspector, PdfMetadataInspector and CaptureSourceDetector and returns
                                    signals with weights for the trust score.

 PreviewPolicyUseCase               Evaluates cached policy rules and entitlement balances locally for instant feedback; the
                                    server result is authoritative.

 ExtractionWorker                   CoroutineWorker processing the queue one document at a time; respects
                                    ThermalGuard; writes results to Room; triggers SyncWorker.

 SyncWorker                         Pushes document metadata and extraction JSON to the API (idempotent by SHA-256);
                                    pulls questions, flags and claim state.

 ChatViewModel                      Single source of truth for the thread: merges Room flows of receipts, questions and claim
                                    state into ChatUiState.

Core interfaces (sketch)

   interface ReceiptExtractor {
       val tier: DeviceTier
       suspend fun isReady(): Boolean
       suspend fun extract(input: ExtractionInput): ExtractionResult
   }

   data class ExtractionInput(val docId: String, val ocrText: String, val pageBitmap: Bitmap?)
   sealed interface ExtractionResult {
       data class Success(val receipt: Receipt, val promptVersion: String) : ExtractionResult
       data class LowConfidence(val receipt: Receipt, val fields: List<String>) : ExtractionResult
       data class Failed(val reason: String) : ExtractionResult
   }

   class DeviceTierResolver @Inject constructor(
       private val genAi: GenAiStatusChecker, private val memory: MemoryInfoProvider,
       private val liteRt: LiteRtModelStore, private val thermal: ThermalGuard) {
       suspend fun resolve(): DeviceTier = when {
           !thermal.canRunHeavyWork()                 -> DeviceTier.C
           genAi.isAvailable()                        -> DeviceTier.A
           memory.totalGb() >= 6 && liteRt.isReady() -> DeviceTier.B
           else                                       -> DeviceTier.C
       }
   }

Room tables on the device
 Entity                                    Purpose

 DocumentEntity                            Local file reference, SHA-256, capture source, quality result, extraction status, trust
                                           score

 ExtractedFieldEntity                      Field name, value, confidence, bounding box, source (ocr, llm, user, inferred)

 ExpenseLineEntity / ClaimDraftEntity      Draft lines and grouping before sync; server IDs once synced

 QuestionEntity / FlagEntity               Open questions and flags pulled from the server, shown in the thread

 EntitlementEntity                         Cached balances with fetched_at for offline display

 OutboxEntity                              Pending API calls for offline-first sync (idempotency key, payload, attempts)

Gradle dependencies (use latest stable versions)
Compose BOM, Material 3, Navigation Compose, Hilt (+ hilt-work), Room (+ KSP), WorkManager, Retrofit, OkHttp, kotlinx.serialization, Coil,
androidx.exifinterface, ML Kit Text Recognition v2 (Latin and Devanagari), Play Services ML Kit Document Scanner, ML Kit GenAI Prompt
API, LiteRT-LM Android library, Tink (Keystore-backed AES-GCM). Check each library's release notes for the current artifact name and
version, since the GenAI and LiteRT-LM artifacts are still evolving.

              SERVICES AND CLASSES

## PRD §22 — Backend design

 Container      Host              Role                                                                      Memory cap

 caddy          kh-core           TLS on :443, reverse proxy to api, serves console static files            64 MB

 api            kh-core           FastAPI (uvicorn, 1 worker): auth, documents, claims, agent,              384 MB
                                  entitlements, approvals

 mock-erp       kh-core           FastAPI mock finance: employees, entitlements, reimbursement intake,      256 MB
                                  status timeline

 postgres       kh-core           Claims database                                                           1.5 GB

 redis          kh-core           RQ job queue, rate-limit counters, circuit-breaker state                  256 MB

 minio          kh-core           Original documents after submit                                           512 MB

 worker         kh-core           RQ workers: extraction, forensics calls, agent turns, ERP submission      768 MB

 forensics      kh-core           Internal FastAPI: ELA, perceptual hash, PDF metadata, recapture           768 MB
                                  heuristics

 litellm        kh-core           LLM gateway to NVIDIA on 127.0.0.1:4000 with task aliases and fallback    512 MB
                                  models

 dev runner     kh-core (host)    make dev-api / dev-worker on 127.0.0.1:8001 while developing              ~600 MB

Hosted stack about 5 GB, dev runner 0.6 GB and Claude Code about 2 GB, so roughly 8 GB of 12 GB in use, leaving headroom within
                                      12 GB. Adjust caps after measuring with docker stats.

Key classes
 Module       Class / function                     Responsibility

 core         Settings                             pydantic-settings; reads .env; one object injected everywhere

 api          documents, claims, agent,            Thin HTTP layer; validates with Pydantic; calls services; never touches
              entitlements, approvals routers      LLMs directly

 services     ClaimService                         Create and update drafts, totals, grouping results; applies
                                                   ClaimStateMachine transitions

 services     ClaimStateMachine                    Allowed transitions (Section 15); raises on illegal moves; writes
                                                   AuditEvent

 services     PolicyEngine                         Loads active policy version; evaluates JsonLogic rules per line; returns
                                                   Flag objects with rule_id and remedies

 services     EntitlementService                   Fetches from ErpClient, computes available = limit - paid - pending -
                                                   reserved; creates and releases reservations inside a transaction with
                                                   row locks

 services     DuplicateService                     Exact SHA-256 match, pHash Hamming distance ≤ 6, and fuzzy key
                                                   (vendor, date, amount ± 1%) across user and organisation

 services     TrustService                         Combines device signals with forensics results into a 0 to 100 score with
                                                   top reasons

 services     ExtractionService                    Tier C extraction via LLMGateway; schema validation; stores
                                                   ExtractedField rows

 services     ErpClient                            HTTP client for mock-erp; retries; maps ERP errors to domain errors

 agent        AgentOrchestrator                    Runs one agent turn: builds context, calls kh-agent with tools, executes
                                                   tool calls, returns reply and updated claim

 agent        ToolRegistry + tools                 group_expenses, check_policy, get_entitlements, find_duplicates,
                                                   get_trust_report, ask_user, update_line, build_claim, submit_claim

 agent        QuestionPlanner                      Deterministic ask() rule from Section 7; ranks and batches questions; the
                                                   LLM only words them

 llm          LLMGateway                           OpenAI client pointed at LiteLLM; task alias in, validated JSON out; writes
                                                   llm_calls rows

 workers      extract_document, run_forensics,     RQ jobs with timeouts and retry policies
              agent_turn, submit_to_erp,
              refresh_entitlements

Agent turn (sketch)

  class AgentOrchestrator:
      MAX_STEPS = 6

        async def run_turn(self, claim_id: str, user_msg: str | None) -> AgentReply:
            ctx = await self.context.build(claim_id)            # lines, flags, open questions, balances
            planned = self.planner.next_questions(ctx)           # deterministic, max 3
            messages = self.prompts.render("agent_v3", ctx=ctx, planned=planned, user=user_msg)
            for _ in range(self.MAX_STEPS):
                resp = await self.llm.chat("kh-agent", messages, tools=self.tools.schemas())
                if not resp.tool_calls:
                    return AgentReply(text=resp.text, claim=await self.claims.view(claim_id))
                for call in resp.tool_calls:
                    result = await self.tools.execute(call.name, call.args, claim_id=claim_id)
                    messages += [resp.as_message(), tool_result(call.id, result)]
            return AgentReply(text=self.prompts.fallback(planned), claim=await self.claims.view(claim_id))

Entitlement reservation (sketch)

  async def reserve(self, session, line: ExpenseLine) -> Reservation:
      ent = await session.scalar(
          select(Entitlement).where(Entitlement.employee_id == line.employee_id,
                                    Entitlement.category == line.category,
                                    Entitlement.period_start <= line.expense_date,
                                    Entitlement.period_end >= line.expense_date)
          .with_for_update())                                   # row lock prevents double use
      if ent is None:
          raise NotEntitled(line.category)
      available = ent.limit_paise - ent.paid_paise - await self.pending(session, ent) \
                  - await self.reserved(session, ent, exclude_line=line.id)
      covered = max(0, min(line.amount_paise, available))
      return Reservation(entitlement_id=ent.id, line_id=line.id, amount_paise=covered, status="held")

Mock ERP contract
 Endpoint                                 Behaviour

 GET /employees/{id}                      Synthetic employee with grade, cost centre, manager

 GET /employees/{id}/entitlements         Per-category limits, periods and paid amounts; values differ by grade and per
                                          employee seed file

 POST /reimbursements                     Validates claim schema, returns ERP reference, schedules status changes (in
                                          review, approved, paid) on a timer

 GET /reimbursements/{ref}                Current status; paid amounts update the employee's entitlement

 POST /admin/scenario                     Demo helper: set an employee's broadband as fully used, force a rejection, add
                                          latency

                POSTGRESQL SCHEMA

## PRD §23 — Database design

All tables use UUID primary keys and created_at / updated_at timestamps (omitted below for brevity). Money is
stored as BIGINT paise. Enumerations are PostgreSQL enum types so invalid states cannot be written. Migrations
are managed with Alembic.

 Table                   Relations                                          Main indexes

 employees               manager_id to employees                            email unique

 policies                referenced by flags.policy_version                 (version) unique, active partial index

 entitlements            employee_id                                        (employee_id, category, period_start) unique

 claims                  employee_id; approver_id to employees              (employee_id, status)

 documents               employee_id; claim_id nullable                     sha256 unique per employee; phash btree;
                                                                            fuzzy_key

 expense_lines           claim_id, document_id                              (claim_id), (category, expense_date)

 reservations            entitlement_id, line_id                            (entitlement_id, status)

 extracted_fields        document_id                                        (document_id, name)

 flags                   claim_id, line_id or document_id                   (claim_id, status)

 questions               claim_id, line_id nullable                         (claim_id) where answered_at is null

 Table                   Relations                                    Main indexes

 agent_messages          claim_id                                     (claim_id, created_at)

 llm_calls               claim_id, document_id nullable               (task, created_at), (provider, success)

 audit_events            actor_id, target                             (target_type, target_id, at)

  CREATE TYPE claim_status AS ENUM ('draft','needs_info','ready','submitted','in_review',
                                    'approved','rejected','returned','paid');
  CREATE TYPE expense_category AS ENUM ('flight','rail','cab','hotel','meal','fuel','toll',
                                        'telecom','broadband','other');
  CREATE TYPE flag_type AS ENUM ('policy','entitlement','duplicate','authenticity','missing');
  CREATE TYPE severity AS ENUM ('green','amber','red');
  CREATE TYPE period_kind AS ENUM ('month','quarter','fin_year','per_trip');

  CREATE TABLE employees (
    id uuid PRIMARY KEY, email text UNIQUE NOT NULL, name text NOT NULL,
    grade text NOT NULL, cost_centre text, home_city text,
    manager_id uuid REFERENCES employees(id), role text NOT NULL DEFAULT 'employee');

  CREATE TABLE policies (
    id uuid PRIMARY KEY, version int UNIQUE NOT NULL, rules jsonb NOT NULL,
    effective_from date NOT NULL, active boolean NOT NULL DEFAULT false);

  CREATE TABLE entitlements (
    id uuid PRIMARY KEY, employee_id uuid NOT NULL REFERENCES employees(id),
    category expense_category, overall boolean NOT NULL DEFAULT false,
    period period_kind NOT NULL, period_start date NOT NULL, period_end date NOT NULL,
    limit_paise bigint NOT NULL CHECK (limit_paise >= 0),
    paid_paise bigint NOT NULL DEFAULT 0, fetched_at timestamptz NOT NULL,
    UNIQUE (employee_id, category, period_start));

  CREATE TABLE claims (
    id uuid PRIMARY KEY, employee_id uuid NOT NULL REFERENCES employees(id),
    title text, trip_start date, trip_end date, city text,
    status claim_status NOT NULL DEFAULT 'draft',
    total_paise bigint NOT NULL DEFAULT 0, approver_id uuid REFERENCES employees(id),
    erp_ref text, submitted_at timestamptz, decided_at timestamptz);
  CREATE INDEX ON claims (employee_id, status);

  CREATE TABLE documents (
    id uuid PRIMARY KEY, employee_id uuid NOT NULL REFERENCES employees(id),
    claim_id uuid REFERENCES claims(id), sha256 char(64) NOT NULL, phash bigint,
    fuzzy_key text, mime text NOT NULL, pages int NOT NULL DEFAULT 1,
    capture_source text NOT NULL, storage_uri text, trust_score smallint,
    device_tier char(1), prompt_version text,
    UNIQUE (employee_id, sha256));
  CREATE INDEX ON documents (fuzzy_key);
  CREATE INDEX ON documents (phash);

  CREATE TABLE expense_lines (
    id uuid PRIMARY KEY, claim_id uuid NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    document_id uuid REFERENCES documents(id), category expense_category NOT NULL,
    expense_date date NOT NULL, vendor text, city text,
    amount_paise bigint NOT NULL, claimable_paise bigint NOT NULL,
    cgst_paise bigint, sgst_paise bigint, igst_paise bigint, gstin text,
    purpose text, attendees jsonb NOT NULL DEFAULT '[]', excluded_reason text);
  CREATE INDEX ON expense_lines (claim_id);

  CREATE TABLE reservations (
    id uuid PRIMARY KEY, entitlement_id uuid NOT NULL REFERENCES entitlements(id),
    line_id uuid NOT NULL REFERENCES expense_lines(id) ON DELETE CASCADE,
    amount_paise bigint NOT NULL,
    status text NOT NULL CHECK (status IN ('held','released','consumed')));
  CREATE INDEX ON reservations (entitlement_id, status);

  CREATE TABLE extracted_fields (
    id uuid PRIMARY KEY, document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    name text NOT NULL, value jsonb NOT NULL, confidence real NOT NULL,
    bbox int[4], source text NOT NULL CHECK (source IN ('ocr','llm','user','inferred')));

  CREATE TABLE flags (
    id uuid PRIMARY KEY, claim_id uuid NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    line_id uuid REFERENCES expense_lines(id), document_id uuid REFERENCES documents(id),
    type flag_type NOT NULL, severity severity NOT NULL, rule_id text,
    policy_version int, message text NOT NULL, evidence jsonb NOT NULL DEFAULT '{}',
    status text NOT NULL DEFAULT 'open', resolution_note text);

  CREATE TABLE questions (
    id uuid PRIMARY KEY, claim_id uuid NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    line_id uuid REFERENCES expense_lines(id), field text NOT NULL, prompt text NOT NULL,
    options jsonb NOT NULL DEFAULT '[]', answer jsonb,
    asked_at timestamptz NOT NULL DEFAULT now(), answered_at timestamptz);

  CREATE TABLE agent_messages (
    id uuid PRIMARY KEY, claim_id uuid NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    role text NOT NULL, content jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now());

  CREATE TABLE llm_calls (
    id uuid PRIMARY KEY, task text NOT NULL, provider text NOT NULL, model text NOT NULL,
    claim_id uuid, document_id uuid, latency_ms int, tokens_in int, tokens_out int,
    success boolean NOT NULL, failure text, created_at timestamptz NOT NULL DEFAULT now());

  CREATE TABLE audit_events (
    id uuid PRIMARY KEY, actor_id uuid, action text NOT NULL, target_type text NOT NULL,
    target_id uuid NOT NULL, before jsonb, after jsonb, at timestamptz NOT NULL DEFAULT now());

                   ONE VM FOR DEVELOPMENT AND HOSTING

## PRD §24 — Oracle Cloud setup

ONE ORACLE ALWAYS FREE VM: DEVELOPMENT + HOSTING

      Android app / browser                       Laptop (APP workspace)
        https://your-domain                            SSH 22 + tunnel :8001

   kh-core | VM.Standard.A1.Flex | arm64 | 2 OCPU | 12 GB | public: 80, 443 (Caddy), 22 (your IP only)

     Hosted stack (/opt/kharcha)                                                   Development (~/kharcha)
                                                                                                                                       NVIDIA API
     compose project kharcha, built on the VM                                      feature branches

       Caddy 2                              api                                     Claude Code
                                                                                                                                      build.nvidia.com
       TLS, :443 public                     FastAPI, internal :8000                 terminal, in tmux

       worker                               forensics                               dev api                                             free dev key
       RQ jobs                              127.0.0.1:8085                          127.0.0.1:8001

       mock-erp                             LiteLLM                                 dev worker                                    primary + fallback
       127.0.0.1:8090                       127.0.0.1:4000                          queues dev-*

                                                                                                                                      outbound HTTPS
       PostgreSQL 16                        Redis + MinIO                           tests
       kharcha, _dev, _test                 DB 0/1, two buckets                     kharcha_test

                                                                                                                                         GitHub
                                                                                                                                          repo, CI
                                                                                                                                        pull to both
                                                                                                                                         checkouts

Dev and hosted share Postgres, Redis, MinIO and the gateway on 127.0.0.1 but use separate databases, Redis DBs, buckets and queues.

              Figure 9. kh-core runs the hosted stack and the development environment side by side; only Caddy is public.

   Check the free allowance first
   Oracle reduced the Always Free Ampere A1 allowance to 2 OCPUs and 12 GB in total during 2026. Size kh-core to
   exactly 2 OCPU / 12 GB and confirm the current limits on Oracle's Always Free resources page. The two micro
   VMs in the free tier are not needed for this design.

Step 1. Network
In the OCI Console open Networking > Virtual Cloud Networks > Start VCN Wizard and choose Create VCN with
Internet Connectivity (CIDR 10.0.0.0/16). Place kh-core in the public subnet.

Step 2. Security list ingress rules
 Source                                 Protocol / port                        Purpose

 Your home IP /32                       TCP 22                                 SSH, Claude Code sessions and the dev tunnel

 0.0.0.0/0                              TCP 80, 443                            Caddy certificate challenge and HTTPS for the app and
                                                                               console

                 Nothing else is opened. Postgres, Redis, MinIO, the gateway, mock ERP and the dev API listen on 127.0.0.1 only.

Step 3. Create the instance
 Name          Shape                            Image                            Boot           Notes
                                                                                 volume

 kh-core       VM.Standard.A1.Flex, 2 OCPU,     Canonical Ubuntu 24.04           ~100 GB        Public IP; paste your SSH key. If "out
               12 GB                            (aarch64)                                       of capacity", retry later or another
                                                                                                availability domain

Oracle may reclaim Always Free instances it considers idle; check the idle criteria in Oracle's Always Free documentation. A running
stack and daily development normally keep kh-core active.

Step 4. Bootstrap the VM
One script installs base tools, swap, Docker with log rotation, the host firewall rules for 80 and 443 (Oracle's
Ubuntu images reject other inbound traffic by default), tmux, uv and the Claude Code CLI, and creates the
release folder.

   # from the laptop
   scp deploy/scripts/bootstrap_server.sh ubuntu@<kh-core-public-ip>:~
   ssh ubuntu@<kh-core-public-ip> 'bash ~/bootstrap_server.sh'
   ssh ubuntu@<kh-core-public-ip>          # new login picks up the docker group
   claude --version

   #!/usr/bin/env bash
   # One-time setup of the single Oracle VM kh-core (Ubuntu 24.04 arm64). PRD §24.
   # Installs: base tools, 4G swap, Docker + compose, host firewall for 80/443, tmux, uv, Claude Code.
   set -euo pipefail

   sudo apt update && sudo apt -y upgrade
   sudo timedatectl set-timezone Asia/Kolkata
   sudo apt -y install git curl jq unzip htop tmux build-essential netfilter-persistent

   # swap (safety net; the stacks fit in RAM)
   if ! swapon --show | grep -q /swapfile; then
     sudo fallocate -l 4G /swapfile && sudo chmod 600 /swapfile
     sudo mkswap /swapfile && sudo swapon /swapfile
     echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
     echo 'vm.swappiness=10' | sudo tee /etc/sysctl.d/99-swap.conf && sudo sysctl --system
   fi

   # Docker Engine + compose plugin, with log rotation
   curl -fsSL https://get.docker.com | sudo sh
   sudo usermod -aG docker "$USER"
   echo '{"log-driver":"json-file","log-opts":{"max-size":"10m","max-file":"3"}}' \
     | sudo tee /etc/docker/daemon.json && sudo systemctl restart docker

   # host firewall: Oracle Ubuntu images reject inbound traffic by default; open web ports only
   sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
   sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
   sudo netfilter-persistent save

   # Python toolchain and Claude Code (terminal CLI, native installer)
   curl -LsSf https://astral.sh/uv/install.sh | sh
   curl -fsSL https://claude.ai/install.sh | bash

   # release checkout location for the hosted stack
   sudo mkdir -p /opt/kharcha && sudo chown "$USER":"$USER" /opt/kharcha

   echo "Done. Log out and back in (docker group), then run: claude --version"

   Docker and firewalls
   Ports published by Docker bypass the host INPUT chain, so the compose file publishes every internal service on
   127.0.0.1 only. Caddy is the single exception on 80 and 443. The OCI security list remains the outer wall.

Step 5. Domain and HTTPS
Create a free subdomain at a dynamic-DNS provider such as DuckDNS and point it to kh-core's public IP.
Caddy obtains and renews the certificate automatically once 80 and 443 are open.

                 TWO CHECKOUTS, ONE VM

## PRD §25 — Installing the stack

kh-core holds two copies of the repository. The dev checkout ~/kharcha is where Claude Code works on feature
branches. The release checkout /opt/kharcha holds only main or a tag and builds the hosted stack. Keeping
them apart means an unfinished change can never reach the demo, and Claude Code is told never to touch
/opt/kharcha.

                   Dev (Claude Code)                                Hosted (demo)

 Checkout          ~/kharcha, feature branches                      /opt/kharcha, main or a tag

 Runs as           make dev-api, make dev-worker (host processes)   Docker Compose project kharcha

 API               127.0.0.1:8001, reached through the SSH tunnel   Caddy at https://your-domain

 Data              kharcha_dev database, Redis DB 1, bucket         kharcha database, Redis DB 0, bucket originals
                   originals-dev, queues dev-*

 Env file          ~/kharcha/.env.dev (LLM_MODE=stub by default)    /opt/kharcha/.env (LLM_MODE=live)

 Who starts it     Claude Code or you                               You only: make deploy

Step 1. Checkouts and environment files

  ssh-keygen -t ed25519 -C kh-core && cat ~/.ssh/id_ed25519.pub    # add to GitHub
  git clone git@github.com:<you>/kharcha.git ~/kharcha             # dev checkout
  cd ~/kharcha && cp .env.dev.example .env.dev && chmod 600 .env.dev
  cp docs/workspaces/CLAUDE.local.BACKEND.md CLAUDE.local.md
  git clone git@github.com:<you>/kharcha.git /opt/kharcha          # release checkout
  cp /opt/kharcha/.env.example /opt/kharcha/.env && chmod 600 /opt/kharcha/.env
  nano /opt/kharcha/.env          # DOMAIN, passwords, NVIDIA_API_KEY (Section 26)

Step 2. Hosted stack definition
All images build on the VM (arm64). Official images (Caddy, Postgres, Redis, MinIO) are multi-arch; Kharcha's
own Dockerfiles start from python:3.12-slim.

  # Kharcha hosted stack on the single Oracle VM (kh-core, arm64).
  # Run from the RELEASE checkout /opt/kharcha via deploy/scripts/deploy.sh (project name: kharcha).
  # Only Caddy is public (80/443). Everything else binds to 127.0.0.1 so the dev runner and
  # the SSH tunnel can reach it, but the internet cannot.
  name: kharcha
  services:
    caddy:
      image: caddy:2
      ports: [ "80:80", "443:443" ]
      volumes:
         - ./Caddyfile:/etc/caddy/Caddyfile:ro
         - ../../console/dist:/srv/console:ro
         - caddy:/data
      environment:
         DOMAIN: ${DOMAIN}
      depends_on: [ api ]
      mem_limit: 64m
      restart: unless-stopped
    api:
      build: ../../backend
      command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
      env_file: ../../.env
      volumes: [ "../../data/seed:/data/seed:ro" ]
      depends_on:
         postgres: { condition: service_healthy }
         redis: { condition: service_started }
      mem_limit: 384m
      restart: unless-stopped
    worker:
      build: ../../backend
      command: rq worker --url redis://redis:6379/0 extract forensics agent erp
      env_file: ../../.env
      depends_on: [ postgres, redis ]
      mem_limit: 768m
      restart: unless-stopped
    forensics:
      build: ../../forensics
      ports: [ "127.0.0.1:8085:8085" ]
      mem_limit: 768m
      restart: unless-stopped
    mock-erp:
      build: ../../mock-erp
      ports: [ "127.0.0.1:8090:8090" ]
      volumes: [ "../../data/seed:/data/seed:ro" ]
      mem_limit: 256m
      restart: unless-stopped
    litellm:
      build: ../../gateway
      env_file: ../../.env
      ports: [ "127.0.0.1:4000:4000" ]
      mem_limit: 512m
      restart: unless-stopped
    postgres:
      image: postgres:16-alpine
      environment:
         POSTGRES_DB: kharcha
         POSTGRES_USER: kharcha
         POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}

      command: postgres -c shared_buffers=256MB -c work_mem=4MB -c max_connections=60
      volumes: [ "pg:/var/lib/postgresql/data", "./initdb:/docker-entrypoint-initdb.d:ro" ]
      ports: [ "127.0.0.1:5432:5432" ]
      healthcheck: { test: ["CMD", "pg_isready", "-U", "kharcha"], interval: 10s }
      mem_limit: 1536m
      restart: unless-stopped
    redis:
      image: redis:7-alpine
      command: redis-server --appendonly yes --maxmemory 200mb --maxmemory-policy noeviction
      volumes: [ "redis:/data" ]
      ports: [ "127.0.0.1:6379:6379" ]
      mem_limit: 256m
      restart: unless-stopped
    minio:
      image: minio/minio
      command: server /data --console-address ":9001"
      environment:
        MINIO_ROOT_USER: ${MINIO_ROOT_USER}
        MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
      volumes: [ "minio:/data" ]
      ports: [ "127.0.0.1:9000:9000", "127.0.0.1:9001:9001" ]
      mem_limit: 512m
      restart: unless-stopped
  volumes: { pg: {}, redis: {}, minio: {}, caddy: {} }

  # deploy/server/Caddyfile
  {$DOMAIN} {
    encode gzip
    handle /v1/* {
      reverse_proxy api:8000
    }
    handle {
      root * /srv/console
      try_files {path} /index.html
      file_server
    }
  }

  # deploy/server/initdb/10-dev-test.sql
  -- Runs once when the Postgres volume is first created.
  -- kharcha       : hosted stack (demo)
  -- kharcha_dev   : dev runner used while Claude Code develops (make dev-api)
  -- kharcha_test : pytest (wiped by tests)
  CREATE DATABASE kharcha_dev OWNER kharcha;
  CREATE DATABASE kharcha_test OWNER kharcha;

Step 3. Start shared services early
Before the backend exists, start the shared infrastructure from the release checkout so development can begin.
Add services as their tasks merge.

  cd ~/kharcha
  make infra-up                                              # postgres redis minio
  make infra-up SVC="postgres redis minio mock-erp forensics litellm"   # after T-06 merges
  make status                                                # containers + free memory

Step 4. Development loop on the VM

  tmux new -As kharcha
  # window 1: Claude Code           window 2: dev API              window 3: dev worker
  claude                             make migrate-dev && make dev-api    make dev-worker
  curl -s 127.0.0.1:8001/v1/healthz
  make backend-test                  # kharcha_test DB, LLM stub
  make llm-smoke                     # one tiny live call per alias (uses NVIDIA quota)

Step 5. Deploy the hosted stack (you only)

  #!/usr/bin/env bash
  # Deploy the hosted stack from the RELEASE checkout /opt/kharcha.
  # HUMAN-run only (never by Claude Code unless asked).
  # Usage: deploy/scripts/deploy.sh [git-ref]   (default: main; use a tag like v0.1.0 for the demo)
  set -euo pipefail
  REF=${1:-main}
  REPO_URL=$(git -C "$(dirname "$0")/../.." remote get-url origin)
  REL=/opt/kharcha

  if [ ! -d "$REL/.git" ]; then
    git clone "$REPO_URL" "$REL"
  fi
  cd "$REL"
  git fetch --tags origin
  git checkout --quiet "$REF"
  git pull --ff-only origin "$REF" 2>/dev/null || true   # no-op for tags
  test -f .env || { echo "Missing $REL/.env (copy .env.example and fill it)"; exit 1; }

  if [ -d console ] && [ -f console/package.json ]; then
    (cd console && npm ci && npm run build)
  fi

  DC=(docker compose --env-file .env -f deploy/server/docker-compose.yml)
  "${DC[@]}" build
  "${DC[@]}" up -d
  "${DC[@]}" exec -T api alembic upgrade head
  sleep 5
  curl -fsS "https://$(grep '^DOMAIN=' .env | cut -d= -f2)/v1/healthz" && echo " <- healthz OK ($REF)"

  # first time and every release
  cd ~/kharcha && git tag v0.1.0 && git push --tags
  make deploy REF=v0.1.0
  docker compose -p kharcha exec api python -m app.scripts.seed \
      --employees /data/seed/employees.json --policy /data/seed/policy_v1.json

Step 6. Backups

  #!/usr/bin/env bash
  # Nightly backup of the hosted database. Install with `crontab -e`:
  # 15 2 * * * /opt/kharcha/deploy/scripts/backup.sh >> /home/ubuntu/backups/backup.log 2>&1
  set -euo pipefail
  mkdir -p ~/backups
  docker exec kharcha-postgres-1 pg_dump -U kharcha kharcha \
    | gzip > ~/backups/"kharcha_$(date +%F).sql.gz"
  find ~/backups -name 'kharcha_*.sql.gz' -mtime +7 -delete

             KEY, MODELS, GATEWAY

## PRD §26 — NVIDIA model setup

NVIDIA build.nvidia.com is the only model provider. These steps create the key, confirm the models and wire
them into the gateway.

Step 1. Get the API key
1. Open build.nvidia.com and sign in or join the free NVIDIA Developer Program (email only, no card).
2. Go to Settings > API Keys (or Get API Key on any model page) and generate a key. It starts with nvapi-. Copy
  it once.
3. On kh-core, put it in /opt/kharcha/.env as NVIDIA_API_KEY. It is never committed and never sent to the
  phone.

Step 2. Confirm the models (task H-05)
 Model id                             Role                                 Check on its build.nvidia.com page

 nvidia/nemotron-nano-12b-v2-vl       Receipt images, primary              Free endpoint, image input format in the code
                                                                           sample

 nvidia/llama-3.1-nemotron-nano-vl    Receipt images, fallback             Free endpoint, image input format
 -8b-v1

 nvidia/nvidia-nemotron-nano-9b-      Text extraction primary, parsing     Free endpoint; reasoning toggle if the model
 v2                                   primary, agent fallback              card offers one (keep it off for extraction)

 mistralai/mistral-nemotron           Agent primary (tool calling), text   Free endpoint, tool-calling support
                                      and parse fallback

  export NVIDIA_API_KEY=nvapi-xxxxxxxx
  curl -s https://integrate.api.nvidia.com/v1/chat/completions \
    -H "Authorization: Bearer $NVIDIA_API_KEY" -H "Content-Type: application/json" \
    -d '{"model":"mistralai/mistral-nemotron",
         "messages":[{"role":"user","content":"Reply with the single word OK"}],
         "max_tokens":10}' | jq -r '.choices[0].message.content'

Step 3. Gateway configuration

  # Kharcha LLM gateway: NVIDIA hosted models only (build.nvidia.com, OpenAI-compatible).
  # Confirm each model id on its build.nvidia.com page before use (H-05). No local model.
  # Fallback = a second NVIDIA model.
  # If both fail, the backend switches to no-LLM degraded mode (SPEC §6).
  model_list:
    - model_name: kh-extract-image
      litellm_params:
        model: nvidia_nim/nvidia/nemotron-nano-12b-v2-vl
        api_key: os.environ/NVIDIA_API_KEY
    - model_name: kh-extract-image-fb
      litellm_params:
        model: nvidia_nim/nvidia/llama-3.1-nemotron-nano-vl-8b-v1
        api_key: os.environ/NVIDIA_API_KEY
    - model_name: kh-extract-text
      litellm_params:
        model: nvidia_nim/nvidia/nvidia-nemotron-nano-9b-v2
        api_key: os.environ/NVIDIA_API_KEY
    - model_name: kh-extract-text-fb
      litellm_params:
        model: nvidia_nim/mistralai/mistral-nemotron
        api_key: os.environ/NVIDIA_API_KEY
    - model_name: kh-agent
      litellm_params:
        model: nvidia_nim/mistralai/mistral-nemotron
        api_key: os.environ/NVIDIA_API_KEY
    - model_name: kh-agent-fb
      litellm_params:
        model: nvidia_nim/nvidia/nvidia-nemotron-nano-9b-v2
        api_key: os.environ/NVIDIA_API_KEY
    - model_name: kh-parse
      litellm_params:
        model: nvidia_nim/nvidia/nvidia-nemotron-nano-9b-v2
        api_key: os.environ/NVIDIA_API_KEY
    - model_name: kh-parse-fb
      litellm_params:
        model: nvidia_nim/mistralai/mistral-nemotron
        api_key: os.environ/NVIDIA_API_KEY

  router_settings:
    num_retries: 1
    timeout: 20
    allowed_fails: 3
    cooldown_time: 300
    fallbacks:
      - kh-extract-image: [kh-extract-image-fb]
      - kh-extract-text: [kh-extract-text-fb]
      - kh-agent: [kh-agent-fb]
      - kh-parse: [kh-parse-fb]

  general_settings:
    master_key: os.environ/LITELLM_MASTER_KEY

  # Not used in the prototype. Another provider can be added later by config only, e.g.:
  # - model_name: kh-agent-alt
  #    litellm_params: { model: <provider>/<model>, api_key: os.environ/<PROVIDER>_API_KEY }

            LiteLLM option names change between releases; check its proxy documentation for the version you install.

  # gateway/Dockerfile
  FROM python:3.12-slim
  RUN pip install --no-cache-dir "litellm[proxy]"
  COPY litellm.config.yaml /app/litellm.config.yaml
  EXPOSE 4000
  CMD ["litellm", "--config", "/app/litellm.config.yaml", "--host", "0.0.0.0", "--port", "4000"]

Step 4. Smoke test

  # make llm-smoke -> deploy/scripts/llm_smoke.sh
  #!/usr/bin/env bash
  # Calls each gateway alias once with a tiny prompt. Reads LITELLM_MASTER_KEY from .env.dev.
  set -euo pipefail
  cd "$(dirname "$0")/../.."
  KEY=$(grep '^LITELLM_MASTER_KEY=' .env.dev | cut -d= -f2)
  for alias in kh-extract-text kh-agent kh-parse kh-extract-text-fb kh-agent-fb; do
    printf '%-22s ' "$alias"
    body=$(jq -nc --arg m "$alias" \
       '{model:$m, max_tokens:8, messages:[{role:"user", content:"Reply with OK"}]}')
    curl -s -m 30 http://127.0.0.1:4000/v1/chat/completions \
       -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" -d "$body" \
       | jq -r '.choices[0].message.content // .error.message' | head -c 60
    echo
  done

Environment variables
 Variable                                     File             Example / note

 DOMAIN                                       .env             kharcha.duckdns.org (points to kh-core)

 POSTGRES_PASSWORD, DATABASE_URL              .env, .env.dev   hosted: @postgres:5432/kharcha; dev:
                                                               @127.0.0.1:5432/kharcha_dev

 TEST_DATABASE_URL                            .env.dev         @127.0.0.1:5432/kharcha_test

 REDIS_URL, QUEUE_PREFIX                      .env, .env.dev   hosted redis://redis:6379/0; dev redis://127.0.0.1:6379/1 with
                                                               prefix dev-

 MINIO_ROOT_USER/PASSWORD,                    .env, .env.dev   buckets originals and originals-dev
 S3_ENDPOINT, S3_BUCKET

 JWT_SECRET                                   .env, .env.dev   64 random bytes; mock SSO signs demo users

 ERP_BASE_URL, FORENSICS_URL                  .env, .env.dev   service names in .env; 127.0.0.1 ports in .env.dev

 LLM_MODE                                     .env, .env.dev   live for hosted; stub for dev unless a task needs live calls

 LITELLM_URL, LITELLM_MASTER_KEY              .env, .env.dev   http://litellm:4000 or http://127.0.0.1:4000; same key in both

 NVIDIA_API_KEY                               .env only        Read by the gateway container; the only provider key

               KEEPING IT RUNNING

## PRD §27 — CI/CD, testing and operations

 Workflow           Trigger              Steps

 android.yml        PR, push to main     Gradle cache, lint, unit tests, assembleDebug, upload APK artifact

 backend.yml        PR, push to main     ruff + mypy, pytest with Postgres and Redis service containers, Alembic migration
                                         check

 eval.yml           Manual               Run eval/run_eval.py in stub mode in CI; live NVIDIA runs happen on kh-core with
                                         make eval

 deploy             You, on kh-core      make deploy REF=v0.x.y builds from /opt/kharcha on the VM, runs migrations and
                                         checks healthz (no registry, no deploy workflow)

Testing approach
 Level                What                                                                  Tools

 Unit                 Validators, policy rules, entitlement maths, question planner,        JUnit + Turbine (Android), pytest
                      state machine                                                         (backend)

 Integration          API with real Postgres and Redis; mock ERP; gateway with a stub       pytest + testcontainers or CI services
                      provider

 AI evaluation        Field accuracy, category accuracy, tamper recall, questions per       eval/run_eval.py, llm_calls table
                      claim, latency per provider

 On device            Extraction latency and memory per tier; thermal behaviour on a        Macrobenchmark, Android Studio
                      20-receipt batch                                                      profiler

 End to end           Demo storyline scripted against staging                               Maestro or Compose UI tests

Runbook
 Symptom                         Likely cause                         Fix

 Site unreachable                Caddy down or ports blocked          make status; check iptables rules (80/443) and the security
                                                                      list

 Certificate errors              DNS not pointing to kh-core          Update the DuckDNS record; restart caddy

 Extraction stuck "on            Worker down or NVIDIA failing        docker logs kharcha-worker-1; check llm_calls failures;
 server"                                                              make llm-smoke

 Many 429 errors                 NVIDIA limits reached                Dev back to LLM_MODE=stub; fallback model; degraded
                                                                      mode keeps users moving

 kh-core out of memory           Caps too high or too many            make status; close idle sessions; lower container caps
                                 Claude Code sessions

 Instance stopped by             Over free limits or idle             Check the console and Always Free limits; resize to 2 OCPU /
 Oracle                          reclamation                          12 GB

 Demo broke after a              Change reached /opt/kharcha          make deploy REF= to roll back
 change

               FIFTEEN WORKING DAYS

## PRD §28 — Day-by-day development plan

Each row maps to task cards T-00 to T-32 (Appendix A, docs/TASKS.md); the Android column runs on the laptop
and the backend and AI columns on kh-core (Section 30). The plan assumes one developer working full days. If
the timeline is shorter, keep every P0 item and drop P1 and P2 items in the order listed in Section 6.

 Day      Android                      Backend and infrastructure       AI and evaluation             Done when

 1        Laptop setup; project        Oracle VM, bootstrap, Claude     Synthetic receipt             Mock API serves contract; ssh
          skeleton, Compose            Code, both checkouts,            generator v0                  kh-core works
          theme, navigation, Hilt      infra-up, contract freeze

 2        Capture: scanner,            Postgres schema + Alembic,       Generate 200 synthetic +      Mock ERP returns
          picker, share intent         seed data, mock ERP              tampered variants             entitlements
                                       endpoints

 3        Ingest, SecureFileStore,     documents API, idempotent        Label golden set (300         Upload round trip works
          Room schema                  upload, MinIO                    docs)

 Day       Android                    Backend and infrastructure      AI and evaluation          Done when

 4         QualityGate, OcrEngine,    NVIDIA key, model checks,       Receipt JSON schema +      OCR text visible on cards
           PdfTextExtractor           llm-smoke                       prompt v1

 5         DeviceTierResolver,        LiteLLM gateway with NVIDIA     eval/run_eval.py v1        First accuracy table in
           GeminiNanoExtractor /      primary + fallback models,                                 results/
           LiteRtLmExtractor          degraded mode

 6         Validators,                ExtractionService (Tier C),     Prompt v2 from error       ≥ 90% key-field accuracy
           TrustSignalCollector       llm_calls logging               analysis

 7         Chat thread UI with        PolicyEngine, policy v1 JSON    Category accuracy          Policy flags appear in app
           receipt cards and                                          check
           states

 8         Entitlement strip and      EntitlementService,             Planted over-limit         Exhausted broadband demo
           line states                reservations, ERP client        scenarios                  works

 9         Review screen, trip        DuplicateService, forensics     Tamper recall              Duplicates flagged with link
           grouping UI                service v1                      measurement

 10        Question chips, answer     QuestionPlanner,                Questions-per-claim        10-receipt scenario ≤ 2
           flow                       AgentOrchestrator, tools        metric                     questions

 11        Submit screen, status      ClaimStateMachine, submit to    Agent prompt tuning        Submit to approval end to
           updates                    mock ERP, webhooks                                         end

 12        Offline mode,              Approver console (React) on     Latency per tier on test   Return-and-resubmit works
           SyncWorker hardening       Caddy                           phone

 13        Polish, accessibility,     make deploy of v0.1.0,          Full eval run on the       Tagged release live on the
           empty and error states     backups, healthz                NVIDIA models              domain

 14        Bug bash on two            Load test 20-receipt batches;   Metrics slide from         No P0 bugs open
           devices                    tune memory caps                llm_calls and eval

 15        Record backup demo         Freeze; staging snapshot        Final numbers into PRD     Demo rehearsed under 4
           video                                                      Section 3                  minutes

      Definition of done for the prototype
      All P0 requirements pass their acceptance criteria; the evaluation table is generated from a real run; the app
      works in airplane mode up to submission; the demo runs on the Oracle deployment with at least one fallback
      provider configured; README explains setup in under 15 minutes for a new developer.

                AGENT-READY SPECIFICATION

## PRD §29 — Building with Claude Code

This PRD is written to be executed by an AI coding agent such as Claude Code as well as read by people. A PDF
is good for review but awkward as working context, so the same content ships as a companion kit of plain-text
files that sit in the repository root. Claude Code reads a project-level CLAUDE.md at the start of every session, can
pull other files in with @path imports, and loads CLAUDE.md files in subdirectories when it works there. The kit uses
all three.

Companion kit contents
 File                              Purpose for the agent

 CLAUDE.md, CLAUDE.local.md        Project summary, the two workspaces, fixed stack, commands, rules (money in paise, no
                                   secrets, no direct vendor calls, no remote actions), finishing checklist. Imports the three
                                   docs below.

 docs/SPEC.md                      Locked decisions and every number the code needs: API request/response shapes, error
                                   codes, state transitions, thresholds, algorithms, trust weights, entitlement maths. Wins over
                                   the PDF if they differ.

 docs/TASKS.md                     33 task cards (T-00 to T-32) plus 9 human tasks. Each card has dependencies, PRD/SPEC
                                   references, deliverables, acceptance criteria and exact verify commands.

 docs/schema.sql                   The database schema from Section 23, tested on PostgreSQL 16. Alembic migration 0001
                                   must match it.

 contracts/                        The shared surface between workspaces: openapi.yaml, receipt.schema.json, test vectors
                                   for both validators, the shared extraction prompt, VERSION and CHANGELOG.

 docs/workspaces/                  APP and BACKEND guides, setup steps for each machine, CLAUDE.local templates naming
                                   the workspace.

 scripts/                          Laptop helpers: Prism mock, SSH tunnel to kh-core, adb reverse for a USB phone.

 data/seed/*.json                  Four synthetic demo users with per-employee entitlements, and policy v1 as JsonLogic
                                   rules.

 deploy/, gateway/,                Single-server compose file, Caddyfile, database init, bootstrap, deploy, backup and
 .env.example, .env.dev.example,   smoke-test scripts, NVIDIA-only LiteLLM config. All YAML and scripts validated.
 Makefile

 backend/CLAUDE.md,                Area-specific conventions loaded only when the agent works in that folder.
 android/CLAUDE.md

 docs/PRD.pdf                      This document, for references such as "PRD §9".

Order of authority
When sources disagree the agent follows, in order: the user's instruction in the session, CLAUDE.local.md
(workspace), docs/SPEC.md, contracts/ and docs/schema.sql, docs/TASKS.md, then this PDF. Anything still
ambiguous is a question for the user, not a guess; CLAUDE.md tells the agent to stop and ask.

Working loop
1. Open a fresh session in the repository root for each task so context stays small.
2. Ask for one task: "Read CLAUDE.md. Implement T-13 from docs/TASKS.md only. Plan first, then build, then
  run its Verify commands and report."
3. Review the plan before letting it write code; check the files it intends to touch against the card's Deliver list.
4. The task is done only when every Verify command passes. The agent ticks the box in TASKS.md and
  summarises files changed and how they were checked.
5. Commit per task with a conventional message (for example feat(entitlements): T-13 reservations), push,
  and let CI run.
6. For HUMAN-VERIFY tasks, the agent ships code with fakes and tests; you confirm on a real phone or VM and
  note the result in the card.

What stays with you
 Area                                Why the agent does not do it                      Kit support

 Oracle Console, VCN, the VM         Needs your cloud login and choices about          bootstrap_server.sh; Section 24 steps
                                     cost

 NVIDIA API key                      Secrets must not pass through the agent           .env.example lists it; it lives only in
                                                                                       /opt/kharcha/.env

 DNS, GitHub repo and SSH key        Account-level access                              H-03 and H-04 checklists

 Physical phone checks               On-device GenAI, scanner and thermal              Fakes for unit tests; benchmark module;
                                     behaviour need hardware                           HUMAN-VERIFY steps

 Deploying the hosted stack          It is the live demo on the same VM                make deploy REF=tag from /opt/kharcha;
                                                                                       Claude Code never runs it

  Guardrails written into CLAUDE.md
  No secrets in code, logs or commits. No calls to model vendors except through the gateway. The LLM never
  decides money, limits or policy outcomes. No changes to /opt/kharcha and no deploys, ever, unless you ask.
  Changes stay inside the current task. Tests are written with the code, and LLM tests always run in stub mode
  with recorded fixtures.

Requirement traceability
 Requirements (Section 6 and 9)                                                 Tasks

 ING-1 capture and multi-file                                                   T-21

 ING-2, ING-3 quality gate, PDF text layer                                      T-22

 EXT-1, EXT-2 classify and extract                                              T-08, T-10, T-23

 EXT-3 split multi-receipt images (P1)                                          T-23

 EXT-4 Hindi text (P1)                                                          T-22

 EXT-5 normalisation                                                            T-08, T-24

 VER-1 trust score                                                              T-15, T-24

 VER-2 GSTIN and tax maths                                                      T-08, T-24

 VER-3 duplicates                                                               T-14

 POL-1, POL-2 policy rules and remedies                                         T-12, T-27

 POL-3 reimbursable preview (P1)                                                T-23, T-27

 ENT-1 to ENT-9 entitlements                                                    T-13, T-25, T-27

 AGT-1, AGT-2 grouping and completeness                                         T-16, T-26

 AGT-3 question policy                                                          T-17

 AGT-4 natural-language edits (P1)                                              T-18

 CLM-1, CLM-2 claim build and submission                                        T-16, T-19

 CLM-3 approver console (P1)                                                    T-28

 CLM-4 PDF export (P2)                                                          Backlog, after T-32

                      The day-by-day plan in Section 28 runs these tasks in the same order; Appendix A lists every card.

                     LAPTOP FOR THE APP, ORACLE FOR THE BACKEND

## PRD §30 — Two-workspace development

Development is split across two machines. The Android app and the approver console are built on your laptop;
the backend, the AI pipeline and the LLM gateway are built on the Oracle kh-core VM, which also hosts the
running backend. Claude Code is used as the terminal CLI on both machines. Both machines work on one
GitHub repository. Each machine knows its role from an untracked CLAUDE.local.md, and each task card names
the workspace it belongs to, so the two Claude Code sessions never edit the same folders.

TWO WORKSPACES, ONE REPOSITORY

   APP WORKSPACE | laptop                                                                                BACKEND WORKSPACE | kh-core

     Claude Code (terminal) + SDK                                                                          Claude Code (terminal) in tmux
     android/, console/
                                                                     GitHub repo                           backend/, gateway/, eval/, deploy/

                                                       push
                                                                     main (protected)          push

     Prism mock :4010                                                   app/T-xx-*                         Dev runner 127.0.0.1:8001
     serves contracts/openapi.yaml                                      be/T-xx-*                          kharcha_dev, queues dev-*
                                                       pull                                     pull
                                                                        contract/*

     Emulator / USB phone                                              CI path filters                     Hosted stack /opt/kharcha
     adb reverse :4010 :8001                                                                               Caddy :443, the live demo

     CLAUDE.local.md                                                                                       Owns contracts/
                                                                       contracts/
     "this is APP"                                                                                         VERSION + CHANGELOG
                                                                    only shared surface

                                                      SSH tunnel: localhost:8001, :8090 to kh-core

Only Caddy (443) is public on kh-core; the dev runner binds to 127.0.0.1:8001 and is reached only through SSH.

                       Figure 10. The repository is the hand-off point; contracts/ is the only folder both sides depend on.

Who owns what
 Workspace             Machine                                     Owns (may edit)                                     Reads only

 APP                   Laptop: Android SDK, JDK 17, Node.js,       android/, console/, laptop scripts                  contracts/, docs/,
                       Claude Code CLI                                                                                 data/demo/

 BACKEND               kh-core: VM.Standard.A1.Flex, arm64,        backend/, forensics/, mock-erp/,                    docs/
                       2 OCPU, 12 GB; Claude Code in               gateway/, eval/, data/, deploy/,
                       tmux; also hosts the backend                contracts/

 Shared                GitHub                                      main branch, CI, contracts/ releases                —

   Claude Code on kh-core
   Claude Code needs at least 4 GB of RAM and supports arm64, so it runs comfortably on kh-core next to the
   hosted stack. The bootstrap script installs it with the native installer; run it inside tmux so sessions survive SSH
   drops. On the laptop, Claude Code also runs in the terminal and builds the app with ./gradlew; Android Studio is
   optional, for the emulator and layout previews.

The contract is the boundary
Everything the two sides must agree on lives in contracts/: openapi.yaml (every endpoint, request and
response), receipt.schema.json, the test vectors both validators must pass, and the extraction prompt used on
the phone and on the server. The backend workspace owns it. The app workspace asks for changes in
docs/CONTRACT_REQUESTS.md. Each change goes on a contract/ branch with a version bump, merges first,
and then both sides build against it.

• Additive changes (new optional field) are MINOR versions; the app ignores unknown fields so it never breaks.
• Breaking changes are MAJOR versions and need both workspaces updated before release.
• Backend contract test compares FastAPI routes and models with openapi.yaml in CI and fails on any
  mismatch.
• Prism mock serves openapi.yaml on the laptop, so app work never waits for the backend.

Three environments
 Environment      API runs on                         App reaches it at                                 Use for

 mock             Prism on the laptop                 Emulator 10.0.2.2:4010; USB phone                 UI work from day one
                                                      localhost:4010 via adb reverse

 dev              Dev runner on kh-core,              Via SSH tunnel: 10.0.2.2:8001 or localhost:8001   Integration with the
                  127.0.0.1:8001                                                                        real backend

 demo             Hosted stack on kh-core             https://your-domain                               Demo, HUMAN-VERIFY,
                  (Sections 24 to 25)                                                                   judging

 Android build flavors mock, dev and demo set API_BASE_URL. Cleartext HTTP is allowed only to localhost and 10.0.2.2 in mock and
                                                            dev.

Setting up kh-core (backend workspace)

  # after bootstrap_server.sh (Section 24) and the checkouts (Section 25 step 1)
  claude                                   # first run: complete the login link in your laptop browser
  cd ~/kharcha
  git sparse-checkout set --no-cone '/*' '!/android/'   # optional: hide the app
  make infra-up && make migrate-dev
  tmux new -As kharcha                     # windows: claude | make dev-api | make dev-worker
  curl -s 127.0.0.1:8001/v1/healthz

Setting up the laptop (app workspace)

  git clone git@github.com:<you>/kharcha.git && cd kharcha
  # optional: hide backend folders
  git sparse-checkout set --no-cone '/*' '!/backend/' '!/forensics/' \
      '!/mock-erp/' '!/gateway/' '!/eval/'
  cp docs/workspaces/CLAUDE.local.APP.md CLAUDE.local.md
  ./scripts/mock-api.sh                 # mock flavor: http://localhost:4010/v1/healthz
  ./scripts/tunnel.sh kh-core           # dev flavor: forwards :8001 and :8090 from kh-core
  ./scripts/app-dev-connect.sh          # USB phone: adb reverse for :4010 and :8001
  claude                                # Claude Code in the terminal

Daily routine
 Step           Laptop (APP)                                             kh-core (BACKEND)

 Start          git pull --rebase; start mock or tunnel                  ssh kh-core; tmux attach; git pull --rebase; make
                                                                         dev-api, make dev-worker

 Work           One task per Claude Code session (Workspace: APP)        One task per Claude Code session (Workspace:
                                                                         BACKEND)

 Branch         app/T-xx-topic                                           be/T-xx-topic or contract/topic

 Finish         Verify commands, PR, CI green, merge                     Verify commands, PR, CI green, merge; contract first if
                                                                         changed

 Integrate      Switch to dev flavor after the matching backend          Keep the dev runner up while the app tests against it
                task merges

 Release        Test the demo flavor against https://your-domain         You run make deploy REF=tag

Memory on kh-core while developing
 Process                                                  Approx. RAM             Tip

 Hosted stack (Caddy, api, worker, forensics, mock ERP,   ~5 GB caps              Always on; it is the demo
 gateway, Postgres, Redis, MinIO)

 Dev runner (uvicorn --reload, rq worker)                 ~0.6 GB                 Stop when idle

 Claude Code with test runs                               ~1.5 to 2 GB            Close idle sessions

 OS and cache                                             ~1 to 2 GB              4 GB swap as safety net

  Development never touches the demo
  Dev and hosted share Postgres, Redis, MinIO and the gateway, but use separate databases, Redis DBs, buckets
  and queue names, and live in separate checkouts. Claude Code works only in ~/kharcha with .env.dev; the
  hosted stack changes only when you run make deploy. Both use the same NVIDIA key, so keep dev in stub
  mode unless a task needs live calls.

              DOCS/TASKS.MD SUMMARY

## PRD §A — Appendix: task board

Workspace: APP runs on the laptop, BACKEND on kh-core, BOTH needs both. Owner: CLAUDE means Claude Code completes and
verifies the task; HUMAN-VERIFY means it builds with fakes and you confirm on hardware. Full cards with deliverables and commands
are in docs/TASKS.md.

 ID        Task                                                    Workspace       Depends                 Owner

 T-00      Contract v1 freeze                                      BACKEND         —                       CLAUDE

 T-01      Repo scaffold and tooling                               BACKEND         —                       CLAUDE

 T-02      Backend skeleton                                        BACKEND         T-01                    CLAUDE

 T-03      Mock ERP service                                        BACKEND         T-01                    CLAUDE

 T-04      Database models and migration                           BACKEND         T-02                    CLAUDE

 T-05      Seed script and mock auth                               BACKEND         T-03, T-04              CLAUDE

 T-06      Server stack and dev runner                             BACKEND         T-02, T-03              CLAUDE

 T-07      Synthetic receipt generator                             BACKEND         T-01                    CLAUDE

 T-08      Receipt contract and validators (Python)                BACKEND         T-02                    CLAUDE

 T-09      LLM gateway client and stub mode                        BACKEND         T-04                    CLAUDE

 T-10      Documents API and Tier C extraction                     BACKEND         T-05, T-08, T-09        CLAUDE

 T-11      Evaluation harness                                      BACKEND         T-07, T-09              CLAUDE

 T-12      Policy engine                                           BACKEND         T-08                    CLAUDE

 T-13      Entitlements and reservations                           BACKEND         T-05, T-12              CLAUDE

 T-14      Duplicate detection                                     BACKEND         T-10                    CLAUDE

 T-15      Forensics service and trust score                       BACKEND         T-06, T-07              CLAUDE

 T-16      Claim state machine and claims API                      BACKEND         T-12, T-13, T-14        CLAUDE

 T-17      Question planner                                        BACKEND         T-16                    CLAUDE

 T-18      Agent orchestrator and tools                            BACKEND         T-09, T-17              CLAUDE

 T-19      Submit, ERP sync and approvals                          BACKEND         T-16, T-03              CLAUDE

 T-20      Android scaffold                                        APP             T-01                    CLAUDE

 T-21      Capture, ingest, secure storage                         APP             T-20                    HUMAN-VERIFY

 T-22      Quality gate and OCR                                    APP             T-21                    HUMAN-VERIFY

 T-23      Device tiers and extractors                             APP             T-22                    HUMAN-VERIFY

 T-24      Validators and trust signals (Kotlin)                   APP             T-20                    CLAUDE

 T-25      Network, sync and outbox                                APP             T-20, T-00              CLAUDE

 T-26      Chat thread UI                                          APP             T-23, T-25              HUMAN-VERIFY

 T-27      Review, entitlements and submit UI                      APP             T-26                    HUMAN-VERIFY

 ID       Task                                                   Workspace         Depends                   Owner

 T-28     Approver console                                       APP               T-00                      CLAUDE

 T-29     Deployment files                                       BACKEND           T-06                      CLAUDE

 T-30     CI/CD workflows                                        BACKEND           T-02, T-29                CLAUDE

 T-31     End-to-end demo script                                 BOTH              T-19, T-27, T-28          HUMAN-VERIFY

 T-32     Documentation and metrics                              BACKEND           T-11, T-31                CLAUDE

 Human task                                                                             Before

 H-01 Oracle VCN, the kh-core VM and bootstrap_server.sh                                T-00

 H-02 NVIDIA key into /opt/kharcha/.env                                                 make infra-up with litellm (T-06)

 H-03 DNS subdomain to kh-core                                                          First deploy

 H-04 GitHub repo, branch protection, kh-core SSH key                                   H-08

 H-05 Confirm NVIDIA model ids, run make llm-smoke                                      T-09 live checks

 H-06 Test phones: developer mode, GenAI availability, benchmark                        T-21 to T-27 verification

 H-07 First make deploy of a tag, seed, smoke test                                      Demo rehearsal

 H-08 Claude Code login, dev and release checkouts, env files, infra-up                 T-00

 H-09 Laptop tools, clone, CLAUDE.local (APP), SSH config, mock and tunnel check        T-20
