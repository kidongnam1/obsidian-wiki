---
title: Obsidian 추천 플러그인
category: references
tags: [obsidian, plugins, productivity, pkm]
sources: [gemini-session-2026-08-08]
created: 2026-08-08
updated: 2026-08-08
summary: Obsidian 세컨드 브레인 구축에 필수/추천되는 커뮤니티 플러그인 목록과 각각의 역할.
---

# Obsidian 추천 플러그인

## 필수 플러그인

| 플러그인 | 역할 | 비고 |
|---|---|---|
| **Dataview** | 프론트매터 메타데이터 쿼리, 동적 테이블/리스트 생성 | [[dataview-카드뷰-대시보드]] 참고 |
| **QuickAdd** | 단축키 기반 노트 생성/메모 캡처 자동화 | [[quickadd-자동화]] 참고 |
| **Omnisearch** | 볼트 전체 통합 검색 (비마크다운 파일 포함) | Text Extractor와 조합 |
| **Text Extractor** | PDF, Excel, 이미지 내부 텍스트 추출 → Omnisearch에 공급 | Omnisearch와 조합 |

## 강력 추천 플러그인

| 플러그인 | 역할 | 비고 |
|---|---|---|
| **PDF++** | PDF 하이라이트 ↔ 마크다운 양방향 실시간 연결 | [[obsidian-비마크다운-파일-연관]] 참고 |
| **Templater** | 고급 템플릿 구문 (날짜, 조건, 커서 위치 지정) | QuickAdd와 조합 가능 |
| **Obsidian Git** | 볼트 자동 백업을 Git 저장소로 | 버전 관리 + 크로스 디바이스 동기화 |
| **Graph Analysis** | 강화된 그래프 뷰, 연결 분석 | 지식 네트워크 시각화 |
| **Minimal Theme** | 카드 뷰, 커버 이미지 등 시각화 CSS 지원 | [[dataview-카드뷰-대시보드]] 참고 |

## 상황별 추천

| 플러그인 | 역할 | 적용 상황 |
|---|---|---|
| **CSV Editor** | CSV 파일을 인터랙티브 표로 편집 | Excel → CSV 변환 후 Obsidian 내 편집 |
| **Pandoc** | Word/HWP를 마크다운으로 자동 변환 | 대량 문서 마이그레이션 시 |
| **Calendar** | 일간/주간 노트 캘린더 뷰 | 저널링 워크플로우에 활용 |
| **Kanban** | 칸반 보드 생성 | 프로젝트 태스크 관리 |

## obsidian-wiki 전용 추천 (kepano/obsidian-skills)

| 스킬 | 역할 |
|---|---|
| `obsidian-markdown` | Obsidian 마크다운 구문 (위키링크, 콜아웃, 임베드) |
| `obsidian-bases` | `.base` 파일 (데이터베이스형 노트 뷰) |
| `json-canvas` | `.canvas` 파일 (비주얼 마인드맵) |
| `defuddle` | 웹 페이지에서 깔끔한 마크다운 추출 |

## 관련 개념

- [[obsidian-비마크다운-파일-연관]]
- [[quickadd-자동화]]
- [[dataview-카드뷰-대시보드]]
- [[허브-노트-패턴]]
