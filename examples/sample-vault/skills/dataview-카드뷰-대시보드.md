---
title: Dataview 카드 뷰 대시보드
category: skills
tags: [obsidian, dataview, dashboard, visualization, minimal-theme]
sources: [gemini-session-2026-08-08]
created: 2026-08-08
updated: 2026-08-08
summary: DataviewJS로 프로젝트 메모를 실시간 모니터링하고, Minimal 테마의 CSS 카드 뷰로 시각화하는 대시보드 구축법.
---

# Dataview 카드 뷰 대시보드

## DataviewJS — 최근 캡처 메모 모니터링

각 프로젝트 허브 노트에 쌓이는 캡처 메모를 대시보드 한곳에서 실시간으로 확인하는 기능.

## Minimal 테마 카드 뷰

Minimal 테마 설치 후 대시보드 노트 상단에 `cssclasses`를 부여하면 밋밋한 표가 격자형 카드로 변환된다.

```yaml
---
cssclasses:
  - cards
  - cards-cover
  - cards-1-1
---
```

| cssclass | 효과 |
|---|---|
| `cards` | Dataview 표를 카드 레이아웃으로 전환 |
| `cards-cover` | 이미지를 카드 커버로 표시 |
| `cards-1-1` | 1:1 비율 카드 |

## 관련 개념

- [[quickadd-자동화]]
- [[허브-노트-패턴]]
