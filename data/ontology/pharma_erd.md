# AbbVie Pharma Data Model - Entity Relationship Diagram
# ======================================================
# Upload this to @PHARMA_ONTOLOGY.GOVERNANCE.DOC_STAGE
# The AI interpreter extracts entities, relationships, and attributes.

## ENTITIES

### PATIENT
- patient_id (PK) : STRING
- age : INTEGER
- gender : STRING {Male, Female}
- primary_diagnosis : STRING
- diagnosis_code : STRING (ICD-10)
- therapy_area_id (FK) : STRING → THERAPY_AREA
- enrollment_date : DATE
- insurance_type : STRING {Commercial, Medicare, Medicaid, Medicare Advantage}
- region : STRING {Northeast, Southeast, Midwest, West, Southwest}

### DRUG
- drug_id (PK) : STRING
- brand_name : STRING
- generic_name : STRING
- therapy_area_id (FK) : STRING → THERAPY_AREA
- mechanism_of_action : STRING
- route_of_administration : STRING {Oral, Subcutaneous, IV, Ophthalmic}
- approval_date : DATE
- patent_expiry : DATE
- status : STRING {Launch, Growth, Mature}

### PRESCRIBER (HCP)
- prescriber_id (PK) : STRING
- first_name : STRING
- last_name : STRING
- npi : STRING (10-digit)
- specialty : STRING
- facility_id (FK) : STRING → FACILITY
- therapy_area_id (FK) : STRING → THERAPY_AREA
- years_in_practice : INTEGER
- is_kol : BOOLEAN (Key Opinion Leader flag)

### FACILITY
- facility_id (PK) : STRING
- facility_name : STRING
- facility_type : STRING {Academic Medical Center, Community Hospital, Specialty Practice, Infusion Center, Specialty Pharmacy}
- health_system : STRING
- address_state : STRING (2-letter)
- region : STRING
- bed_count : INTEGER
- is_teaching_hospital : BOOLEAN
- infusion_center : BOOLEAN

### PRESCRIPTION
- rx_id (PK) : STRING
- patient_id (FK) : STRING → PATIENT
- drug_id (FK) : STRING → DRUG
- prescriber_id (FK) : STRING → PRESCRIBER
- facility_id (FK) : STRING → FACILITY
- fill_date : DATE
- days_supply : INTEGER
- refill_number : INTEGER
- quantity : FLOAT
- prior_auth_required : BOOLEAN
- switch_from_drug_id (FK) : STRING → DRUG (nullable)
- switch_reason : STRING {Inadequate response, Adverse event, Insurance formulary change, Patient preference} (nullable)

### THERAPY_AREA
- therapy_area_id (PK) : STRING
- therapy_area_name : STRING
- parent_area (FK) : STRING → THERAPY_AREA (self-referencing hierarchy)
- description : STRING
- priority_level : STRING {Primary, Secondary}

### TREATMENT_PATHWAY
- pathway_id (PK) : STRING
- therapy_area_id (FK) : STRING → THERAPY_AREA
- diagnosis : STRING
- line_of_therapy : INTEGER {1, 2, 3}
- drug_id (FK) : STRING → DRUG
- prior_drug_id (FK) : STRING → DRUG (nullable, the drug this follows)
- switch_criteria : STRING
- evidence_level : STRING {Level A, Level B, Level C}
- guideline_source : STRING

### ADVERSE_EVENT
- ae_id (PK) : STRING
- patient_id (FK) : STRING → PATIENT
- drug_id (FK) : STRING → DRUG
- event_type : STRING {Infection, Gastrointestinal, Dermatologic, Hepatic, Cardiovascular, Hematologic}
- event_term : STRING (MedDRA preferred term)
- severity : STRING {Mild, Moderate, Severe}
- serious : BOOLEAN
- onset_date : DATE
- resolution_date : DATE (nullable)
- outcome : STRING {Recovered, Recovering, Not recovered, Recovered with sequelae, Unknown}
- reporter_type : STRING {Physician, Patient, Pharmacist}
- causality_assessment : STRING {Probable, Possible, Unlikely, Unassessable}


## RELATIONSHIPS

PATIENT --[IS_DIAGNOSED_WITH]--> THERAPY_AREA (N:1)
  A patient has one primary therapy area assignment based on diagnosis

PATIENT --[IS_PRESCRIBED]--> DRUG (N:N via PRESCRIPTION)
  Patients receive prescriptions for one or more drugs over time

PATIENT --[EXPERIENCES]--> ADVERSE_EVENT (1:N)
  A patient may have zero or more adverse events reported

PATIENT --[FOLLOWS]--> TREATMENT_PATHWAY (N:1)
  Each patient follows a treatment pathway based on diagnosis and line of therapy

DRUG --[TREATS]--> THERAPY_AREA (N:1)
  Each drug is approved for a primary therapy area

DRUG --[CAUSES]--> ADVERSE_EVENT (1:N)
  A drug may be associated with reported adverse events

DRUG --[PRECEDES]--> DRUG (via TREATMENT_PATHWAY, ordered by line_of_therapy)
  In a treatment pathway, one drug follows another when patients switch

PRESCRIBER --[PRESCRIBES]--> DRUG (N:N via PRESCRIPTION)
  Prescribers write prescriptions for drugs

PRESCRIBER --[WORKS_AT]--> FACILITY (N:1)
  Each prescriber is affiliated with a primary facility

PRESCRIBER --[SPECIALIZES_IN]--> THERAPY_AREA (N:1)
  Each prescriber has a primary therapy area alignment

FACILITY --[BELONGS_TO]--> HEALTH_SYSTEM (N:1 via health_system column)
  Facilities are grouped into integrated delivery networks

FACILITY --[LOCATED_IN]--> REGION (N:1)
  Geographic assignment

THERAPY_AREA --[PARENT_OF]--> THERAPY_AREA (1:N, self-referencing hierarchy)
  Immunology > Rheumatology, Dermatology, Gastroenterology
  Oncology > Hematologic Oncology, Solid Tumors
  Neuroscience > Migraine, Parkinson's


## HIERARCHY

THERAPY_AREA hierarchy:
├── Immunology
│   ├── Rheumatology
│   ├── Dermatology
│   └── Gastroenterology
├── Oncology
│   ├── Hematologic Oncology
│   └── Solid Tumors
├── Neuroscience
│   ├── Migraine
│   └── Parkinson's
├── Eye Care
└── Aesthetics


## INFERENCE RULES

1. INVERSE: If Patient IS_PRESCRIBED Drug, then Drug IS_PRESCRIBED_TO Patient
2. INVERSE: If Drug PRECEDES Drug2 in pathway, then Drug2 FOLLOWS Drug
3. CHAIN: Patient→Prescription→Drug→TherapyArea => Patient→TherapyArea (inferred)
4. CHAIN: Patient→Prescription→Prescriber→Facility => Patient→Facility (inferred: where patient receives care)
5. 2-STAGE: Patient→Drug→AdverseEvent + Drug→TherapyArea => TherapyArea has safety signal (aggregate inference)
