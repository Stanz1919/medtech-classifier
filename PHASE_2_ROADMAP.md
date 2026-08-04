# Phase 2 Roadmap: Gap Testing & Ambiguous Rule Clarification

## Rules with unit test coverage but NO ground-truth device cases

These 9 rules have per-rule branch tests but are not yet exercised end-to-end through the engine with a realistic device:

### Rule 3 (Non-invasive, modifies biological/chemical composition)
**Annex VIII 4.3** — covers devices that modify tissue/cells/blood composition or are used in vitro with human cells/embryos.
- **Base case → IIb:** Device modifies composition but NOT via filtration/centrifugation/gas exchange
- **Exception → IIa:** Device uses filtration, centrifugation, gas, or heat exchange for treatment
- **Exception → III:** Substance used in vitro in direct contact with human cells/tissues/organs/embryos

**Real-world examples needed:**
- [ ] **Topical wound spray that promotes collagen production** (modifies tissue composition, applied to skin) → should be IIb or IIa depending on mechanism
- [ ] **Hemodialysis cartridge** (filtration of blood) → IIa
- [ ] **In vitro tissue culture medium** (used with human cells) → III
- [ ] **Chemical peel solution** (modifies skin composition) → IIb

---

### Rule 10 (Active diagnostic/monitoring devices)
**Annex VIII 6.2** — active devices for diagnosis and monitoring, with nuanced precedence on energy absorption.
- **Base case → IIa:** Diagnostic device; supplies energy absorbed by body; or images radiopharmaceutical distribution; or allows direct diagnosis of vital processes
- **Exception → I:** Illuminates patient's body in visible spectrum only (de-escalates!)
- **Exception → IIb:** Direct diagnosis/monitoring of vital parameters with immediate danger potential (e.g., cardiac arrhythmia detection)
- **Exception → IIb:** Emits ionising radiation for diagnostic/interventional radiology

**Real-world examples needed:**
- [ ] **Pulse oximeter** (non-invasive, absorbs infrared energy, monitors vital O₂ saturation) → IIa
- [ ] **Surgical light used for illumination only** (visible spectrum, no other function) → I
- [ ] **Implantable glucose monitoring sensor** (vital parameter with immediate-danger risk) → IIb
- [ ] **CT scanner** (ionising radiation, diagnostic) → IIb

---

### Rule 12 (Active devices administering/removing substances)
**Annex VIII 6.4** — active devices that deliver or extract medicinal products, body liquids, or substances.
- **Base case → IIa:** Normal administration/removal
- **Exception → IIb:** Administration/removal is potentially hazardous (substance nature, body part, mode of application)

**Real-world examples needed:**
- [ ] **Insulin infusion pump** (administers medicinal product, routine hazard profile) → IIa
- [ ] **Chemotherapy infusion pump** (administers hazardous cytotoxic drugs) → IIb
- [ ] **Wound drainage vacuum-assisted closure device** (removes body fluids, normal hazard) → IIa

---

### Rule 13 (Residual catch-all for active devices)
**Annex VIII 6.5** — "all other active devices" not covered by Rules 9-12.
- Only output: **Class I**

**Real-world examples needed:**
- [ ] **Digital temperature display (non-recording, no storage/transmission)** → I
- [ ] **Electric heating pad** (active, therapeutic energy, but standard hazard) → I
- [ ] **Simple electronic timer for physical therapy** → I

---

### Rule 14 (Device incorporating ancillary medicinal substance)
**Annex VIII 7.1** — devices with an integral medicinal product where the medicinal action is *ancillary* to the device.
- Only output: **Class III**

**Real-world examples needed:**
- [ ] **Antibiotic-coated surgical implant** (implant is primary, antibiotic coating is ancillary) → III
- [ ] **Hormone-releasing intrauterine device (IUD)** (contraceptive device + hormonally-active substance) → III
- [ ] **Vaccine-delivery patch** (patch is device, vaccine is ancillary substance) → III

---

