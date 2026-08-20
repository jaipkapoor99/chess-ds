-- =============================================================================
-- chess-ds: Strict 3rd Normal Form (3NF) Database DDL (DuckDB / PostgreSQL ANSI)
-- =============================================================================
-- 1NF: Atomic attributes, explicit column types, no repeating groups.
-- 2NF: No partial key dependencies; all non-key columns depend on whole PK.
-- 3NF: No transitive functional dependencies; entities completely decoupled.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. DIMENSION & ENTITY TABLES
-- -----------------------------------------------------------------------------

-- Players Dimension
CREATE TABLE IF NOT EXISTS players (
    player_id         VARCHAR PRIMARY KEY,   -- Lichess username or FIDE ID (e.g. 'magnuscarlsen')
    display_name      VARCHAR NOT NULL,
    title             VARCHAR(10),           -- 'GM', 'IM', 'FM', 'WGM', etc.
    country           VARCHAR(3)             -- ISO 3166-1 alpha-3 code
);

-- Openings Master Dimension (ECO Classification)
CREATE TABLE IF NOT EXISTS openings (
    eco               VARCHAR(3) PRIMARY KEY, -- 'A00' through 'E99'
    opening_name      VARCHAR NOT NULL,       -- e.g. 'Sicilian Defense'
    variation_name    VARCHAR                 -- e.g. 'Najdorf Variation'
);

-- Engines Master Dimension
CREATE TABLE IF NOT EXISTS engines (
    engine_id         VARCHAR PRIMARY KEY,    -- e.g. 'lc0_v0_32_1', 'stockfish_18'
    engine_name       VARCHAR NOT NULL,
    version           VARCHAR NOT NULL,
    eval_paradigm     VARCHAR NOT NULL,       -- 'Neural_MCTS', 'Alpha_Beta_NNUE'
    hardware_target   VARCHAR NOT NULL        -- 'GPU_TensorCore', 'CPU_AVX512'
);

-- Tactical Themes Dimension
CREATE TABLE IF NOT EXISTS themes (
    theme_id          VARCHAR PRIMARY KEY,    -- e.g. 'pin', 'fork', 'mateIn2', 'deflection'
    description       VARCHAR
);

-- Benchmark Run Executions (Enables tracking multiple benchmark runs over time)
CREATE TABLE IF NOT EXISTS benchmark_runs (
    run_id            VARCHAR PRIMARY KEY,    -- e.g. 'run_20260820_123000'
    movetime_ms       INTEGER NOT NULL,
    total_puzzles     INTEGER NOT NULL,
    wandb_run_id      VARCHAR,
    started_at        TIMESTAMP NOT NULL,
    completed_at      TIMESTAMP
);

-- -----------------------------------------------------------------------------
-- 2. PUZZLE RELATIONS (3NF Normalized)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS puzzles (
    puzzle_id         VARCHAR PRIMARY KEY,
    fen               VARCHAR NOT NULL,
    solution_uci      VARCHAR(5) NOT NULL,    -- Initial winning response
    rating            INTEGER NOT NULL,
    rating_deviation  INTEGER,
    popularity        INTEGER DEFAULT 100,
    nb_plays          INTEGER DEFAULT 0,
    game_url          VARCHAR,
    daily_date        DATE
);

-- Puzzle Themes Bridge (1NF / 3NF Many-to-Many Mapping)
CREATE TABLE IF NOT EXISTS puzzle_themes (
    puzzle_id         VARCHAR NOT NULL REFERENCES puzzles(puzzle_id),
    theme_id          VARCHAR NOT NULL REFERENCES themes(theme_id),
    PRIMARY KEY (puzzle_id, theme_id)
);

-- Puzzle Evaluations Telemetry (Composite Key: run_id, puzzle_id, engine_id)
CREATE TABLE IF NOT EXISTS puzzle_evaluations (
    run_id            VARCHAR NOT NULL REFERENCES benchmark_runs(run_id),
    puzzle_id         VARCHAR NOT NULL REFERENCES puzzles(puzzle_id),
    engine_id         VARCHAR NOT NULL REFERENCES engines(engine_id),
    engine_move       VARCHAR(5) NOT NULL,
    engine_move_san   VARCHAR(10),
    solution_san      VARCHAR(10),
    is_correct        BOOLEAN NOT NULL,
    depth             INTEGER NOT NULL,
    nps               DOUBLE NOT NULL,
    elapsed_seconds   DOUBLE NOT NULL,
    evaluated_at      TIMESTAMP NOT NULL,
    PRIMARY KEY (run_id, puzzle_id, engine_id)
);

