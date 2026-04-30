---
title: "Step 1 검색식·URL (센서 융합 디스플레이 RFP)"
created: 2026-03-07
tags: [특허검색, Google Patents, 검색식, RFP, 센서융합디스플레이]
---

# Step 1 검색식·Google Patents URL

**기준 RFP**: (2026) RFP 센서 융합 디스플레이 기술  
**반드시 포함**: 신축(stretchable), 디스플레이(display)  
**반드시 제외**: OLED, 페로브스카이트(perovskite), LCD  
**검색 기간**: 우선일 기준 2011.01.01 ~ 2026.12.31 (15년)

---

## 검색식 (QUERY_STRING)

```
(stretchable OR display) AND (experience OR interface OR user OR display OR panel OR screen OR OLED OR LED OR flexible OR stretchable) AND (sensor OR sensing OR deformation OR transformable OR strain OR touch OR detection OR deformable) AND  NOT ("OLED" OR "perovskite" OR "LCD")
```

- 첫 번째 블록: **필수 포함** — `stretchable` 또는 `display` 중 최소 1개
- 두 번째 블록: 디스플레이·UI 관련어 (RFP 추출)
- 세 번째 블록: 센서·변형 관련어 (RFP 추출)
- `NOT`: OLED, perovskite, LCD 제외

---

## Google Patents 검색 URL

**아래 URL을 브라우저에서 열고, 검색 결과에서 CSV를 내보내기 하세요.**

[https://patents.google.com/?q=%28stretchable+OR+display%29+AND+%28experience+OR+interface+OR+user+OR+display+OR+panel+OR+screen+OR+OLED+OR+LED+OR+flexible+OR+stretchable%29+AND+%28sensor+OR+sensing+OR+deformation+OR+transformable+OR+strain+OR+touch+OR+detection+OR+deformable%29+AND++NOT+%28%22OLED%22+OR+%22perovskite%22+OR+%22LCD%22%29&after=priority:20110101&before=priority:20261231](https://patents.google.com/?q=%28stretchable+OR+display%29+AND+%28experience+OR+interface+OR+user+OR+display+OR+panel+OR+screen+OR+OLED+OR+LED+OR+flexible+OR+stretchable%29+AND+%28sensor+OR+sensing+OR+deformation+OR+transformable+OR+strain+OR+touch+OR+detection+OR+deformable%29+AND++NOT+%28%22OLED%22+OR+%22perovskite%22+OR+%22LCD%22%29&after=priority:20110101&before=priority:20261231)

---

## 다음 단계 (Step 2)

1. 위 URL로 Google Patents 검색 결과를 연다.
2. 결과 페이지에서 **Download** 또는 **CSV 내보내기**로 데이터를 다운로드한다.
3. 다운로드한 CSV 파일을 워크스페이스에 저장한 뒤 **파일 경로**를 알려준다.
4. 해당 경로를 사용해 Step 3(상관성 파이프라인)을 실행한다.
