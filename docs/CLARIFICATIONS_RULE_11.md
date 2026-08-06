# Clarification: Rule 11 (software severity tiering)

## Status: partially resolved - real examples confirmed; a genuine implementation gap was also found

Same verification discipline as Rules 4 and 8: everything below traces to
the actual MDCG 2021-24 Rev.1 PDF, extracted with `pdfplumber`, pages
46-47. Full extracted text saved at
[`docs/legal_sources/mdcg_2021-24_rule_11_software.txt`](legal_sources/mdcg_2021-24_rule_11_software.txt).

That document itself points to a dedicated guidance document, **MDCG
2019-11 "Qualification and classification of software"**, for further
detail (real footnote/URL in the source PDF: `https://ec.europa.eu/health/sites/health/files/md_sector/docs/md_mdcg_2019_11_guidance_qualification_classification_software_en.pdf`).
**That document has not itself been fetched and read** - only what MDCG
2021-24 quotes from it is relied on here. If Phase 2 needs deeper
software-classification guidance, MDCG 2019-11 should be fetched and
verified the same way before citing it further.

## The regulation (Annex VIII, 6.3)

> "Software intended to provide information which is used to take
> decisions with diagnosis or therapeutic purposes is classified as class
> IIa, except if such decisions have an impact that may cause: - death or
> an irreversible deterioration of a person's state of health, in which
> case it is in class III; or - a serious deterioration of a person's
> state of health or a surgical intervention, in which case it is
> classified as class IIb. Software intended to monitor physiological
> processes is classified as class IIa, except if it is intended for
> monitoring of vital physiological parameters, where the nature of
> variations of those parameters is such that it could result in
> immediate danger to the patient, in which case it is classified as
> class IIb. All other software is classified as class I."

## What official guidance says

### Severity is explicitly context-dependent (this refines, but does not remove, the ambiguity)

**Note 2** (MDCG 2021-24, p. 47):

> "For the classification of software, it is needed to consider the
> intended purpose, intended population (including e.g. diseases to be
> treated and/or diagnosed), context of use (e.g. intensive care,
> emergency care, home use) of the software and of the information
> provided by the software as well as of the possible decisions to be
> taken."

This is a real, useful clarification: **the same underlying algorithm can
land in different classes depending on clinical context**, not just what
it computes. MDCG's own worked examples make this concrete:

> "Devices intended to be used to obtain readings of vital physiological
> signals in routine check-ups **including monitoring at home**" → **IIa**
>
> "Medical devices including MDSW intended to be used for continuous
> surveillance of vital physiological processes in **anaesthesia,
> intensive care or emergency care**" → **IIb**

Same category of function (vital-sign monitoring), different class,
purely because of where/how it's used. This confirms the engine's design
choice to model `software_monitors_vital_parameters_with_immediate_danger_potential`
as an independent flag (representing clinical context) rather than trying
to infer danger potential from the parameter type alone.

### Real worked examples (verbatim, pp. 46-47)

| Class | Example |
|---|---|
| **IIa** (decision support) | "MDSW intended to rank therapeutic suggestions for a health care professional based on patient history, imaging test results, and patient characteristics, for example, MDSW that lists and ranks all available chemotherapy options for BRCA-positive individuals." Also: "Cognitive therapy MDSW where a specialist determines the necessary cognitive therapy based on the outcome provided by the MDSW." |
| **III** (decision support, death/irreversible) | "MDSW intended to perform diagnosis by means of image analysis for making treatment decisions in patients with acute stroke." |
| **IIb** (decision support, serious/surgical) | "A mobile app intended to analyse a user's heartbeat, detect abnormalities and inform a physician accordingly." Also: "MDSW intended for diagnosing depression based on a score resulting from inputted data on patient symptoms (e.g. anxiety, sleep patterns, stress etc.)." |
| **IIa** (monitoring, non-vital or routine) | "MDSW intended to monitor physiological processes that are not considered to be vital." Also: "Devices intended to be used to obtain readings of vital physiological signals in routine check-ups including monitoring at home." |
| **IIb** (monitoring, vital + danger context) | "Medical devices including MDSW intended to be used for continuous surveillance of vital physiological processes in anaesthesia, intensive care or emergency care." |
| **I** (all other software) | "MDSW app intended to support conception by calculating the user's fertility status based on a validated statistical algorithm. The user inputs health data including basal body temperature (BBT) and menstruation days to track and predict ovulation. The fertility status of the current day is reflected by one of three indicator lights: red (fertile), green (infertile) or yellow (learning phase/cycle fluctuation)." |

