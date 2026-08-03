-- Import AbbVie pharma OSI semantic model into Snowflake (run after ontology build).
-- Requires OSI YAML at outputs/ontology/abbvie_pharma_intelligence_v2.1.0.yaml
-- Upload YAML to a stage first, or paste content into the procedure call.

USE DATABASE ABBVIE_DATAOPS_DEV;
USE SCHEMA CURATED;

-- Example: create stage for OSI artifacts
CREATE STAGE IF NOT EXISTS OSI_ARTIFACTS
  DIRECTORY = (ENABLE = TRUE)
  COMMENT = 'Versioned OSI YAML from Data Ops SDK ontology pipeline';

-- After uploading abbvie_pharma_intelligence_v2.1.0.yaml to @OSI_ARTIFACTS:
-- CALL SYSTEM$CREATE_SEMANTIC_VIEW_FROM_OSSIE_YAML(
--   'ABBVIE_DATAOPS_DEV.CURATED',
--   (SELECT $1 FROM @OSI_ARTIFACTS/abbvie_pharma_intelligence_v2.1.0.yaml (FILE_FORMAT => 'YAML'))
-- );

-- Verify semantic view exists and export round-trip
-- SELECT SYSTEM$READ_OSSIE_YAML_FROM_SEMANTIC_VIEW('ABBVIE_DATAOPS_DEV.CURATED.ABBVIE_PHARMA_INTELLIGENCE');
