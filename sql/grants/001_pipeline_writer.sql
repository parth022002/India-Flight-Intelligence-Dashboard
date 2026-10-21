BEGIN;

GRANT USAGE ON SCHEMA public TO ifi_pipeline_writer;

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

GRANT INSERT, UPDATE
ON TABLE public.collection_runs
TO ifi_pipeline_writer;

GRANT SELECT (run_id)
ON TABLE public.collection_runs
TO ifi_pipeline_writer;

GRANT USAGE
ON SEQUENCE public.airports_airport_id_seq
TO ifi_pipeline_writer;

GRANT USAGE
ON SEQUENCE public.collection_runs_run_id_seq
TO ifi_pipeline_writer;

COMMIT;
