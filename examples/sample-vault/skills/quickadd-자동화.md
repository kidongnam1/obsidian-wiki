---
title: QuickAdd 자동화
category: skills
tags: [obsidian, automation, quickadd, productivity, template, capture]
sources: [gemini-session-2026-08-08]
created: 2026-08-08
updated: 2026-08-08
summary: QuickAdd 플러그인으로 허브 노트 1초 생성(Template)과 중단 없는 스피드 메모(Capture) 자동화를 구축하는 단계별 가이드. 상세 설정 포함.
---

# QuickAdd 자동화

Obsidian QuickAdd 플러그인을 활용한 두 가지 핵심 자동화. obsidian-wiki의 `/wiki-capture`가 AI 세션용이라면, QuickAdd는 일상 업무 중 즉석 메모용으로 상호 보완적.

## 설치

설정(Settings) → 커뮤니티 플러그인(Community plugins) → `QuickAdd` 검색 후 설치 및 활성화

## 1. Template — 허브 노트 1초 생성

### 사전 준비

허브 노트 템플릿 파일을 `00_System/Templates/T_Hub_Note.md`에 준비. QuickAdd 기본 구문 사용 시 `{{title}}`을 `{{VALUE}}`로 변경하면 파일 생성 시 제목이 자동 입력됨.

### 설정 단계

1. QuickAdd 설정창 → 상단 입력창에 `새 허브노트 생성` 입력
2. 드롭다운에서 **Template** 선택 → **Add Choice** 클릭
3. ⚙️ Configure 클릭 후 세부 설정:

| 항목 | 설정값 | 설명 |
|---|---|---|
| Template Path | `00_System/Templates/T_Hub_Note.md` | 허브노트 템플릿 지정 |
| File Name Format | ON → `{{VALUE}}` | 실행 시 제목 입력 팝업 표시 |
| Create in folder | ON → `10_Projects` | 생성 위치 자동 지정 |
| Open the created file | ON | 노트 생성 후 즉시 열기 |

4. ⚡ Lightning Bolt 아이콘 클릭하여 단축키 등록 활성화
5. 설정 → 단축키 → `QuickAdd: 새 허브노트 생성` 검색 → `Ctrl + Shift + H` 지정

### 실전 흐름

`Ctrl+Shift+H` → 팝업에 "2026_신축공사_설비계약" 입력 → Enter → `10_Projects/2026_신축공사_설비계약.md` 자동 생성 및 열림 → PDF/Excel 드래그&드롭

## 2. Capture — 스피드 메모 추가

노트를 찾아서 열고 스크롤 내려 위치를 잡고 타자를 치는 4~5단계를 **단축키 1회 + 텍스트 입력 1회(2단계)**로 압축.

### 설정 단계

1. QuickAdd 설정창 → `허브노트에 빠른 메모 추가` 입력 → **Capture** 선택 → **Add Choice**
2. ⚙️ Configure:

| 항목 | 설정값 | 설명 |
|---|---|---|
| Capture to file | ON | 파일에 덧붙이기 활성화 |
| Target File Path | `10_Projects/메인_프로젝트_허브.md` | 대상 허브 노트 경로 (비우면 매번 선택 팝업) |
| Write to end of file | OFF | 파일 끝이 아닌 특정 섹션에 삽입 |
| Insert after section | ON | 섹션 헤딩 아래에 삽입 |
| Section heading | `📝 메모 & 회의록` | 삽입 위치 지정 |
| Capture format | ON → `- [{{date:YYYY-MM-DD HH:mm}}] {{VALUE}}` | 타임스탬프 + 입력 내용 |

3. ⚡ 활성화 후 단축키 `Alt + C` 지정

### 실전 흐름

엑셀 작업이나 PDF 읽기 중 아이디어 발생 → `Alt+C` → 팝업에 메모 입력:
- 예시 1: `설비 업체 견적서 재요청 필요 (다음 주 화요일까지)`
- 예시 2: `[[2026_변경견적서_v2.xlsx]] 파일 검토 완료`

Enter → 현재 화면 유지한 채 대상 허브 노트의 `## 📝 메모 & 회의록` 섹션에 자동 기록:

```
- [2026-08-08 14:32] 설비 업체 견적서 재요청 필요 (다음 주 화요일까지)
- [2026-08-08 15:10] [[2026_변경견적서_v2.xlsx]] 파일 검토 완료
```

## obsidian-wiki와의 역할 분담

| | QuickAdd | obsidian-wiki `/wiki-capture` |
|---|---|---|
| 용도 | 일상 업무 중 즉석 메모 | AI 에이전트 세션의 인사이트 보존 |
| 입력 | 사용자가 직접 타이핑 | AI가 대화에서 자동 추출 |
| 속도 | 단축키 1초 | `--quick` 모드 60초 |
| 대상 | 허브 노트 특정 섹션 | 위키 전체 (카테고리 자동 분류) |

## 관련 개념

- [[허브-노트-패턴]]
- [[dataview-카드뷰-대시보드]]
- [[obsidian-추천-플러그인]]
