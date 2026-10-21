BEGIN;
CREATE TABLE IF NOT EXISTS schema_migrations (
    version         VARCHAR(100) PRIMARY KEY,
    description     TEXT NOT NULL,
    checksum_sha256 CHAR(64) NOT NULL,
    applied_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS data_sources (
    source_id       BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_name     TEXT NOT NULL UNIQUE,
    source_url      TEXT NOT NULL,
    data_type       TEXT NOT NULL,
    license_status  TEXT NOT NULL DEFAULT 'not_reviewed'
        CHECK (license_status IN (
            'not_reviewed', 'under_review', 'approved', 'restricted', 'rejected'
        )),
    attribution_required BOOLEAN,
    redistribution_allowed BOOLEAN,
    retention_notes TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS airports (
    airport_id       BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_name      TEXT NOT NULL DEFAULT 'OurAirports',
    source_airport_id TEXT NOT NULL,
    ident            TEXT,
    airport_type     TEXT NOT NULL,
    name             TEXT NOT NULL,
    latitude_deg     DOUBLE PRECISION NOT NULL
        CHECK (latitude_deg BETWEEN -90 AND 90),
    longitude_deg    DOUBLE PRECISION NOT NULL
        CHECK (longitude_deg BETWEEN -180 AND 180),
    elevation_ft     INTEGER,
    iso_country      CHAR(2) NOT NULL,
    iso_region       TEXT,
    municipality     TEXT,
    scheduled_service BOOLEAN,
    icao_code        TEXT,
    iata_code        TEXT,
    master_scope     TEXT NOT NULL,
    source_build_date DATE,
    imported_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (source_name, source_airport_id)
);
CREATE INDEX IF NOT EXISTS idx_airports_country
    ON airports (iso_country);
CREATE INDEX IF NOT EXISTS idx_airports_icao
    ON airports (icao_code)
    WHERE icao_code IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_airports_iata
    ON airports (iata_code)
    WHERE iata_code IS NOT NULL;
CREATE TABLE IF NOT EXISTS airport_tiers (
    airport_tier_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    airport_id      BIGINT NOT NULL REFERENCES airports(airport_id),
    tier_code       TEXT NOT NULL
        CHECK (tier_code IN ('T0', 'T1', 'T2', 'T3', 'T4', 'T5', 'T6')),
    annual_movements BIGINT CHECK (annual_movements >= 0),
    movement_year   SMALLINT CHECK (movement_year BETWEEN 1900 AND 2200),
    poll_interval_minutes INTEGER NOT NULL
        CHECK (poll_interval_minutes > 0),
    live_adsb_retention_months INTEGER NOT NULL
        CHECK (live_adsb_retention_months > 0),
    classification_status TEXT NOT NULL DEFAULT 'unclassified'
        CHECK (classification_status IN (
            'classified', 'unclassified', 'pending_review'
        )),
    classification_basis TEXT,
    valid_from      DATE NOT NULL DEFAULT CURRENT_DATE,
    valid_to        DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (valid_to IS NULL OR valid_to >= valid_from),
    CHECK (
        tier_code NOT IN ('T5', 'T6')
        OR classification_status <> 'classified'
    )
);
CREATE INDEX IF NOT EXISTS idx_airport_tiers_airport
    ON airport_tiers (airport_id, valid_from DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_airport_tiers_one_current
    ON airport_tiers (airport_id)
    WHERE valid_to IS NULL;
CREATE TABLE IF NOT EXISTS collection_runs (
    run_id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_id       BIGINT REFERENCES data_sources(source_id),
    run_type        TEXT NOT NULL
        CHECK (run_type IN (
            'airport_master_import', 'live_poll', 'archive_sample',
            'official_statistics', 'weather', 'analytics', 'maintenance'
        )),
    status          TEXT NOT NULL DEFAULT 'running'
        CHECK (status IN (
            'running', 'succeeded', 'partial', 'failed', 'cancelled'
        )),
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    records_received BIGINT NOT NULL DEFAULT 0 CHECK (records_received >= 0),
    records_accepted BIGINT NOT NULL DEFAULT 0 CHECK (records_accepted >= 0),
    records_rejected BIGINT NOT NULL DEFAULT 0 CHECK (records_rejected >= 0),
    error_code      TEXT,
    error_summary   TEXT,
    metadata        JSONB NOT NULL DEFAULT '{}'::JSONB,
    CHECK (finished_at IS NULL OR finished_at >= started_at),
    CHECK (
        status = 'running'
        OR finished_at IS NOT NULL
    )
);
CREATE INDEX IF NOT EXISTS idx_collection_runs_started
    ON collection_runs (started_at DESC);
CREATE INDEX IF NOT EXISTS idx_collection_runs_status
    ON collection_runs (status, started_at DESC);
CREATE TABLE IF NOT EXISTS adsb_observations (
    observation_id  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id          BIGINT NOT NULL REFERENCES collection_runs(run_id),
    source_id       BIGINT NOT NULL REFERENCES data_sources(source_id),
    source_type     TEXT NOT NULL
        CHECK (source_type IN ('live_poll', 'archive_sample')),
    source_record_key TEXT NOT NULL,
    observed_at     TIMESTAMPTZ,
    ingested_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    aircraft_id     TEXT,
    icao24          TEXT,
    callsign        TEXT,
    latitude_deg    DOUBLE PRECISION
        CHECK (latitude_deg IS NULL OR latitude_deg BETWEEN -90 AND 90),
    longitude_deg   DOUBLE PRECISION
        CHECK (longitude_deg IS NULL OR longitude_deg BETWEEN -180 AND 180),
    altitude_ft     DOUBLE PRECISION,
    on_ground       BOOLEAN,
    assigned_airport_id BIGINT REFERENCES airports(airport_id),
    assignment_distance_nm DOUBLE PRECISION
        CHECK (assignment_distance_nm IS NULL OR assignment_distance_nm >= 0),
    assignment_reason TEXT,
    assignment_rule_version TEXT,
    raw_payload     JSONB,
    UNIQUE (run_id, source_record_key)
);
CREATE OR REPLACE FUNCTION validate_adsb_observation_run_type()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    linked_run_type TEXT;
BEGIN
    SELECT run_type
    INTO linked_run_type
    FROM collection_runs
    WHERE run_id = NEW.run_id;
    IF linked_run_type IS NULL THEN
        RAISE EXCEPTION 'Collection run % does not exist', NEW.run_id;
    END IF;
    IF NEW.source_type = 'live_poll'
       AND linked_run_type <> 'live_poll' THEN
        RAISE EXCEPTION
            'source_type live_poll requires a live_poll collection run';
    END IF;
    IF NEW.source_type = 'archive_sample'
       AND linked_run_type <> 'archive_sample' THEN
        RAISE EXCEPTION
            'source_type archive_sample requires an archive_sample collection run';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER trg_validate_adsb_observation_run_type
BEFORE INSERT OR UPDATE OF run_id, source_type
ON adsb_observations
FOR EACH ROW
EXECUTE FUNCTION validate_adsb_observation_run_type();
CREATE INDEX IF NOT EXISTS idx_adsb_observations_time
    ON adsb_observations (observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_adsb_observations_aircraft_time
    ON adsb_observations (aircraft_id, observed_at DESC)
    WHERE aircraft_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_adsb_observations_airport_time
    ON adsb_observations (assigned_airport_id, observed_at DESC)
    WHERE assigned_airport_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_adsb_observations_run
    ON adsb_observations (run_id);
CREATE TABLE IF NOT EXISTS quality_checks (
    quality_check_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id          BIGINT REFERENCES collection_runs(run_id),
    check_name      TEXT NOT NULL,
    status          TEXT NOT NULL
        CHECK (status IN ('passed', 'warning', 'failed', 'not_evaluated')),
    checked_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    affected_records BIGINT CHECK (affected_records >= 0),
    details         JSONB NOT NULL DEFAULT '{}'::JSONB
);
CREATE INDEX IF NOT EXISTS idx_quality_checks_run
    ON quality_checks (run_id, checked_at DESC);
COMMIT;