-- -----------------------------------------------------------------------------
-- 3. FULL GAME RELATIONS (3NF Normalized)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS games (
    game_id           VARCHAR PRIMARY KEY,
    event             VARCHAR,
    site_url          VARCHAR,
    game_date         DATE,
    white_player_id   VARCHAR NOT NULL REFERENCES players(player_id),
    black_player_id   VARCHAR NOT NULL REFERENCES players(player_id),
    white_elo         INTEGER,
    black_elo         INTEGER,
    result            VARCHAR(7) NOT NULL,    -- '1-0', '0-1', '1/2-1/2', '*'
    time_control      VARCHAR,               -- '180+0', '900+10'
    eco               VARCHAR(3) REFERENCES openings(eco),
    total_plies       INTEGER NOT NULL,
    termination       VARCHAR,               -- 'Normal', 'Time forfeit'
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS game_moves (
    game_id           VARCHAR NOT NULL REFERENCES games(game_id),
    ply               INTEGER NOT NULL,      -- Half-move sequence (1, 2, 3, ...)
    move_number       INTEGER NOT NULL,      -- Full move number (1, 1, 2, 2, ...)
    turn              VARCHAR(1) NOT NULL,   -- 'w' or 'b'
    fen               VARCHAR NOT NULL,
    move_uci          VARCHAR(5) NOT NULL,
    move_san          VARCHAR(10) NOT NULL,
    eval_cp           INTEGER,               -- Position centipawn eval after move
    eval_mate         INTEGER,               -- Mate distance
    best_engine_move  VARCHAR(5),
    centipawn_loss    INTEGER,               -- Accuracy difference vs. engine best
    judgment          VARCHAR(15),           -- 'best', 'inaccuracy', 'mistake', 'blunder'
    clock_seconds     DOUBLE,
    PRIMARY KEY (game_id, ply)
);

-- -----------------------------------------------------------------------------
-- 4. ENGINE VS ENGINE MATCH RELATIONS (3NF Normalized)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS engine_matches (
    match_id          VARCHAR PRIMARY KEY,    -- e.g. 'match_20260820_131500'
    engine1_id        VARCHAR NOT NULL REFERENCES engines(engine_id),
    engine2_id        VARCHAR NOT NULL REFERENCES engines(engine_id),
    time_control      VARCHAR NOT NULL,       -- e.g. '10+0.1', '60+1'
    total_rounds      INTEGER NOT NULL,
    concurrency       INTEGER DEFAULT 1,
    engine1_score     DOUBLE DEFAULT 0.0,
    engine2_score     DOUBLE DEFAULT 0.0,
    draws             INTEGER DEFAULT 0,
    pgn_path          VARCHAR,
    started_at        TIMESTAMP NOT NULL,
    completed_at      TIMESTAMP
);

CREATE TABLE IF NOT EXISTS engine_match_games (
    game_id                VARCHAR PRIMARY KEY,    -- e.g. 'match_20260820_131500_g1'
    match_id               VARCHAR NOT NULL REFERENCES engine_matches(match_id),
    round_number           INTEGER NOT NULL,
    white_engine_id        VARCHAR NOT NULL REFERENCES engines(engine_id),
    black_engine_id        VARCHAR NOT NULL REFERENCES engines(engine_id),
    result                 VARCHAR(7) NOT NULL,    -- '1-0', '0-1', '1/2-1/2', '*'
    total_plies            INTEGER NOT NULL,
    white_avg_depth        DOUBLE,
    black_avg_depth        DOUBLE,
    white_avg_movetime_sec DOUBLE,
    black_avg_movetime_sec DOUBLE,
    termination            VARCHAR,                -- 'Adjudication', 'Checkmate', 'Time forfeit'
    moves_pgn              TEXT,
    played_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------------------------
-- 5. PERFORMANCE & ANALYTICAL INDEXES
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_puzzle_eval_correct ON puzzle_evaluations(is_correct);
CREATE INDEX IF NOT EXISTS idx_puzzle_eval_run ON puzzle_evaluations(run_id);
CREATE INDEX IF NOT EXISTS idx_puzzle_rating ON puzzles(rating);
CREATE INDEX IF NOT EXISTS idx_games_players ON games(white_player_id, black_player_id);
CREATE INDEX IF NOT EXISTS idx_games_eco ON games(eco);
CREATE INDEX IF NOT EXISTS idx_moves_judgment ON game_moves(judgment);
CREATE INDEX IF NOT EXISTS idx_moves_fen ON game_moves(fen);
CREATE INDEX IF NOT EXISTS idx_matches_engines ON engine_matches(engine1_id, engine2_id);
CREATE INDEX IF NOT EXISTS idx_match_games_match ON engine_match_games(match_id);
