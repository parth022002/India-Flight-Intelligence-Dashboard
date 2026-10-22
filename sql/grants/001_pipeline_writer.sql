BEGIN;

-- Schema access
GRANT USAGE ON SCHEMA public TO ifi_pipeline_writer;

-- Airport master import: preserve existing permissions
GRANT INSERT, UPDATE
ON TABLE public.airports
TO ifi_pipeline_writer;

GRANT SELECT (
    source_name,
    source_airport_id,
    ident,
    airport_type,
    name,
    latitude_deg,
    longitude_deg,
    elevation_ft,
    iso_country,
    iso_region,
    municipality,
    scheduled_service,
    icao_code,
    iata_code,
    master_scope,
    source_build_date
)
ON TABLE public.airports
TO ifi_pipeline_writer;

-- Collection run creation and finalization
GRANT INSERT
ON TABLE public.collection_runs
TO ifi_pipeline_writer;

-- Remove the previous table-wide UPDATE privilege before narrowing it.
REVOKE UPDATE
ON TABLE public.collection_runs
FROM ifi_pipeline_writer;

GRANT SELECT (
    run_id,
    source_id,
    run_type,
    status
)
ON TABLE public.collection_runs
TO ifi_pipeline_writer;

GRANT UPDATE (
    status,
    finished_at,
    records_received,
    records_accepted,
    records_rejected,
    error_code,
    error_summary
)
ON TABLE public.collection_runs
TO ifi_pipeline_writer;

-- Source verification: only the fields the orchestrator needs
GRANT SELECT (
    source_id,
    source_name,
    data_type,
    license_status
)
ON TABLE public.data_sources
TO ifi_pipeline_writer;

-- ADS-B observation persistence
GRANT INSERT (
    run_id,
    source_id,
    source_type,
    source_record_key,
    observed_at,
    aircraft_id,
    icao24,
    callsign,
    latitude_deg,
    longitude_deg,
    altitude_ft,
    on_ground,
    assigned_airport_id,
    assignment_distance_nm,
    assignment_reason,
    assignment_rule_version,
    raw_payload
)
ON TABLE public.adsb_observations
TO ifi_pipeline_writer;

-- Identity sequences used by inserts
GRANT USAGE
ON SEQUENCE public.airports_airport_id_seq
TO ifi_pipeline_writer;

GRANT USAGE
ON SEQUENCE public.collection_runs_run_id_seq
TO ifi_pipeline_writer;

GRANT USAGE
ON SEQUENCE public.adsb_observations_observation_id_seq
TO ifi_pipeline_writer;

COMMIT;
