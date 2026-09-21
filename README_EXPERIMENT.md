# GPU Server v5.5 — VLM-refined Graph + Dataset Scenario Evaluation

이 버전은 Edge Server `v4.5 dataset_scenario_replay`에서 전송하는 event package를 받아 다음 기능을 수행합니다.

## 핵심 기능

1. **Edge source_meta 기반 experiment context 인식**
   - `run_id`, `phase`, `metric_include`, `video_id`, `binary_label`, `task`, `scenario`, `stream_time_sec` 등을 읽습니다.

2. **phase-aware normality graph update**
   - `phase=warmup`: Global Normality Graph 업데이트 허용, metric 제외
   - `phase=eval`: Global Normality Graph freeze, metric 포함

3. **run_id별 graph namespace 분리**
   - 기본값: `graph_namespace = {run_id}:{camera_id}`
   - 실험 run 간 normality graph가 섞이지 않습니다.

4. **VLM-refined object-relation graph**
   - YOLO/bbox geometry로 provisional relation을 생성합니다.
   - novelty / safety priority가 높은 relation 후보만 VLM에 전달합니다.
   - VLM이 controlled vocabulary 기반 semantic relation을 반환합니다.
   - `semantic_event_graph.json`을 별도로 저장합니다.

5. **evaluation logging**
   - `storage/eval_runs/{run_id}/event_results.jsonl`
   - DB table: `eval_runs`, `eval_event_results`, `eval_video_results`

6. **video-level aggregation & metrics**
   - 웹 API 또는 CLI로 `AUROC`, `Average Precision`, `Accuracy`, `Precision`, `Recall`, `F1` 계산 가능

7. **Experiment Dashboard**
   - `/dashboard/eval`
   - run별 실험 상태, score timeline, latest image, event graph, semantic relation, metrics 확인 가능

## 실행

```bash
./run_server.sh ollama
```

또는 Gemini 사용:

```bash
export GEMINI_API_KEY="..."
./run_server.sh gemini
```

VLM을 끄고 빠르게 파이프라인 테스트:

```bash
./run_server.sh off
```

## 주요 화면

- 기본 대시보드: `http://<GPU_SERVER>:8008/dashboard`
- 실험 대시보드: `http://<GPU_SERVER>:8008/dashboard/eval`
- Global Graph: `http://<GPU_SERVER>:8008/dashboard/global-graph`

## Edge Server에서 전달해야 하는 source_meta

Edge event package의 `metadata.json > source_meta`에 다음 필드가 들어오면 GPU Server가 실험 모드로 인식합니다.

```json
{
  "source_type": "dataset_scenario_replay",
  "is_replay": true,
  "run_id": "stream_eval_001",
  "phase": "warmup",
  "metric_include": false,
  "dataset_name": "aihub_safety_subset_v1",
  "video_id": "intrusion_normal_001",
  "video_relative_path": "normal/rgb/intrusion/intrusion_normal_001.mp4",
  "binary_label": 0,
  "binary_name": "normal",
  "task": "intrusion",
  "scenario": "normal",
  "stream_time_sec": 120.0,
  "frame_index": 120,
  "video_timestamp_sec": 4.0,
  "sample_fps": 1.0,
  "send_policy": "all_sampled"
}
```

## Metrics 생성

웹에서 `/dashboard/eval`의 `Aggregate & metrics` 버튼을 눌러도 되고, CLI로도 가능합니다.

```bash
python tools/finalize_eval_run.py \
  --run-id stream_eval_001 \
  --aggregation topk_mean \
  --threshold 0.5
```

생성 결과:

```text
storage/eval_runs/stream_eval_001/
├── event_results.jsonl
├── video_results.csv
└── metrics.json
```

## VLM relation refinement 출력

각 event 폴더에 다음이 저장됩니다.

```text
result.json
semantic_event_graph.json
semantic_novelty.json
vlm_relation_refinement.json
vlm/relation_prompts/*.txt
vlm/relation_responses/*.json
```

VLM 출력 schema는 다음 형태입니다.

```json
{
  "subject_id": "person_1",
  "object_id": "floor_region_1",
  "geometry_relation": "near",
  "relation_supported": true,
  "semantic_relation": "lying_on",
  "relation_confidence": 0.86,
  "semantic_risk": 0.91,
  "safety_risk_type": "fall",
  "uncertainty": "medium",
  "evidence": ["The person appears horizontally positioned on the floor region."],
  "recommendation": "ABNORMAL"
}
```

## 설정 파일

주요 설정 위치:

```text
configs/server_config.yaml
```

중요 설정:

```yaml
vlm:
  provider: "ollama"
  max_candidates_per_event: 3
  min_novelty_for_vlm: 0.35
  min_priority: 0.45

vlm_relation_refinement:
  enabled: true

evaluation:
  enabled: true
  graph_namespace_policy: "run_id_camera"
  phase_policy:
    warmup:
      update_global_graph: true
      metric_include: false
      force_decision: "WATCH"
    eval:
      update_global_graph: false
      metric_include: true

global_graph:
  update_geometry_edges: true
  update_semantic_edges: true
```

## 주의

- `phase=eval`에서는 기본적으로 Global Graph가 업데이트되지 않습니다.
- 실험별 normality graph는 `run_id:camera_id` namespace로 분리됩니다.
- VLM relation refinement는 모든 관계가 아니라, novelty/safety priority가 높은 관계 후보만 수행합니다.
