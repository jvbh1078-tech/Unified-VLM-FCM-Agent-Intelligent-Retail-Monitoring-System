# Unified VLM-FCM Agent

## Intelligent Retail Monitoring System for Embedded Environments

AI와 VLM(Vision-Language Model)을 활용한 지능형 매장 모니터링 시스템입니다.

기존의 객체 탐지 방식은 영상 속에 어떤 사람이 있는지, 어떤 물체가 있는지를 확인하는 데에는 효과적이지만, 객체 사이의 관계나 전체적인 상황을 이해하는 데에는 한계가 있습니다.

이 프로젝트에서는 **YOLO 기반 객체 탐지 → 관심 영역 추출 → Event Graph 구성 → VLM 분석**의 과정을 통해 매장 내에서 발생하는 상황과 객체 간 관계를 분석하는 것을 목표로 합니다.

---

## Project Overview

카메라에서 입력된 영상에서 객체를 탐지하고, 탐지된 객체의 위치와 관계를 Graph 형태로 구성한 후 VLM을 활용하여 상황을 분석합니다.

### Processing Pipeline

```text
Camera
  ↓
YOLO Object Detection
  ↓
Bounding Box
  ↓
Crop
  ↓
Event Graph / Semantic Graph
  ↓
VLM Analysis
  ↓
Situation & Relationship Inference
  ↓
Event Evaluation
Main Features
YOLO 기반 객체 탐지
Bounding Box 기반 객체 영역 추출
객체 간 관계 분석
Event Graph 구성
Semantic Graph 구성
Global Graph 기반 이벤트 관리
VLM 기반 상황 및 관계 분석
이벤트 평가 및 Scoring
WebSocket 기반 데이터 처리
웹 Dashboard를 통한 분석 결과 확인
Gemini / Ollama / OFF 등 VLM Provider 구조 분리
Technology Stack
AI / Vision
YOLO
VLM (Vision-Language Model)
Object Detection
Graph-based Reasoning
Backend
Python
FastAPI
WebSocket
Frontend
HTML
CSS
JavaScript
Configuration
YAML
Environment Variables
Project Structure
.
├── app/
│   ├── core/
│   ├── routers/
│   ├── services/
│   │   ├── evaluation/
│   │   ├── event_graph/
│   │   ├── event_ingest/
│   │   ├── global_graph/
│   │   ├── scoring/
│   │   ├── vlm/
│   │   └── websocket/
│   ├── static/
│   ├── templates/
│   └── main.py
│
├── configs/
│   ├── relation_vocabulary.yaml
│   └── server_config.yaml
│
├── README.md
└── .gitignore
VLM Architecture

VLM 기능은 특정 모델에 종속되지 않도록 Provider 구조로 분리했습니다.

현재 프로젝트에서는 다음과 같은 Provider 구조를 사용합니다.

VLM
├── Gemini
├── Ollama
└── OFF

이를 통해 VLM 모델을 변경하더라도 전체 시스템 구조를 크게 수정하지 않고 사용할 수 있도록 구성했습니다.

Graph-based Situation Analysis

단순히 객체를 탐지하는 것에서 끝내지 않고 탐지된 객체들의 위치와 관계를 Graph 형태로 표현합니다.

이를 통해 다음과 같은 정보를 구조화합니다.

객체(Entity)
객체 위치
객체 간 거리 및 공간적 관계
객체 간 관계
이벤트 정보
시간에 따른 이벤트 변화

이렇게 구성된 정보를 VLM 분석 과정에서 활용하여 영상 속 상황을 보다 구조적으로 해석할 수 있도록 설계했습니다.

Dashboard

웹 기반 Dashboard를 통해 처리된 이벤트와 Graph 정보를 확인할 수 있도록 구성했습니다.

Dashboard에서는 시스템에서 처리된 이벤트와 분석 결과를 확인하고, Graph 기반으로 객체 및 관계 정보를 시각적으로 확인할 수 있습니다.

Project Goal

이 프로젝트의 목표는 단순한 객체 탐지를 넘어 영상 속 여러 객체의 관계와 상황을 종합적으로 이해할 수 있는 지능형 Retail Monitoring Agent를 구현하는 것입니다.

향후에는 실제 매장 환경에서 발생할 수 있는 다양한 이벤트를 대상으로 테스트하고, AI 모델의 정확도뿐만 아니라 실제 서비스 환경에서의 처리 속도와 안정성까지 고려하는 방향으로 개발을 진행할 예정입니다.

Development Status

현재 프로젝트는 졸업 프로젝트를 기반으로 개발 중인 연구 및 프로토타입 시스템입니다.

주요 기능을 지속적으로 개발하고 있으며, 실제 환경에서의 테스트와 평가를 통해 시스템의 완성도를 높이는 것을 목표로 하고 있습니다.

Repository

GitHub:

https://github.com/jvbh1078-tech/Unified-VLM-FCM-Agent-Intelligent-Retail-Monitoring-System
