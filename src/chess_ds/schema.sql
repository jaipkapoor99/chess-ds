-- =============================================================================
-- chess-ds: Strict 3rd Normal Form (3NF) Database DDL (DuckDB / ANSI SQL)
-- =============================================================================
-- 1NF: Atomic values (no repeating groups, themes normalized into bridge tables).
-- 2NF: No partial key dependencies (every non-key attribute fully depends on whole PK).
-- 3NF: No transitive dependencies (e.g. openings, players, engines, themes isolated).
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. DIMENSION & ENTITY TABLES (Independent Master Entities)
-- -----------------------------------------------------------------------------

-- Players Master (Eliminates transitive player attributes from games)
CREATE TABLE IF NOT EXISTS players (
    player_id         VARCHAR PRIMARY KEY,   -- Lichess username or FIDE ID (e.g. 'magnuscarlsen')
    display_name      VARCHAR NOT NULL,
    title             VARCHAR(10),           -- 'GM', 'IM', 'FM', 'WGM', etc.
    country           VARCHAR(3)             -- ISO 3166-1 alpha-3 code
);

-- Openings Master (Eliminates transitive dependency: eco -> opening_name in games)
CREATE TABLE IF NOT EXISTS openings (
    eco               VARCHAR(3) PRIMARY KEY, -- 'A00' through 'E99'
    opening_name      VARCHAR NOT NULL,       -- e.g. 'Sicilian Defense'
    variation_name    VARCHAR                 -- e.g. 'Najdorf Variation'
);

-- Engines Master (Eliminates repeating engine definitions in evaluation telemetry)
CREATE TABLE IF NOT EXISTS engines (
    engine_id         VARCHAR PRIMARY KEY,    -- e.g. 'lc0_v0_32_1', 'stockfish_18'
    engine_name       VARCHAR NOT NULL,
    version           VARCHAR NOT NULL,
    eval_paradigm     VARCHAR NOT NULL,       -- 'Neural_MCTS', 'Alpha_Beta_NNUE'
    hardware_target   VARCHAR NOT NULL        -- 'GPU_TensorCore', 'CPU_AVX512'
);

-- Tactical Themes Master (Atomic taxonomy for 1NF/3NF puzzle categorization)
CREATE TABLE IF NOT EXISTS themes (
    theme_id          VARCHAR PRIMARY KEY,    -- e.g. 'pin', 'fork', 'mateIn2'
    description       VARCHAR
);

-- -----------------------------------------------------------------------------
-- 2. PUZZLE RELATIONS (3NF Normalized)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS puzzles (
    puzzle_id         VARCHAR PRIMARY KEY,
    fen               VARCHAR NOT NULL,
    solution_uci      VARCHAR(5) NOT NULL,    -- Winning move (atomic)
    rating            INTEGER NOT NULL,
    rating_deviation  INTEGER,
    popularity        INTEGER DEFAULT 100,
    nb_plays          INTEGER DEFAULT 0,
    game_url          VARCHAR,
    daily_date        DATE
);

-- Puzzle-to-Theme Bridge Table (1NF / 3NF decomposition of multi-value themes)
CREATE TABLE IF NOT EXISTS puzzle_themes (
    puzzle_id         VARCHAR NOT NULL REFERENCES puzzles(puzzle_id),
    theme_id          VARCHAR NOT NULL REFERENCES themes(theme_id),
    PRIMARY KEY (puzzle_id, theme_id)
);

-- Puzzle Evaluation Results (Depends only on candidate key (puzzle_id, engine_id))
CREATE TABLE IF NOT EXISTS puzzle_evaluations (
    puzzle_id         VARCHAR NOT NULL REFERENCES puzzles(puzzle_id),
    engine_id         VARCHAR NOT NULL REFERENCES engines(engine_id),
    engine_move       VARCHAR(5) NOT NULL,
    is_correct        BOOLEAN NOT NULL,
    depth             INTEGER NOT NULL,
    nps               DOUBLE NOT NULL,
    elapsed_seconds   DOUBLE NOT NULL,
    evaluated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (puzzle_id, engine_id)
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
    move_number       INTEGER NOT NULL,      -- Full move (1, 1, 2, 2, ...)
    turn              VARCHAR(1) NOT NULL,   -- 'w' or 'b'
    fen               VARCHAR NOT NULL,
    move_uci          VARCHAR(5) NOT NULL,
    move_san          VARCHAR(10) NOT NULL,
    eval_cp           INTEGER,               -- Position evaluation after move
    eval_mate         INTEGER,               -- Mate distance
    best_engine_move  VARCHAR(5),
    centipawn_loss    INTEGER,               -- Loss relative to optimal engine move
    judgment          VARCHAR(15),           -- 'best', 'inaccuracy', 'mistake', 'blunder'
    clock_seconds     DOUBLE,
    PRIMARY KEY (game_id, ply)
);

-- -----------------------------------------------------------------------------
-- 4. PERFORMANCE INDEXES
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_puzzle_eval_correct ON puzzle_evaluations(is_correct);
CREATE INDEX IF NOT EXISTS idx_puzzle_rating ON puzzles(rating);
CREATE INDEX IF NOT EXISTS idx_games_players ON games(white_player_id, black_player_id);
CREATE INDEX IF NOT EXISTS idx_games_eco ON games(eco);
CREATE INDEX IF NOT EXISTS idx_moves_judgment ON game_moves(judgment);
