from __future__ import annotations
import sqlite3
from pathlib import Path
from threading import Lock
from typing import Any, Iterable

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA busy_timeout=5000;
CREATE TABLE IF NOT EXISTS events (
  event_id TEXT PRIMARY KEY, camera_id TEXT, edge_id TEXT, status TEXT,
  decision TEXT, score REAL, created_at TEXT, received_at TEXT, updated_at TEXT,
  event_dir TEXT, result_path TEXT, error_message TEXT
);
CREATE TABLE IF NOT EXISTS event_nodes (
  id INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT, camera_id TEXT, node_id TEXT,
  label TEXT, type TEXT, confidence REAL, bbox_json TEXT, crop_path TEXT, source TEXT
);
CREATE TABLE IF NOT EXISTS event_edges (
  id INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT, camera_id TEXT, subject_id TEXT,
  subject_label TEXT, relation TEXT, object_id TEXT, object_label TEXT, source TEXT,
  confidence REAL, evidence_json TEXT, novelty_score REAL, vlm_risk REAL
);
CREATE TABLE IF NOT EXISTS global_nodes (
  camera_id TEXT, node_label TEXT, count INTEGER DEFAULT 0, first_seen_at TEXT,
  last_seen_at TEXT, last_event_id TEXT, PRIMARY KEY(camera_id,node_label)
);
CREATE TABLE IF NOT EXISTS global_edges (
  camera_id TEXT, subject_label TEXT, relation TEXT, object_label TEXT, count INTEGER DEFAULT 0,
  first_seen_at TEXT, last_seen_at TEXT, last_event_id TEXT, normal_score REAL DEFAULT 0.0,
  PRIMARY KEY(camera_id,subject_label,relation,object_label)
);
CREATE TABLE IF NOT EXISTS edge_observations (
  id INTEGER PRIMARY KEY AUTOINCREMENT, camera_id TEXT, event_id TEXT, subject_label TEXT,
  relation TEXT, object_label TEXT, observed_at TEXT, novelty_score REAL
);
CREATE TABLE IF NOT EXISTS vlm_calls (
  id INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT, camera_id TEXT, provider TEXT, model TEXT,
  candidate_key TEXT, status TEXT, prompt_path TEXT, response_path TEXT, image_path TEXT,
  semantic_risk REAL, uncertainty TEXT, latency_ms REAL, error_message TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS edge_heartbeats (
  edge_id TEXT PRIMARY KEY, camera_id TEXT, status TEXT, payload_json TEXT, received_at TEXT
);

CREATE TABLE IF NOT EXISTS eval_runs (
  run_id TEXT PRIMARY KEY,
  dataset_name TEXT,
  source_type TEXT,
  status TEXT,
  started_at TEXT,
  finished_at TEXT,
  config_json TEXT
);
CREATE TABLE IF NOT EXISTS eval_event_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT,
  phase TEXT,
  metric_include INTEGER,
  event_id TEXT,
  camera_id TEXT,
  graph_namespace TEXT,
  video_id TEXT,
  video_relative_path TEXT,
  stream_order INTEGER,
  stream_time_sec REAL,
  frame_index INTEGER,
  video_timestamp_sec REAL,
  y_true INTEGER,
  y_true_name TEXT,
  task TEXT,
  scenario TEXT,
  decision TEXT,
  final_score REAL,
  graph_novelty_score REAL,
  semantic_relation_novelty REAL,
  vlm_semantic_risk REAL,
  temporal_persistence_score REAL,
  rule_risk_score REAL,
  confidence_risk REAL,
  uncertainty_risk REAL,
  result_path TEXT,
  created_at TEXT
);
CREATE TABLE IF NOT EXISTS eval_video_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT,
  video_id TEXT,
  video_relative_path TEXT,
  y_true INTEGER,
  y_true_name TEXT,
  task TEXT,
  scenario TEXT,
  num_events INTEGER,
  mean_score REAL,
  max_score REAL,
  topk_mean_score REAL,
  abnormal_event_ratio REAL,
  y_score REAL,
  y_pred INTEGER,
  aggregation TEXT,
  threshold REAL,
  created_at TEXT
);
"""

class Database:
    def __init__(self, path: str | Path):
        self.path=Path(path); self.path.parent.mkdir(parents=True, exist_ok=True); self.lock=Lock(); self.init()
    def connect(self):
        conn=sqlite3.connect(self.path, timeout=10, check_same_thread=False)
        conn.row_factory=sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;"); conn.execute("PRAGMA synchronous=NORMAL;"); conn.execute("PRAGMA busy_timeout=5000;")
        return conn
    def init(self):
        with self.lock:
            conn=self.connect(); conn.executescript(SCHEMA); conn.commit(); conn.close()
    def execute(self, sql: str, params: Iterable[Any]=()):
        with self.lock:
            conn=self.connect()
            try:
                cur=conn.execute(sql, tuple(params)); conn.commit(); return cur.lastrowid
            finally: conn.close()
    def query(self, sql: str, params: Iterable[Any]=()) -> list[dict[str, Any]]:
        conn=self.connect()
        try: return [dict(r) for r in conn.execute(sql, tuple(params)).fetchall()]
        finally: conn.close()
    def one(self, sql: str, params: Iterable[Any]=()) -> dict[str, Any] | None:
        rows=self.query(sql, params); return rows[0] if rows else None
