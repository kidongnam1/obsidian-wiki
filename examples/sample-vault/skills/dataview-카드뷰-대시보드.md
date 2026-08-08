---
title: Dataview 카드 뷰 대시보드
category: skills
tags: [obsidian, dataview, dataviewjs, dashboard, visualization, minimal-theme]
sources: [gemini-session-2026-08-08]
created: 2026-08-08
updated: 2026-08-08
summary: DataviewJS로 프로젝트 메모를 실시간 모니터링하고, Minimal 테마의 CSS 카드 뷰로 시각화하는 대시보드 구축법. 코드 포함.
---

# Dataview 카드 뷰 대시보드

## 1. DataviewJS — 허브 노트별 최근 메모 통합 감시

각 프로젝트 허브 노트에 QuickAdd Capture로 쌓이는 메모를 대시보드 한곳에서 실시간 모니터링.

대시보드 노트(예: `00_Dashboard.md`)에 아래 코드 블록을 삽입:

````markdown
```dataviewjs
const pages = dv.pages('"10_Projects"');
let tableRows = [];

for (let page of pages) {
    let file = app.vault.getAbstractFileByPath(page.file.path);
    let cache = app.metadataCache.getFileCache(file);
    
    if (cache && cache.listItems) {
        let pageList = page.file.lists
            .filter(l => l.text.includes("[202"))
            .slice(-3)
            .map(l => l.text)
            .join("<br>");

        if (pageList) {
            tableRows.push([
                page.file.link,
                pageList,
                page.file.mtime.toFormat("yyyy-MM-dd HH:mm")
            ]);
        }
    }
}

tableRows.sort((a, b) => (a[2] < b[2] ? 1 : -1));
dv.table(
    ["📌 허브 노트", "💬 최근 수집된 메모 (Max 3)", "🕒 최근 업데이트"],
    tableRows
);
```
````

### 간이 DQL 버전

DataviewJS가 부담스러우면 표준 DQL로 간단하게:

````markdown
```dataview
TABLE 
    file.mtime AS "최근 업데이트",
    file.lists.text AS "수집된 메모 목록"
FROM "10_Projects"
WHERE file.lists
SORT file.mtime DESC
LIMIT 10
```
````

## 2. Minimal 테마 카드 뷰 설정

### 사전 준비

1. 설정 → 테마 → **Minimal** 테마 설치 및 적용
2. 커뮤니티 플러그인에서 **Minimal Theme Settings** 설치 및 활성화
3. (권장) **Contextual Typography** 플러그인 설치 — 카드 레이아웃 정밀 정렬

### 카드 뷰 DQL 코드

대시보드 노트 상단 프론트매터에 `cssclasses`를 부여:

```yaml
---
cssclasses:
  - cards
  - cards-1-1
  - cards-cover
---
```

본문에 Dataview 쿼리 삽입:

````markdown
```dataview
TABLE WITHOUT ID
    file.link AS "📌 프로젝트명",
    status AS "상태",
    file.mtime AS "최근 수정일",
    file.folder AS "위치"
FROM "10_Projects"
WHERE type = "hub-note" OR file.folder = "10_Projects"
SORT file.mtime DESC
```
````

### cssclass 옵션 레퍼런스

| cssclass | 효과 |
|---|---|
| `cards` | Dataview 표를 카드 레이아웃으로 전환 |
| `cards-cover` | 노트 내 첫 번째 이미지를 카드 상단 커버로 표시 |
| `cards-1-1` | 1:1 정사각형 비율 카드 |
| `cards-cols-3` | 그리드를 3열로 고정 (2~4 조절 가능) |
| `table-with-borders` | 카드에 명확한 테두리 윤곽선 부여 |

### 완성 결과

- 프로젝트별 상태(🟢/🟡), 수정일, 첨부파일 링크가 격자형 카드에 표시
- 허브 노트에 대표 이미지가 있으면 카드 상단 커버로 자동 표시
- 화면 크기에 따라 2열/3열/4열 반응형 재배치

## 활용 노하우

- QuickAdd Capture의 `- [{{date:YYYY-MM-DD HH:mm}}] {{VALUE}}` 포맷 덕분에 메모 앞에 시각이 자동으로 붙어 타임라인 형태 출력
- 대시보드 표의 허브 노트 링크 클릭 → 해당 프로젝트로 즉시 이동
- 메모 내 `[[파일명.xlsx]]` 링크도 대시보드에서 바로 클릭 가능

## 관련 개념

- [[quickadd-자동화]]
- [[허브-노트-패턴]]
- [[obsidian-추천-플러그인]]
