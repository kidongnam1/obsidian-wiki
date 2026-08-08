---
title: QuickAdd 자동화
category: skills
tags: [obsidian, automation, quickadd, productivity]
sources: [gemini-session-2026-08-08]
created: 2026-08-08
updated: 2026-08-08
summary: QuickAdd 플러그인으로 허브 노트 1초 생성(Template)과 중단 없는 스피드 메모(Capture) 자동화를 구축하는 방법.
---

# QuickAdd 자동화

Obsidian QuickAdd 플러그인을 활용한 두 가지 핵심 자동화.

## 1. Template — 허브 노트 1초 생성

| 항목 | 설정값 |
|---|---|
| 타입 | Template |
| 템플릿 경로 | `00_System/Templates/T_Hub_Note.md` |
| 생성 폴더 | `10_Projects` |
| 단축키 | `Ctrl + Shift + H` |

**흐름:** 단축키 → 제목 팝업창 → 허브 노트 자동 생성

## 2. Capture — 스피드 메모 추가

| 항목 | 설정값 |
|---|---|
| 타입 | Capture |
| 대상 노트 | 특정 허브 노트 지정 |
| Section heading | `📝 메모 & 회의록` |
| 단축키 | `Alt + C` |
| 포맷 | `- [{{DATE:YYYY-MM-DD HH:mm}}] {{VALUE}}` |

**흐름:** 단축키 → 팝업에 메모 입력 → 대상 노트에 타임라인 형태로 자동 추가 (노트를 직접 열지 않음)

## 관련 개념

- [[허브-노트-패턴]]
- [[dataview-카드뷰-대시보드]]
