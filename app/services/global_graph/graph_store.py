from __future__ import annotations
from app.core.db import Database
from app.core.time import utc_now

class GraphStore:
    def __init__(self, db: Database):
        self.db=db
    def camera_event_count(self, camera_id: str) -> int:
        row=self.db.one("SELECT COUNT(*) AS n FROM events WHERE camera_id=? AND status='done'", (camera_id,))
        return int(row["n"] if row else 0)
    def node_count(self, camera_id: str, label: str) -> int:
        row=self.db.one("SELECT count FROM global_nodes WHERE camera_id=? AND node_label=?", (camera_id,label))
        return int(row["count"] if row else 0)
    def edge_count(self, camera_id: str, s: str, r: str, o: str) -> int:
        row=self.db.one("SELECT count FROM global_edges WHERE camera_id=? AND subject_label=? AND relation=? AND object_label=?", (camera_id,s,r,o))
        return int(row["count"] if row else 0)
    def update_after_event(self, event_id: str, camera_id: str, graph: dict, edge_novelties: list[dict]):
        now=utc_now()
        for n in graph.get("nodes", []):
            label=n["label"]; exists=self.node_count(camera_id,label)
            if exists:
                self.db.execute("UPDATE global_nodes SET count=count+1,last_seen_at=?,last_event_id=? WHERE camera_id=? AND node_label=?", (now,event_id,camera_id,label))
            else:
                self.db.execute("INSERT INTO global_nodes(camera_id,node_label,count,first_seen_at,last_seen_at,last_event_id) VALUES(?,?,?,?,?,?)", (camera_id,label,1,now,now,event_id))
        novelty_by_key={x.get("key"): x.get("novelty_score",0.0) for x in edge_novelties}
        for e in graph.get("edges", []):
            s,r,o=e["subject_label"],e["relation"],e["object_label"]
            exists=self.edge_count(camera_id,s,r,o)
            if exists:
                self.db.execute("UPDATE global_edges SET count=count+1,last_seen_at=?,last_event_id=? WHERE camera_id=? AND subject_label=? AND relation=? AND object_label=?", (now,event_id,camera_id,s,r,o))
            else:
                self.db.execute("INSERT INTO global_edges(camera_id,subject_label,relation,object_label,count,first_seen_at,last_seen_at,last_event_id,normal_score) VALUES(?,?,?,?,?,?,?,?,?)", (camera_id,s,r,o,1,now,now,event_id,0.0))
            self.db.execute("INSERT INTO edge_observations(camera_id,event_id,subject_label,relation,object_label,observed_at,novelty_score) VALUES(?,?,?,?,?,?,?)", (camera_id,event_id,s,r,o,now,float(novelty_by_key.get(f'{s}|{r}|{o}',0.0))))
    def top_edges(self, camera_id: str, limit: int=50):
        return self.db.query("SELECT * FROM global_edges WHERE camera_id=? ORDER BY count DESC LIMIT ?", (camera_id,limit))
    def rare_edges(self, camera_id: str, limit: int=50):
        return self.db.query("SELECT * FROM global_edges WHERE camera_id=? ORDER BY count ASC,last_seen_at DESC LIMIT ?", (camera_id,limit))
