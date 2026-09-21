from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any

_DATASET_SOURCE_TYPES = {"dataset_replay", "dataset_scenario_replay", "edge_dataset_replay"}

@dataclass
class EvalContext:
    enabled: bool
    source_type: str
    is_replay: bool
    run_id: str | None
    phase: str
    metric_include: bool
    dataset_name: str | None
    scenario_manifest: str | None
    stream_order: int | None
    stream_time_start_sec: float | None
    stream_time_sec: float | None
    injection_type: str | None
    video_id: str | None
    video_name: str | None
    video_relative_path: str | None
    video_repeat_index: int | None
    y_true: int | None
    y_true_name: str | None
    modality: str | None
    task: str | None
    scenario: str | None
    split: str | None
    frame_index: int | None
    video_timestamp_sec: float | None
    sample_fps: float | None
    send_policy: str | None
    graph_namespace: str | None
    update_global_graph: bool
    force_decision: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _as_bool(v: Any, default: bool = False) -> bool:
    if isinstance(v, bool):
        return v
    if v is None:
        return default
    if isinstance(v, (int, float)):
        return bool(v)
    return str(v).strip().lower() in {"1", "true", "yes", "y", "on"}


def _as_int(v: Any) -> int | None:
    try:
        if v is None or v == "": return None
        return int(float(v))
    except Exception:
        return None


def _as_float(v: Any) -> float | None:
    try:
        if v is None or v == "": return None
        return float(v)
    except Exception:
        return None


def build_eval_context(meta: dict[str, Any], camera_id: str, settings) -> EvalContext:
    source_meta = meta.get("source_meta") or {}
    source_type = str(source_meta.get("source_type") or meta.get("source_type") or "camera")
    is_replay = _as_bool(source_meta.get("is_replay"), source_type in _DATASET_SOURCE_TYPES)
    run_id = source_meta.get("run_id") or None
    phase = str(source_meta.get("phase") or ("eval" if is_replay else "camera")).lower()

    eval_enabled = bool(settings.get("evaluation.enabled", True)) and (is_replay or bool(run_id))
    metric_include = _as_bool(source_meta.get("metric_include"), phase == "eval")
    if phase == "warmup":
        metric_include = False

    y_true = source_meta.get("binary_label")
    if y_true is None:
        y_true = source_meta.get("y_true")
    y_true = _as_int(y_true)
    y_true_name = source_meta.get("binary_name") or source_meta.get("y_true_name")

    graph_policy = str(settings.get("evaluation.graph_namespace_policy", "run_id_camera"))
    graph_namespace = None
    if eval_enabled:
        if graph_policy == "run_id_camera" and run_id:
            graph_namespace = f"{run_id}:{camera_id}"
        elif graph_policy == "run_id" and run_id:
            graph_namespace = str(run_id)
        elif graph_policy == "camera":
            graph_namespace = camera_id
        else:
            graph_namespace = f"{run_id or 'eval'}:{camera_id}"

    default_update = bool(settings.get("evaluation.default_update_global_graph", True))
    update_global_graph = default_update
    force_decision = None
    if eval_enabled:
        phase_cfg = settings.get(f"evaluation.phase_policy.{phase}", {}) or {}
        update_global_graph = _as_bool(phase_cfg.get("update_global_graph"), phase == "warmup")
        force_decision = phase_cfg.get("force_decision")
        if phase == "eval":
            update_global_graph = _as_bool(phase_cfg.get("update_global_graph"), False)

    return EvalContext(
        enabled=eval_enabled,
        source_type=source_type,
        is_replay=is_replay,
        run_id=str(run_id) if run_id else None,
        phase=phase,
        metric_include=metric_include,
        dataset_name=source_meta.get("dataset_name"),
        scenario_manifest=source_meta.get("scenario_manifest"),
        stream_order=_as_int(source_meta.get("stream_order")),
        stream_time_start_sec=_as_float(source_meta.get("stream_time_start_sec")),
        stream_time_sec=_as_float(source_meta.get("stream_time_sec")),
        injection_type=source_meta.get("injection_type"),
        video_id=source_meta.get("video_id"),
        video_name=source_meta.get("video_name"),
        video_relative_path=source_meta.get("video_relative_path") or source_meta.get("relative_path"),
        video_repeat_index=_as_int(source_meta.get("video_repeat_index")),
        y_true=y_true,
        y_true_name=str(y_true_name) if y_true_name is not None else None,
        modality=source_meta.get("modality"),
        task=source_meta.get("task"),
        scenario=source_meta.get("scenario"),
        split=source_meta.get("split"),
        frame_index=_as_int(source_meta.get("frame_index")),
        video_timestamp_sec=_as_float(source_meta.get("video_timestamp_sec")),
        sample_fps=_as_float(source_meta.get("sample_fps")),
        send_policy=source_meta.get("send_policy"),
        graph_namespace=graph_namespace,
        update_global_graph=update_global_graph,
        force_decision=str(force_decision) if force_decision else None,
    )
