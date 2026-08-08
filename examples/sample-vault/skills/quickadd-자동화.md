---
title: QuickAdd 자동화
category: skills
tags: [obsidian, automation, quickadd, productivity, template]
sources: [gemini-session-2026-08-08]
created: 2026-08-08
updated: 2026-08-08
summary: QuickAdd 플러그인으로 허브 노트 1초 생성(Template)과 중단 없는 스피드 메모(Capture) 자동화를 구축하는 단계별 가이드.
---

# QuickAdd 자동화

Obsidian QuickAdd 플러그인을 활용한 두 가지 핵심 자동화. obsidian-wiki의 `/wiki-capture`가 AI 세션용이라면, QuickAdd는 일상 업무 중 즉석 메모용으로 상호 보완적.

## 설치

설정(Settings) → 커뮤니티 플러그인(Community plugins) → `QuickAdd` 검색 후 설치 및 활성화

## 1. Template — 허브 노트 1초 생성

### 설정 단계

1. QuickAdd 설정창 → 상단 입력창에 `새 허브노트 생성` 입력
2. 드롭다운에서 **Template** 선택 → **Add Choice** 클릭
3. ⚙️ Configure 클릭 후 세부 설정:

| 항목 | 설정값 |
|---|---|
| Template Path | `00_System/Templates/T_Hub_Note.md` |
| File Name Format | ON → `{{VALUE}}` (제목 입력 팝업) |
| Create in folder | ON → `10_Projects` |
| Open the created file | ON |

4. ⚡ Lightning Bolt 아이콘 클릭하여 활성화
5. 설정 → 단축키 → `QuickAdd: 새 허브노트 생성` 검색 → `Ctrl + Shift + H` 지정

### 실전 흐름

`Ctrl+Shift+H` → 팝업에 "2026_신축공사_설비계약" 입력 → Enter → `10_Projects/2026_신축공사_설비계약.md` 자동 생성 및 열림 → PDF/Excel 드래그&드롭

## 2. Capture — 스피드 메모 추가

### 설정 단계

1. QuickAdd 설정창 → `스피드 메모` 입력 → **Capture** 선택 → **Add Choice**
2. ⚙️ Configure:

| 항목 | 설정값 |
|---|---|
| 대상 노트 | 특정 허브 노트 지정 |
| Section heading | `📝 메모 & 회의록` |
| Capture format | `- [{{DATE:YYYY-MM-DD HH:mm}}] {{VALUE}}` |

3. ⚡ 활성화 후 단축키 `Alt + C` 지정

### 실전 흐름

`Alt+C` → 팝업에 메모 입력 → 대상 노트의 `📝 메모 & 회의록` 섹션에 타임라인 형태로 자동 추가 (노트를 직접 열지 않음)

## obsidian-wiki와의 역할 분담

| | QuickAdd | obsidian-wiki `/wiki-capture` |
|---|---|---|
| 용도 | 일상 업무 중 즉석 메모 | AI 에이전트 세션의 인사이트 보존 |
| 입력 | 사용자가 직접 타이핑 | AI가 대화에서 자동 추출 |
| 속도 | 단축키 1초 | `--quick` 모드 60초 |

## 관련 개념

- [[허브-노트-패턴]]
- [[dataview-카드뷰-대시보드]]
- [[obsidian-추천-플러그인]]