All six have been added as named ground-truth cases in
`tests/test_known_devices.py`, citing MDCG 2021-24 directly.

### A scoping note worth keeping for Phase 2

> "Software used in conjunction with medical device(s) which solely
> record, store or display information would generally **not be
> considered devices** (see guidance MDCG 2019-11, section 3.3 for
> further detail). For example, software analogous to diaries for
> recording insulin doses would not be considered devices, unless an
> analysis is performed on the data or the device in some way alters the
> patient's treatment, prescription, doses etc."

This matters for Phase 2: some "software" the extractor encounters won't
be a medical device *at all* (out of MDR scope entirely), rather than
being Class I under Rule 11's catch-all. A pure logging/diary app is
out-of-scope; the same app that *analyses* the logged data to suggest a
dose change becomes a device. The current engine has no explicit
"out of scope" outcome - everything either matches a rule or returns
`None`. This is worth a note for whoever builds the extractor, though not
an engine change: `None` (no rule matched) is arguably the right proxy
for "not a device" already, as long as the extractor doesn't force
`is_software=True` on things like pure diary apps.

## A genuine implementation gap this research surfaced (now fixed)

**Note 3** (MDCG 2021-24, p. 47), restating Annex VIII Chapter II, point
3.3:

> "Medical device software should be classified in the same way,
> regardless of the software's location or the type of interconnection
> between the software and a (hardware) device. **However, in line with
> implementing rule 3.3 Annex VIII to the MDR, software which drives a
> device or influences the use of a device shall fall within the same
> class as the device.**"

We already have the verbatim Annex VIII 3.3 text in
`docs/legal_sources/annex_viii_classification_rules.txt` from Phase 1:

> "Software, which drives a device or influences the use of a device,
> shall fall within the same class as the device. If the software is
> independent of any other device, it shall be classified in its own
> right."

**This was not implemented anywhere in the engine when first found.**
`Rule11` always evaluated a software device against the standalone
decision-support/monitoring criteria, regardless of whether that
software drives a physical device. Concretely: firmware controlling a
Class IIb infusion pump should inherit **IIb** via 3.3, not get
re-derived from Rule 11's own criteria (which might independently
compute something different, e.g. IIa if the firmware's own
decision-support role seems low-risk in isolation).

This was a real gap, not a hypothetical one - it was found by reading
the actual guidance, not invented. It was out of scope for "implement
Rules 1-22" (3.3 is a Chapter II implementing rule, not one of the 22
numbered rules), but it materially affects correctness for embedded/
driving software, so rather than leave it flagged indefinitely it was
implemented as a follow-up:

- Added `DeviceAttributes.drives_or_influences_device_class:
  Optional[DeviceClass]`. When set, `Rule11.evaluate()` short-circuits to
  that class directly - citing Annex VIII 3.3 (and MDCG 2021-24's Note 3
  confirming it) - instead of evaluating its own decision-support/
  monitoring criteria at all. Left `None` (the default), Rule 11 behaves
  exactly as before for standalone software.
- Added `tests/test_rules_individual.py::test_rule11_software_driving_a_device_inherits_its_class`:
  firmware with `software_decision_impact=OTHER_IMPACT` (which alone
  would compute IIa) and `drives_or_influences_device_class=DeviceClass.IIB`
  correctly returns IIb, not IIa - and asserts the outcome is not flagged
  ambiguous, since 3.3's inheritance is mechanical, unlike Rule 11's own
  severity tiering.
- Added a regression test
  (`test_rule11_standalone_software_unaffected_by_3_3_field_default`)
  confirming the new field doesn't change behaviour when left unset.
- Added a named ground-truth case to `tests/test_known_devices.py`
  ("Embedded firmware controlling a Class IIb infusion pump").

## Summary

| Question | Answer |
|---|---|
| Is severity tiering still a judgement call? | Yes - MDCG confirms it's genuinely context-dependent, not mechanical. Real examples now ground it. |
| Are there real worked examples now in the test suite? | Yes - six MDCG-sourced examples added to `tests/test_known_devices.py`. |
| Was MDCG 2019-11 (the deeper software guidance) verified? | No - only what MDCG 2021-24 quotes from it. Fetch and verify separately before citing it further. |
| Was a new gap found? | Yes - Annex VIII 3.3 ("software driving a device inherits its class") was not implemented when this rule was first researched. |
| Is it fixed now? | Yes - `Rule11` short-circuits via `drives_or_influences_device_class`; see `rules_engine/eu_mdr/rules.py` and the tests listed above. |
