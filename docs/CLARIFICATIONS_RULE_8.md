# Clarification: Rule 8 ("ancillary component" carve-out for joint/spinal implants)

## Status: partially resolved - real examples confirmed, but no blanket rule exists

Same verification discipline as Rule 4: nothing below is invented. All
quotes and examples are pulled from the actual MDCG 2021-24 Rev.1 PDF,
extracted with `pdfplumber`, pages 38-41. Full extracted text saved at
[`docs/legal_sources/mdcg_2021-24_rule_8_implants.txt`](legal_sources/mdcg_2021-24_rule_8_implants.txt).

**Unlike Rule 4, this ambiguity does not fully resolve.** MDCG gives real
named examples of the carve-out (which is genuinely useful), but also
explicitly states there is no blanket rule for it - each component still
requires its own intended-purpose classification. The `RuleOutcome.ambiguous`
flag stays on `Rule8` for the joint/spinal ancillary-component case, but
its note now cites real precedent instead of an abstract "notified bodies
dispute this" claim.

## The regulation (Annex VIII, 5.4, relevant excerpt)

> "...are total or partial joint replacements, in which case they are
> classified as class III, with the exception of ancillary components
> such as screws, wedges, plates and instruments; or - are spinal disc
> replacement implants or are implantable devices that come into contact
> with the spinal column, in which case they are classified as class III
> with the exception of components such as screws, wedges, plates and
> instruments."

## What official guidance says

**Source:** MDCG 2021-24 Rev.1, pages 38-41. Same legal-weight caveat as
the Rule 4 document: MDCG guidance is not binding law, but it is what
notified bodies use in practice.

### Real named examples of the "ancillary component" carve-out

The worked-examples table lists, under the joint-replacement Class III
row's *base* (IIb) examples rather than its Class III examples:

> Class IIb examples include: "**Pedicle screws**", "**Hooks that fix
> rods on the spinal column**"

And explicitly, **Note 7**:

> "Contact with the spinal column should be understood as intended
> contact with any of the bony structures forming the column (cervical,
> thoracic, lumbar, sacral and coccyx) including the spinous and
> transverse processes of the vertebrae. **Hooks that fix rods on the
> spinal column are considered similar to 'screws, wedges, plates and
> instruments' exemption in the last indent of Rule 8.**"

This is real, citable precedent for what counts as "ancillary": fixation
hardware (screws, hooks, wedges, plates, instruments) whose purpose is to
attach/anchor the implant system rather than replace/bear the joint or
disc itself.

### But there is explicitly no blanket rule - Note 1

> "Article 52(4) states: '[...] for class IIb implantable devices, except
> sutures, staples, dental fillings, dental braces, tooth crowns, screws,
> wedges, plates, wires, pins, clips and connectors, the assessment of
> the technical documentation as specified in Section 4 of Annex IX
> shall apply for every device.' **This does not imply classification of
> all sutures, staples, dental fillings, dental braces, tooth crowns,
> screws, wedges, plates, wires, pins, clips and connectors as class
> IIb. Such devices must be classified in their own right according to
> their intended purpose and the applicable rules.**"

This is the key finding: MDCG is explicit that "it's a screw, therefore
it's ancillary/IIb" is **not a valid shortcut**. A component's category
(screw, plate, wire) is not itself the classification test - its
*intended purpose* is. A screw that is itself load-bearing or functions
as the joint replacement (not merely fixation hardware) would not
qualify for the carve-out. MDCG does not give a bright-line test for
telling these apart beyond the named examples above - this is the part
that remains a genuine, unresolved judgement call.

### Bonus finding: the "placed in the teeth" exception is narrower than expected

While extracting this section we found a second, unrelated but important
nuance - **Note 4**:

> "Implants without bioactive coatings intended to secure teeth or
> prostheses to the maxillary or mandibular bones are in Class IIb
> following the general rule."

And the worked-examples table lists **"Dental implants and abutments"**
under the Class **IIb** row, not the Class IIa ("placed in the teeth")
row. Only things placed *within* tooth structure itself - "Bridges and
crowns," "Dental filling materials and pins," "Dental alloys, ceramics
and polymers" - get the IIa exception.

**This means the colloquial term "dental implant" is misleading for
classification purposes.** A titanium post anchored in the jawbone (what
most people mean by "dental implant") is Class IIb under Rule 8's base
rule, not Class IIa. The IIa exception is for things genuinely embedded
in a tooth (fillings, crowns, bridges).

