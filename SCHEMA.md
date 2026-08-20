# ♟️ Database Relational Architecture & 3NF Schema

This document details the Strict Third Normal Form (3NF) relational architecture for the `chess-ds` analytical platform.

______________________________________________________________________

## 1. 3NF Relational Architecture Map

```txt
┌──────────────┐         ┌──────────────────────┐         ┌─────────────┐
│   puzzles    │◄───1:N──│  puzzle_evaluations  │───N:1──►│   engines   │
└──────┬───────┘         └──────────────────────┘         └─────────────┘
       │ 1:N
       ▼
┌──────────────┐         ┌──────────────┐
│ puzzle_themes│───N:1──►│    themes    │
└──────────────┘         └──────────────┘

┌──────────────┐         ┌──────────────────────┐         ┌─────────────┐
│   players    │◄───1:N──│        games         │───N:1──►│  openings   │
└──────────────┘         └──────────┬───────────┘         └─────────────┘
                                    │ 1:N
                                    ▼
                         ┌──────────────────────┐
                         │      game_moves      │
                         └──────────────────────┘
```

______________________________________________________________________

## 2. Normal Form Compliance (1NF, 2NF, 3NF)

1. **First Normal Form (1NF)**:

   - All attributes contain atomic values.
   - Repeating tactical themes are decomposed into the `puzzle_themes` bridge entity.

1. **Second Normal Form (2NF)**:

   - In composite primary key tables (`puzzle_evaluations`, `puzzle_themes`, `game_moves`), every non-key column fully depends on the whole composite primary key.

1. **Third Normal Form (3NF)**:

   - Transitive functional dependencies are eliminated:
     - `eco -> opening_name` is isolated into `openings`.
     - Player metadata is isolated into `players`.
     - Engine configurations are isolated into `engines`.

______________________________________________________________________

## 3. Physical DDL Reference

The complete executable DDL is maintained in:
`src/chess_ds/schema.sql`
