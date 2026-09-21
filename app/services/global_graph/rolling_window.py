from __future__ import annotations
from datetime import datetime, timezone, timedelta
from app.core.db import Database

class RollingWindow:
    def __init__(self, db: Database, seconds: int=300):
        self.db=db; self.seconds=seconds
    def persistence_score(self, camera_id: str, s: str, r: str, o: str) -> float:
        since=(datetime.now(timezone.utc)-timedelta(seconds=self.seconds)).isoformat()
        row=self.db.one("SELECT COUNT(*) AS n FROM edge_observations WHERE camera_id=? AND subject_label=? AND relation=? AND object_label=? AND observed_at>=?", (camera_id,s,r,o,since))
        return min(1.0, int(row["n"] if row else 0)/5.0)
