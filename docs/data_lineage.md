# Data lineage

Every public metric should be traceable from a chart/tile to aggregate version, transformation version, input rows, and source retrieval.

Minimum lineage: `source_name`, `source_url`, `source_document_id` where relevant, `source_type`, source time, `retrieved_at`, `ingested_at`, `pipeline_run_id`, transformation name/version, validation status, rejection reason, aggregate version, and publication time.

Never silently overwrite source values. Corrections should be auditable and retain source values where license/privacy rules permit.