This has been fixed in the codebase: `DeviceAttributes.placed_in_teeth`
now carries an explicit docstring warning about this (see
`rules_engine/models.py`), and `Rule8`'s class docstring cites Note 4
directly (see `rules_engine/eu_mdr/rules.py`). Two ground-truth test
cases were added to `tests/test_known_devices.py` to lock this in: a
jawbone-anchored implant post (→ IIb) and a dental filling (→ IIa).

### Other real worked examples relevant to Rule 8 (verbatim, pp. 38-41)

| Class | Named examples |
|---|---|
| **IIb** (base) | Artificial ligaments for reinforcement, dental implants and abutments, shunts, peripheral stents/valves, plates, intra-ocular lenses, internal closure devices, tissue augmentation implants (excl. breasts), peripheral vascular catheters/grafts/stents (long-term), penile implants, non-absorbable sutures, non-biodegradable bone cements, maxillo-facial implants, visco-elastic ophthalmic surgical devices, **pedicle screws**, **hooks that fix rods on the spinal column** |
| **IIa** (placed in the teeth) | Bridges and crowns, dental filling materials and pins, dental alloys/ceramics/polymers |
| **III** (heart/CNS contact) | Prosthetic heart valves, aneurysm clips, vascular prosthesis/stents, central vascular catheters (long-term), spinal stents, CNS electrodes, cardiovascular sutures, vena cava filters, septal occlusion devices, intra-aortic balloon pumps, external LVADs |
| **III** (biological effect / absorbed) | Long-term absorbable sutures, bioactive-coated adhesives/implants, biodegradable bone cements, elastoviscous joint fluids (e.g. non-animal hyaluronan) |
| **III** (administers medicinal products) | Rechargeable non-active drug delivery systems, peritoneal dialysis |
| **III** (active implantable/accessory) | Cochlear implants, cardiac pacemakers, ICDs, leads/electrodes/adaptors, implantable nerve/bladder/sphincter stimulators, and *accessories to active implantable devices even if the accessory itself is non-implantable or non-active* (Note 6) - torque wrenches, programmer cables, magnets, external transmitters, pacemaker leads |
| **III** (breast implants/surgical mesh) | Breast implants, breast tissue expanders, surgical meshes for hernia repair, tension-free vaginal tape |
| **III** (joint replacement, minus ancillary) | Hip, knee, shoulder, ankle replacements |
| **III** (spinal disc/column contact, minus ancillary) | Spinal disc replacement implants, devices placed in the disc space, interbody fusion devices |

Six of these (pedicle screw, spinal rod hook, dental implant post, dental
filling, knee replacement, interbody fusion device) have been added as
named ground-truth cases in `tests/test_known_devices.py`.

## What this means for Phase 2 (extraction)

Given MDCG's own position that there's no blanket rule, the extractor
cannot mechanically infer "ancillary" from a device-type keyword alone
("screw" ≠ automatically ancillary). Recommended approach:

1. **Match against the confirmed named list first**: pedicle screws,
   fixation hooks/wedges/plates/instruments described as attaching or
   anchoring an implant system → `is_ancillary_component = True`.
2. **Treat anything load-bearing or functionally replacing the joint/disc
   itself as NOT ancillary**, even if it has a name that sounds like
   fixation hardware (e.g. a polyethylene bearing insert is not
   "ancillary" merely because it's a separate component).
3. **On genuine uncertainty, default to `is_ancillary_component = False`**
   (i.e. classify conservatively as Class III) - this matches the
   project's general policy of not forcing a lower-confidence answer, and
   errs toward the class requiring more rigorous conformity assessment
   rather than less.
4. **Separately**: never infer `placed_in_teeth = True` from the word
   "implant" alone if the device is jawbone-anchored - only genuine
   intra-tooth restorations qualify.

## Summary

| Question | Answer |
|---|---|
| Are there real examples of "ancillary" components? | Yes - pedicle screws and spinal-rod-fixation hooks, confirmed in MDCG 2021-24 (Note 7). |
| Is there a bright-line test for "ancillary" in general? | No - MDCG's Note 1 explicitly rules this out; each component needs its own intended-purpose classification. |
| Does the engine's `ambiguous` flag stay on Rule 8? | Yes, but the note now cites real precedent instead of an abstract claim. |
| Was a separate, unrelated bug/gap found? | Yes - "placed in the teeth" was at risk of being misapplied to jawbone-anchored dental implants. Fixed via documentation + test cases; no logic change needed since the field was already meant to mean "within tooth structure," just undocumented. |
