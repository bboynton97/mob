CREATE TABLE IF NOT EXISTS contributions (
  github_user  TEXT NOT NULL,
  pet          TEXT NOT NULL,
  machine_fp   TEXT NOT NULL,
  xp           INTEGER NOT NULL CHECK (xp >= 0),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (github_user, pet, machine_fp)
);

CREATE TABLE IF NOT EXISTS pets_meta (
  github_user   TEXT NOT NULL,
  pet           TEXT NOT NULL,
  pet_name      TEXT,
  display_name  TEXT NOT NULL,
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (github_user, pet)
);

CREATE INDEX IF NOT EXISTS contributions_totals_idx
  ON contributions (github_user, pet, xp);
