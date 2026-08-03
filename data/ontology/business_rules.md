# AbbVie Pharma Intelligence Platform
# Business Rules & Relationship Definitions
# Version 2.1 | Data Architecture Team | Q3 2025
# ================================================================
# Upload this to @PHARMA_ONTOLOGY.GOVERNANCE.DOC_STAGE
# Simulates a PowerPoint deck with business rules and ontology logic.

---
## SLIDE 1: Title

**AbbVie Pharma Intelligence Platform**
**Business Rules & Relationship Definitions**
Version 2.1 | Data Architecture Team | Q3 2025

---
## SLIDE 2: Entity Classification Rules

### What is a "Pharma Entity"?
An abstract class representing anything in the AbbVie data ecosystem that can
participate in relationships. Subtypes:

| Abstract Class | Concrete Subclasses | Description |
|---|---|---|
| PharmaEntity | (all below) | Top-level abstract |
| TherapeuticProduct | Drug | Marketed or pipeline compounds |
| CareProvider | Prescriber, Facility | Entities delivering care |
| CareRecipient | Patient | Individuals receiving treatment |
| ClassificationScheme | TherapyArea, Diagnosis | Organizing taxonomies |
| ClinicalEvent | Prescription, AdverseEvent | Time-stamped occurrences |
| CareGuideline | TreatmentPathway | Evidence-based protocols |

**Rule: Abstract classes NEVER have direct instances.**
They exist only to enable polymorphic queries like "show me all PharmaEntities
related to immunology."

---
## SLIDE 3: Relationship Definitions

### Core Relationships

| Relationship | From | To | Cardinality | Business Meaning |
|---|---|---|---|---|
| IS_PRESCRIBED | Patient | Drug | N:N | Patient receives drug via Rx |
| PRESCRIBES | Prescriber | Drug | N:N | HCP writes Rx for drug |
| TREATS | Drug | TherapyArea | N:1 | Drug's primary indication |
| WORKS_AT | Prescriber | Facility | N:1 | HCP's primary site |
| SPECIALIZES_IN | Prescriber | TherapyArea | N:1 | HCP's clinical focus |
| EXPERIENCES | Patient | AdverseEvent | 1:N | Patient reports AE |
| CAUSED_BY | AdverseEvent | Drug | N:1 | AE attributed to drug |
| FOLLOWS_PATHWAY | Patient | TreatmentPathway | N:1 | Current line of therapy |
| PRECEDES | Drug | Drug | N:N | Treatment sequencing |
| PARENT_OF | TherapyArea | TherapyArea | 1:N | Hierarchy |

---
## SLIDE 4: Inference Rules

### Rule 1: Inverse Relationships (Bidirectional)
If we know A->B, we automatically infer B->A with the inverse predicate.

| Known Fact | Inferred Fact |
|---|---|
| Patient IS_PRESCRIBED Drug | Drug IS_PRESCRIBED_TO Patient |
| Prescriber PRESCRIBES Drug | Drug PRESCRIBED_BY Prescriber |
| TherapyArea PARENT_OF SubArea | SubArea CHILD_OF TherapyArea |
| Drug PRECEDES Drug2 | Drug2 FOLLOWS Drug |

**Implementation**: For every edge (A, rel, B), create (B, inverse(rel), A)

### Rule 2: Transitive Chain (Multi-hop Collapse)
Multi-step traversals materialized as direct edges for O(1) lookup.

| Chain | Inferred Direct Edge | Business Value |
|---|---|---|
| Patient->Rx->Drug | Patient->Drug | Which drugs is a patient on? |
| Patient->Rx->Prescriber->Facility | Patient->Facility | Where does patient receive care? |
| Patient->Rx->Drug->TherapyArea | Patient->TherapyArea | Patient's therapy area assignment |
| Drug->Pathway->PriorDrug | Drug->DrugLineage | Drug succession tracking |

**Implementation**: Walk paths in KG_EDGE, insert inferred edge with provenance

### Rule 3: 2-Stage Chain (Aggregated Inference)
Combine individual facts into aggregate-level insights.

| Individual Facts | Aggregated Inference |
|---|---|
| N patients on Drug X report AE type Y | Drug X has safety signal for Y |
| M prescribers at Facility F prescribe Drug X | Facility F is high-value for Drug X |
| K patients switch from Drug A to Drug B | Treatment migration trend A->B |

**Threshold**: Only materialize when count > configurable minimum (default: 5)

---
## SLIDE 5: Treatment Switching Business Logic

### When is a "Switch" detected?

A treatment switch is defined as:
1. Same patient
2. Same therapy area
3. Different drug (by mechanism of action)
4. New drug claim within 60 days of last claim for prior drug
5. No overlap (patient is not on combination therapy)

### Switch Reason Classification:
- **Inadequate Response**: Same diagnosis, escalating severity codes in 90 days prior
- **Adverse Event**: AE report within 30 days of last fill of prior drug
- **Formulary Change**: Prior auth denial or plan change within 60 days
- **Patient Preference**: None of the above criteria met

### Line of Therapy Determination:
- **1L**: First biologic/targeted therapy in the therapy area (after csDMARD failure for RA)
- **2L**: Switch to different MOA after 1L failure
- **3L**: Switch to third distinct MOA
- **Lateral Switch**: Same MOA, different molecule (not a new line)

---
## SLIDE 6: Key Opinion Leader (KOL) Identification

### KOL Classification Rule:
A prescriber is flagged IS_KOL = TRUE if ANY of:
1. Published >= 10 peer-reviewed articles in their therapy area (PubMed indexed)
2. Served as Principal Investigator on >= 1 Phase III clinical trial
3. Member of national guideline committee (ACR, AAD, AGA, NCCN)
4. Top 10% prescriber by volume in their specialty + region
5. Advisory board participant for any AbbVie compound

### KOL Relationship Inference:
If Prescriber IS_KOL AND Prescriber WORKS_AT Facility
THEN Facility IS_KOL_SITE (inferred, useful for medical affairs targeting)

---
## SLIDE 7: Data Quality & Validation Rules

### Referential Integrity:
- Every PRESCRIPTION.PATIENT_ID must exist in PATIENTS
- Every PRESCRIPTION.DRUG_ID must exist in DRUGS
- Every PRESCRIPTION.PRESCRIBER_ID must exist in PRESCRIBERS
- Every ADVERSE_EVENT.DRUG_ID must exist in DRUGS

### Temporal Constraints:
- PRESCRIPTION.FILL_DATE must be between PATIENT.ENROLLMENT_DATE and TODAY
- ADVERSE_EVENT.ONSET_DATE must be after first prescription of the drug
- TREATMENT_PATHWAY.LINE_OF_THERAPY must be sequential (no gaps)

### Completeness Rules:
- Every PATIENT must have at least one PRESCRIPTION (active cohort only)
- Every DRUG must have at least one THERAPY_AREA assignment
- Every active PRESCRIBER must have at least one PRESCRIPTION in last 12 months

---
## SLIDE 8: Ontology Evolution Protocol

### When to add a new entity class:
1. New drug approval (add to DRUGS, create new pathway entries)
2. New indication expansion (add therapy area mapping)
3. Acquisition/partnership brings new data domain

### When to add a new relationship:
1. Business asks questions that require multi-hop traversal not yet inferred
2. New data source provides direct connection previously derived
3. Regulatory requirement demands explicit lineage tracking

### Version Control:
- Every metadata change increments ontology version
- Views auto-regenerate on version change
- Agent picks up new structure without redeployment
- Previous versions accessible via Time Travel (90-day window)
