---
title: Obsidian 비마크다운 파일 연관
category: references
tags: [obsidian, pdf, excel, hwp, word, file-management]
sources: [gemini-session-2026-08-08]
created: 2026-08-08
updated: 2026-08-08
summary: PDF, Excel, Word, HWP 등 비마크다운 파일을 Obsidian에서 연결하고 검색하는 방법 레퍼런스.
---

# Obsidian 비마크다운 파일 연관

## 파일 유형별 연관 방법

### PDF

- `[[문서명.pdf]]` — 파일 링크
- `[[문서명.pdf#page=3]]` — 특정 페이지 직접 링크
- 내장 뷰어로 Obsidian 안에서 즉시 열람 가능

### Excel / Word

- 볼트 내 포함 시 클릭 한 번으로 로컬 프로그램(엑셀/워드)에서 실행
- `[[보고서.xlsx]]` 형태로 위키링크 연결

### HWP (한글)

- 동일하게 `[[문서.hwp]]`로 링크
- 클릭 시 한컴오피스에서 실행

## 첨부 파일 자동 수거

옵시디안 설정:
- **파일 및 링크** → **새 첨부 파일의 기본 위치** → `01_Attachments` 폴더 지정
- 드래그&드롭하는 모든 외부 파일이 해당 폴더로 자동 수거
- 볼트 루트가 깨끗하게 유지됨

## 전문 검색 (Full-Text Search)

**Omnisearch** + **Text Extractor** 커뮤니티 플러그인 설치 시:
- PDF 내부 텍스트 검색 가능
- Excel 내부 텍스트 검색 가능
- Obsidian 전체 검색창에서 통합 검색

## 관련 개념

- [[허브-노트-패턴]]
- [[para-framework]]
