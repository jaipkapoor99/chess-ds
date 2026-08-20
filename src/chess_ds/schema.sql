-- =============================================================================
-- chess-ds: Official Analytical Database DDL (DuckDB / SQL Standard)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. PUZZLE DATA & ENGINE EVALUATION TELEMETRY
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS puzzles (
    puzzle_id         VARCHAR PRIMARY KEY,
    fen               VARCHAR NOT NULL,
    solution          VARCHAR NOT NULL,
    rating            INTEGER NOT NULL,
    popularity        INTEGER DEFAULT 100,
    themes            VARCHAR,
    game_url          VARCHAR,
    daily_date        VARCHAR
);

CREATE TABLE IF NOT EXISTS puzzle_evaluations (
    evaluation_id     BIGINT PRIMARY KEY,
    puzzle_id         VARCHAR NOT NULL REFERENCES puzzles(puzzle_id),
    engine            VARCHAR NOT NULL,
    fen               VARCHAR NOT NULL,
    expected_move     VARCHAR NOT NULL,
    engine_move       VARCHAR NOT NULL,
    is_correct        BOOLEAN NOT NULL,
    depth             INTEGER NOT NULL,
    nps               DOUBLE NOT NULL,
    elapsed_seconds   DOUBLE NOT NULL,
    rating            INTEGER NOT NULL,
    evaluated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_puzzle_eval_engine ON puzzle_evaluations(engine);
CREATE INDEX IF NOT EXISTS idx_puzzle_eval_correct ON puzzle_evaluations(is_correct);

-- -----------------------------------------------------------------------------
-- 2. FULL GAMES & MOVE-BY-MOVE TRAJECTORIES (EXPANDED RELATIONAL MODEL)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS games (
    game_id           VARCHAR PRIMARY KEY,
    event             VARCHAR,
    site_url          VARCHAR,
    game_date         DATE,
    white_player      VARCHAR NOT NULL,
    black_player      VARCHAR NOT NULL,
    white_elo         INTEGER,
    black_elo         INTEGER,
    white_title       VARCHAR,
    black_title       VARCHAR,
    result            VARCHAR(7) NOT NULL,    -- '1-0', '0-1', '1/2-1/2', '*'
    time_control      VARCHAR,               -- e.g. '180+0', '900+10'
    eco               VARCHAR(3),            -- e.g. 'E04'
    opening_name      VARCHAR,               -- e.g. 'Catalan Opening'
    total_plies       INTEGER NOT NULL,
    termination       VARCHAR,               -- 'Normal', 'Time forfeit', 'Rules infraction'
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS game_moves (
    move_id           BIGINT PRIMARY KEY,
    game_id           VARCHAR NOT NULL REFERENCES games(game_id),
    ply               INTEGER NOT NULL,      -- Half-move index (1 = White move 1, 2 = Black move 1)
    move_number       INTEGER NOT NULL,      -- Full move number (1, 2, 3...)
    turn              VARCHAR(1) NOT NULL,   -- 'w' or 'b'
    fen               VARCHAR NOT NULL,      -- FEN before move
    move_uci          VARCHAR(5) NOT NULL,   -- e.g. 'e2e4'
    move_san          VARCHAR(10) NOT NULL,  -- e.g. 'e4', 'Nf3', 'O-O'
    eval_cp           INTEGER,               -- Centipawn eval (+100 = White +1.00 pawn)
    eval_mate         INTEGER,               -- Mate in N (+3 = White mates in 3)
    best_engine_move  VARCHAR(5),            -- Best move found by engine
    centipawn_loss    INTEGER,               -- CPL = best_eval - played_eval
    judgment          VARCHAR(15),           -- 'best', 'good', 'inaccuracy', 'mistake', 'blunder'
    clock_seconds     DOUBLE                 -- Remaining clock time
);

CREATE INDEX IF NOT EXISTS idx_game_moves_game_id ON game_moves(game_id);
CREATE INDEX IF NOT EXISTS idx_game_moves_judgment ON game_moves(judgment);
CREATE INDEX IF NOT EXISTS idx_game_moves_eco ON games(eco);