### Rule 16 (Disinfecting/cleaning/sterilising devices)
**Annex VIII 7.3** — devices for contact lens care, or for disinfecting/sterilising medical devices.
- **Rule 16a → IIb:** Device for disinfecting/cleaning/hydrating contact lenses
- **Rule 16b → IIa:** Device for disinfecting/sterilising other medical devices (default)
- **Rule 16b exception → IIb:** Disinfecting solutions or washer-disinfectors for invasive devices *as end point of processing*
- **Carve-out:** Does NOT apply to devices that clean by physical action only

**Real-world examples needed:**
- [ ] **Contact lens solution (multi-purpose saline + disinfectant)** → IIb
- [ ] **Hospital instrument ultrasonic washer** (cleans instruments, not end-point disinfection) → IIa
- [ ] **High-level disinfectant for endoscopes** (disinfects invasive devices at end of processing) → IIb
- [ ] **Surgical brush for mechanical cleaning only** (physical action only, no rule applies) → Carve-out

---

### Rule 18 (Devices using non-viable human/animal tissue)
**Annex VIII 7.5** — devices made from non-viable tissues/cells of human or animal origin.
- **Base case → III:** Human tissue or animal tissue used
- **Exception (carve-out, AMBIGUOUS):** Animal tissue, intact skin contact only → Class unclear (not III per rule, but rule doesn't say what class it is)

**Real-world examples needed:**
- [ ] **Allograft bone for orthopedic reconstruction** (human bone tissue) → III
- [ ] **Porcine valve for heart replacement** (animal tissue, not intact skin) → III
- [ ] **Collagen-derived wound dressing from bovine origin, skin contact only** (animal tissue, intact skin) → ? (carve-out ambiguity)
- [ ] **Decellularized dermis (human-derived) for burn wound coverage** (human tissue) → III

---

### Rule 20 (Inhaled medicinal product administration via body orifice)
**Annex VIII 7.7** — non-surgical body-orifice-invasive devices administering medicines by inhalation.
- **Base case → IIa:** Standard inhalation device
- **Exception → IIb:** Mode of action has essential impact on efficacy/safety of the drug, OR device treats life-threatening conditions

**Real-world examples needed:**
- [ ] **Metered-dose inhaler (MDI)** for routine asthma/COPD (standard hazard) → IIa
- [ ] **Pressurized inhaler for emergency epinephrine** (treats life-threatening anaphylaxis) → IIb
- [ ] **Dry powder inhaler (DPI) for insulin** (mode of action essential to drug efficacy) → IIb

---

### Rule 21 (Substances introduced via body orifice or applied to skin, absorbed/dispersed)
**Annex VIII 7.8** — substance devices applied to skin/orifices that are absorbed or dispersed in the body.
- **Sub-rule 21a → III:** Systemically absorbed to achieve intended purpose (e.g., nicotine patch)
- **Sub-rule 21b → III:** Achieves purpose in stomach/lower GI *and* is systemically absorbed
- **Sub-rule 21c → IIa:** Applied to skin or nasal/oral cavity to pharynx, achieves purpose locally (no systemic absorption)
- **Catch-all → IIb:** Everything else

**Real-world examples needed:**
- [ ] **Nicotine transdermal patch** (systemically absorbed for smoking cessation) → III
- [ ] **Oral rehydration salts** (electrolytes, absorbed in GI tract, systemic effect) → III
- [ ] **Topical antibiotic cream** (applied to skin, local action, not systemically absorbed) → IIa
- [ ] **Nasal saline spray** (applied to nasal cavity, local decongestant action) → IIa
- [ ] **Suppository for local pain relief** (inserted rectally, absorbed, non-systemic action) → IIb

---

## Ambiguous Rules: Clarification Needed

These 4 rules are flagged as involving genuine judgement calls. Clarification means: documenting the ambiguity, citing MDCG guidance where it exists, and proposing a policy decision for the extractor.

### Rule 4 (Devices contacting injured skin/mucous membrane) — AMBIGUOUS
**Annex VIII 4.4** — drafted as a parallel list of purposes, not a base rule with explicit "unless" exceptions.

**The ambiguity:**
- The rule has four bullets: mechanical barrier/compression/absorption (I), secondary-intent healing of breached dermis (IIb), manage micro-environment (IIa), and catch-all (IIa)
- A single dressing might plausibly fit *multiple* bullets (e.g., a hydrocolloid dressing both absorbs exudate AND manages micro-environment)
- The regulation does NOT say which bullet takes precedence; instead it says "the strictest... shall apply"
- **But does "strictest" mean highest class among matched bullets, or is there an implicit hierarchy in the bullet order?**

**Current implementation:** Uses Annex VIII 3.5 "highest wins" across all matched bullets.

**What notified bodies do:** MDCG 2016-5 (guidance on wound management devices) notes this ambiguity implicitly — they typically assess the device's *primary* intended purpose, not all secondary properties.

**Proposed clarification:**
- [ ] Document that Rule 4 requires a judgement call on "principal intended use"
- [ ] If multiple bullets match, require the extractor to flag which is *primary* (wound_contact_purpose field is already there)
- [ ] Add test case: a dressing claimed to both manage micro-environment AND form a mechanical barrier — assert that the highest class wins, but document the human review step needed

---

### Rule 8 (Implantable devices) — AMBIGUOUS: "Ancillary component" carve-out
**Annex VIII 5.4** — implantable devices and long-term surgical devices, with many exceptions.

**The ambiguity:**
- Joint replacements and spinal implants escalate to Class III *unless* they are "ancillary components such as screws, wedges, plates and instruments"
- **What counts as "ancillary"?** A screw is clearly ancillary; a cobalt-chrome femoral stem is the functional core; but what about a polyethylene liner that bears all the joint forces?
- Notified bodies routinely dispute this boundary in real submissions

**Current implementation:** Flags `is_ancillary_component=True` as ambiguous; implementation falls back to the base Class IIb if a device is marked both joint_replacement AND ancillary_component.

**Real-world examples of the dispute:**
- Hip implant stem: functional core → Class III (not ancillary)
- Hip implant screw: purely fixation → Class I if reusable/Class IIb if implantable (ancillary?)
- Knee implant meniscal bearing (plastic insert): load-bearing → arguably III, not ancillary
- Spinal cage with integral screws: is the screw ancillary or is it the entire system one functional unit?

**Proposed clarification:**
- [ ] Document that "ancillary component" is a fact-specific judgement notified bodies make on a case-by-case basis
- [ ] Add guidance: "When in doubt, assume the component is part of the *functional system*, not merely ancillary, and escalate to Class III"
- [ ] Add test cases:
  - [ ] Hip implant stem (core load-bearing part) → III
  - [ ] Spinal fixation screw (clearly ancillary) → IIb or I depending on reusability
  - [ ] Knee insert bearing (load-bearing, arguably III despite being removable)

---

### Rule 11 (Software) — AMBIGUOUS: Severity tiering
**Annex VIII 6.3** — software classified by the *severity of harm* its wrong output could cause.

**The ambiguity:**
- Software severity is **not mechanical**; it's a clinical/domain judgement
- Examples of disputed severity tiers:
  - Does a wrong cardiac rhythm diagnosis lead to "serious deterioration" (IIb) or "death risk" (III)?
  - Is a misread mammogram causing a missed cancer diagnosis "serious deterioration" or "irreversible deterioration" (III)?
  - If a dose-calculation software gives a 10% overdose, is that serious deterioration (IIb) or potential death (III)?

**Current implementation:** Maps SoftwareDecisionImpact enum (DEATH_OR_IRREVERSIBLE_DETERIORATION, SERIOUS_DETERIORATION_OR_SURGICAL_INTERVENTION, OTHER_IMPACT) to classes (III, IIb, IIa). Flags as ambiguous and notes MDCG 2019-11.

**MDCG guidance:** MDCG 2019-11 *Qualification and Classification of Software in Regulation (EU) 2017/745* is the definitive source, but even it notes that severity assessment requires clinical expertise and regulatory judgement, not mechanical rules.

**Proposed clarification:**
- [ ] Add a reference document explaining the MDCG 2019-11 framework
- [ ] Document the three severity levels with realistic examples from actual FDA/PMCF/literature:
  - [ ] **Immediate death risk (III):** e.g., automated insulin dosing that can deliver 10x overdose undetected
  - [ ] **Serious but not immediately fatal (IIb):** e.g., ECG interpretation that misses atrial fibrillation, leading to stroke (serious but preventable with human review)
  - [ ] **Other (IIa):** e.g., treatment planning software where 5-10% dose error is caught by clinician verification
- [ ] Add test cases from each tier
- [ ] Document that the extractor must assign severity conservatively (default to higher class on uncertainty)

---

### Rule 18 (Tissue devices) — AMBIGUOUS: Animal-origin/intact-skin carve-out
**Annex VIII 7.5** — non-viable tissue/cell devices classified as Class III, *unless* animal-origin tissue contacting intact skin only.

**The ambiguity:**
- The regulation exempts animal-tissue/intact-skin devices from Rule 18 **but does not state what class they should then be**
- A bovine collagen wound dressing: is it Class I (per Rule 1, if non-invasive)? IIa (per Rule 4, if it contacts injured skin)? Something else?
- The carve-out suggests regulatory confidence in animal-tissue safety, but leaves the class undetermined

**Current implementation:** Flags as ambiguous and does NOT apply Rule 18. Falls through to other rules (typically Rule 1, Rule 4, or Rule 3 if it modifies composition).

**Real-world practice:** Notified bodies typically classify these via other rules, but there's no consistent precedent. A bovine collagen dressing applied to intact skin might be Class I; applied to injury might be IIa (Rule 4) or III (Rule 18 for the tissue content + Rule 4 for the wound contact).

**Proposed clarification:**
- [ ] Document that the carve-out is a gap in the regulation itself
- [ ] Propose a policy: "Animal-origin tissue/cells contacting intact skin only: apply other rules (prioritize Rule 4 if wound contact applies, else Rule 1 for non-invasive); do not invoke Rule 18 escalation to III"
- [ ] Add test cases:
  - [ ] Bovine collagen sponge on intact skin (no wound) → Class I
  - [ ] Bovine collagen sponge on an open burn wound → Class IIa (per Rule 4) or IIb?
  - [ ] Porcine-derived decellularized dermis for skin graft → Class III (arguably, despite animal origin, because it's an implanted tissue construct, not mere contact)

---

## Summary of Work Items

### Ground-truth device cases to add (9 rules × ~3-4 examples each = ~30 new test cases)
- [ ] Rule 3: collagen spray, hemodialysis, in-vitro medium, chemical peel
- [ ] Rule 10: pulse oximeter, surgical light, glucose sensor, CT scanner
- [ ] Rule 12: insulin pump, chemo pump, wound drainage
- [ ] Rule 13: temperature display, heating pad, timer
- [ ] Rule 14: antibiotic implant, IUD, vaccine patch
- [ ] Rule 16: contact lens solution, ultrasonic washer, endoscope disinfectant, surgical brush
- [ ] Rule 18: allograft bone, porcine valve, bovine collagen dressing, human dermis
- [ ] Rule 20: routine MDI, epinephrine inhaler, insulin DPI
- [ ] Rule 21: nicotine patch, ORS salts, antibiotic cream, saline spray, suppository

### Documentation for ambiguous rules
- [ ] Rule 4: Document the judgement call on "principal intended purpose"; cite MDCG 2016-5
- [ ] Rule 8: Document "ancillary component" as fact-specific; propose conservative (escalate to III) guidance
- [ ] Rule 11: Create a severity framework doc with MDCG 2019-11 reference + realistic examples from each tier
- [ ] Rule 18: Document the regulatory gap; propose fallback to other rules; add policy guidance

### Implementation tasks
- [ ] Expand `tests/test_known_devices.py` with the 30 new cases
- [ ] Create `docs/CLARIFICATIONS.md` explaining each ambiguous rule and policy decisions
- [ ] Update README to reference the clarifications doc
- [ ] Re-run test suite; confirm 100% rule coverage still holds
- [ ] Commit as "Phase 1b: Gap testing and ambiguous rule clarification"
