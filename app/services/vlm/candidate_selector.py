PERSON_LABELS = {"person", "human"}
DEFAULT_SAFETY_LABELS = {
    "person", "human", "fire", "smoke", "fence", "machine", "forklift", "vehicle", "car",
    "floor", "ground", "door", "bag", "backpack", "knife", "bottle", "helmet", "chair", "ladder"
}
PRIORITY_GEOMETRY = {"near", "overlap", "touching_candidate", "holding_candidate", "inside", "above", "below"}

class CandidateSelector:
    def __init__(self, cfg: dict):
        self.cfg = cfg or {}
        self.safety_labels = set(self.cfg.get("safety_labels") or DEFAULT_SAFETY_LABELS)

    def _flag(self, label: str, labels: set[str]) -> float:
        return 1.0 if str(label).lower() in labels else 0.0

    def select(self, novelty: dict, event_graph: dict) -> list[dict]:
        max_n = int(self.cfg.get("max_candidates_per_event", 3))
        min_novelty = float(self.cfg.get("min_novelty_for_vlm", self.cfg.get("min_novelty", 0.45)))
        min_priority = float(self.cfg.get("min_priority", 0.0))
        edge_by_key = {f"{e['subject_label']}|{e['relation']}|{e['object_label']}": e for e in event_graph.get("edges", [])}
        nov_by_key = {n["key"]: n for n in novelty.get("edges", [])}
        candidates = []
        for key, e in edge_by_key.items():
            n = nov_by_key.get(key, {})
            nov = float(n.get("novelty_score", 0.0) or 0.0)
            s = str(e.get("subject_label", "")).lower()
            o = str(e.get("object_label", "")).lower()
            rel = str(e.get("relation", ""))
            person_related = max(self._flag(s, PERSON_LABELS), self._flag(o, PERSON_LABELS))
            safety_related = max(self._flag(s, self.safety_labels), self._flag(o, self.safety_labels))
            geometry_priority = 1.0 if rel in PRIORITY_GEOMETRY else 0.3
            confidence = float(e.get("confidence", 1.0) or 1.0)
            low_conf = max(0.0, 1.0 - confidence)
            # A balanced priority for semantic relation refinement. It still honors novelty,
            # but does not ignore obvious safety pairs before they become novel.
            priority_score = (
                0.30 * nov +
                0.25 * person_related +
                0.20 * safety_related +
                0.15 * geometry_priority +
                0.10 * low_conf
            )
            if nov < min_novelty and priority_score < min_priority:
                continue
            item = {
                **n,
                "key": key,
                "subject": e.get("subject_label"),
                "relation": e.get("relation"),
                "object": e.get("object_label"),
                "previous_count": n.get("previous_count", 0),
                "novelty_score": nov,
                "is_new": bool(n.get("is_new", False)),
                "priority": 1 - person_related,
                "priority_score": round(priority_score, 4),
                "evidence_path": e.get("evidence_path"),
                "evidence_url": e.get("evidence_url"),
                "event_subject_id": e.get("subject_id"),
                "event_object_id": e.get("object_id"),
                "geometry_confidence": confidence,
            }
            candidates.append(item)
        candidates.sort(key=lambda x: (x.get("priority", 1), -float(x.get("priority_score", 0)), -float(x.get("novelty_score", 0))))
        return candidates[:max_n]
