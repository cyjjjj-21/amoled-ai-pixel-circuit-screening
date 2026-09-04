-- Reproducible source map for the V2 report.
-- Run from the repository root with DuckDB.  The Python report builder performs
-- the same deterministic aggregations and embeds their snapshots in the report.

CREATE OR REPLACE VIEW v2_candidates AS
SELECT *
FROM read_csv_auto('results_v2/all_candidates.csv', header = true);

CREATE OR REPLACE VIEW v2_summary AS
SELECT *
FROM read_json_auto('results_v2/summary.json');

-- Structural candidates are reviewable design-rule inputs rather than outcomes
-- inferred from the numerical sweep.  Keeping them in SQL makes that distinction
-- visible in the report provenance instead of presenting them as measured data.
CREATE OR REPLACE VIEW v2_circuit_families AS
SELECT * FROM (VALUES
  ('F1 6T2C-GS-Shared', '6T2C', 4, 'CST: G-S', 'CDATA: G-X', '通过', '最少晶体管；SCAN_S 为 10110 双脉冲'),
  ('F2 7T2C-GS-Split', '7T2C', 5, 'CST: G-S', 'CDATA: G-X', '条件通过', '拆分 RESET/HOLD 开关；电气核心与 F1 等价'),
  ('F3 7T2C-Series-V1', '7T2C', 4, 'G-A-B-S 串联', 'DATA->A', '淘汰', '|dVGS/dVS|=11.67%，超过 5%'),
  ('F4 6T2C-Source-Inject', '6T2C', 4, 'CST: G-S', 'CDATA: S-X', '淘汰', 'WRITE 时 S 被钳位，数据增益趋近 0'),
  ('F5 5T2C-Merged-Hold/EM', '5T2C', 3, 'CST: G-S', 'CDATA: G-X', '淘汰', '无法独立完成 S 钳位、OLED 隔离和发光连接')
) AS t(family, tc, controls, storage, data_path, status, reason);

-- Sequential hard-gate funnel.  Each CTE consumes the preceding survivor set.
WITH compression AS (
  SELECT * FROM v2_candidates WHERE compression_ratio BETWEEN 0.20 AND 0.60
), source_stability AS (
  SELECT * FROM compression WHERE vgs_source_sensitivity_pct <= 5.0
), cap_area AS (
  SELECT * FROM source_stability WHERE total_cap_ff <= 240.0
), comp_settle AS (
  SELECT * FROM cap_area WHERE comp_settling_pct >= 98.0
), rc_settle AS (
  SELECT * FROM comp_settle
  WHERE source_prep_settling_pct >= 99.0 AND write_settling_pct >= 99.0
), hold_retention AS (
  SELECT * FROM rc_settle WHERE hold_droop_60hz_pct <= 5.0
), emission AS (
  SELECT * FROM hold_retention WHERE em_drop_at_300na_mv <= 100.0
)
SELECT 'raw' AS stage, count(*) AS remaining FROM v2_candidates
UNION ALL SELECT 'compression', count(*) FROM compression
UNION ALL SELECT 'source_stability', count(*) FROM source_stability
UNION ALL SELECT 'cap_area', count(*) FROM cap_area
UNION ALL SELECT 'comp_settle', count(*) FROM comp_settle
UNION ALL SELECT 'rc_settle', count(*) FROM rc_settle
UNION ALL SELECT 'hold_retention', count(*) FROM hold_retention
UNION ALL SELECT 'emission', count(*) FROM emission;
