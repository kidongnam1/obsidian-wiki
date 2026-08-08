---
title: Vault Owner Conventions
---

# Vault Owner Conventions

This file defines owner-specific conventions that override framework defaults for all skills.

## Domain Context

이 볼트는 SSD에 분산된 업무 문서(Excel, PDF, Word, HWP)를 통합 관리하는 세컨드 브레인입니다.

### 주요 업무 영역

- 충전소 사업 프로젝트
- 물류 관리
- 자산 관리
- 법규/표준 양식 참조

## Organizational Convention: PARA Framework

이 볼트의 소유자는 PARA 프레임워크를 사용합니다. 인제스트 시 아래 분류 기준을 참고하세요:

| PARA 분류 | 기준 | obsidian-wiki 매핑 |
|---|---|---|
| Projects | 마감이 있는 명확한 사업/공사 | `projects/` |
| Areas | 마감 없이 지속 관리하는 영역 | `concepts/` 또는 `entities/` (성격에 따라) |
| Resources | 참고 법규, 표준 양식, 연구 자료 | `references/` |
| Archive | 완료된 옛 자료 | `_archives/` |

## Hub Note Convention

프로젝트 페이지를 작성할 때 허브 노트 패턴을 따르세요:

1. 연관 외부 자료를 `[[파일명.확장자]]` 위키링크로 연결
2. 핵심 요약/인사이트를 별도 섹션에 기록
3. 관련 프로젝트/개념 노트를 교차 참조
4. 실행 항목은 체크박스(`- [ ]`)로 관리

## File Handling

- 비마크다운 파일(PDF, Excel, HWP)은 위키링크로 참조
- PDF는 `[[문서.pdf#page=N]]` 형태로 페이지 지정 가능
- 첨부 파일 기본 경로: `01_Attachments/`

## Writing Style

- 한국어 우선, 기술 용어는 영문 병기 가능
- 간결하고 실용적인 톤
- 업무 맥락(프로젝트명, 관련 부서)을 구체적으로 기록

## Ingest Preferences

- 회의록, 업무 로그는 `journal/`에 배치
- 기술 절차/노하우는 `skills/`에 배치
- 법규, 스펙, API 문서는 `references/`에 배치
- 여러 개념을 연결하는 분석은 `synthesis/`에 배치

## Tag Conventions

- 프로젝트 태그: `project/<프로젝트명>`
- 영역 태그: `area/<영역명>`
- 상태 태그: `status/active`, `status/completed`, `status/on-hold`
