# 모바일 문단·네이버 순정 꾸밈 계약

## 확인한 기준

2026-08-20에 범어 설명한의원 블로그 최근 공개 글 15편의 모바일 호흡을 확인했다. 내용·의학 주장·업체 정보는 사용하지 않고 다음 읽기 방식만 참고한다.

- 실제 텍스트 줄 2,111개의 공백 제외 길이 중앙값은 14자였다.
- 빈 줄로 나뉜 문맥 묶음 901개 중 약 91%가 2줄 또는 3줄이었다.
- 짧은 시각 줄 2~3개 뒤에 빈 줄을 두는 패턴이 반복됐다.

같은 날 실제 네이버 스마트에디터 ONE에서 기존 복사 원고의 변환 결과도 확인했다.

- `<blockquote>`는 네이버 인용구 `se-quotation se-l-default`로 변환됐다.
- `<hr>`는 네이버 구분선으로 변환됐다.
- `<table>`은 네이버 순정 `se-table se-l-default`, 편집기 표 스타일의 `표1`로 변환됐다.
- 배경·테두리를 준 `<section>`과 `<h2>`는 1칸 표로 바뀌어 외부 카드처럼 보였다.

따라서 이 스킬은 자연스러운 완성 문장을 먼저 쓴 뒤 `짧은 시각 줄 2~3개 → 빈 줄`로 표시한다. 모바일 길이에 맞추려고 단어를 추상어로 바꾸거나 문장 논리를 다시 만들지 않는다. 꾸밈은 `blockquote·hr·실제 다행다열 table`만 사용한다.

## 금손 모바일 문단

일반 본문은 아래 형식으로 쓴다.

```html
<p data-mobile-group="true"
  style="margin:0;color:#4D4D4D;font-size:16px;line-height:1.9;text-align:center;word-break:keep-all;">
  오래 앉아 있었다는 사실보다<br>
  몸을 어느 방향으로 틀었는지가<br>
  부담이 쏠린 위치를 설명합니다.
</p>
<p data-preview-gap="true" aria-hidden="true" style="margin:0;color:transparent;">&#8288;</p>
```

작성 규칙:

1. `data-mobile-group="true"` 한 개는 모바일 시각 줄 2개 또는 3개다.
2. 시각 줄은 `<br>`로 분리하고, 한 줄은 공백 제외 10~20자를 목표로 하며 4~24자 밖으로 나가지 않는다.
3. 조사와 체언, 수식어와 피수식어, 주어와 서술어 사이를 기계적으로 끊지 않는다.
4. 같은 문장을 길이만 맞추려고 나누지 않고, 다음 줄이 이전 줄의 의미를 완성하거나 새 정보를 더하게 한다.
5. 한 묶음 뒤에는 `data-preview-gap="true"` 빈 줄을 한 개 둔다.
6. 고정 인사, 소제목, 짧은 인용 질문, 표 셀, 고정 연락처는 2~3줄 검사에서 제외한다.
7. 글자가 있는 인용구·인사·소제목·일반 본문·표 셀은 모두 중앙 정렬한다.
8. 줄바꿈은 표시 단계다. 한 줄마다 독립 결론문을 새로 만들거나 체크리스트 말투로 바꾸지 않는다.

## 핵심 문구 강조

- 노란 하이라이트 `3개`: `<span data-goldhand-emphasis="highlight" style="background-color:#FFF2A8;">핵심 결론</span>`
- 순정 밑줄 `2~3개`: `<u data-reference-underline-role="key-point">행동 기준</u>`
- 빨간 글씨 `1~2개`: `<span data-goldhand-emphasis="red" style="color:#E53935;font-weight:700;">안전 경계</span>`
- 세 방식 합계는 `6~8개`이며 한 문구는 공백 제외 22자 이하로 짧게 쓴다.
- 문단 전체를 하이라이트하지 않고 한 문단에 핵심 구절 하나만 고른다.
- 첫 하이라이트는 `solution-preview`에서 독자가 바로 공감할 불편 또는 주제 핵심에 둔다. 나머지 2개는 서로 떨어진 본문 구간에 둔다.
- 같은 문구에 노란 하이라이트·밑줄·빨간 글씨를 겹치지 않는다.
- 빨간 글씨는 운동 중단, 다른 검사 우선, 주의 신호처럼 반드시 구분해야 하는 문장에만 쓴다. 효과나 예약 유도에는 쓰지 않는다.

## 레퍼런스별 체류 장치

- 제목은 선택된 `titleMechanism`의 숫자·권위·대비·지식 공백·생활 장면·결과 모순 가운데 허용된 장치를 쓴다.
- 제목이 `2가지`, `3단계`처럼 실제 답 개수를 약속한 경우에만 같은 개수의 번호 소제목을 두고 `validate_title.py --answer-count N`을 추가한다.
- 도입 `solution-preview`에는 선택된 `data-intro-persuasion-device`와 본문에 보이는 `data-reader-payoff`를 둔다.
- `specific-number-low-friction-topic-payoff`를 선택한 경우에만 `data-reference-role="reading-time-hook" data-reading-minutes="1~5"` 문단을 한 번 둔다.
- 분 단위 숫자는 읽기 비용을 구체화하고 부담을 낮추는 장치다. 실제 분량에 맞는 숫자 뒤에 그 글에서만 얻는 구체적인 보상을 붙이며 원문 문장을 복사하지 않는다.

## 고정 순정 컴포넌트

정확한 규칙은 `assets/goldhand-naver-native-design-system.json`을 단일 기준으로 사용한다.

### 1. 독자 고민 — 네이버 인용구

```html
<blockquote
  data-reference-role="reader-question"
  data-question-source="representative-reader-concern"
  data-naver-native-component="quotation"
  style="text-align:center;">대표 독자 고민</blockquote>
```

- 선택한 편집 레퍼런스 방식에 맞춰 1개, 2개 또는 3개를 사용한다.
- `text-align:center` 외의 배경색, 테두리, padding, 둥근 모서리를 넣지 않는다.
- 네이버에 붙여넣으면 편집기의 순정 인용구가 외형을 결정한다.

### 2. 금손한의원 소개 — 정보 본문 직전 고정 표

- `credential` 표는 모든 글에서 정확히 한 번 사용한다.
- 독자 고민과 고정 인사는 편집 마스터가 정한 순서로 모두 끝내고, `solution-preview` 전체가 끝난 뒤에 배치한다. `before-credential` 실제 사진 1장 구성에서만 표 바로 위 사진을 허용한다.
- `credential` 다음의 첫 콘텐츠 컴포넌트는 첫 정보 본문의 `divider` 또는 `section-heading`이어야 한다. 구분선과 소제목을 함께 쓰면 `credential`은 첫 구분선 바로 앞에 둔다.
- `solution-preview`와 `credential` 사이, `credential`과 첫 정보 본문 사이에 이미지·일반 본문·`article-summary`·다른 표를 끼우지 않는다. 시각 간격만 만드는 `data-preview-gap="true"`는 콘텐츠로 보지 않는다.
- 이 위치는 주제·편집 마스터·이미지 유무와 관계없이 모든 자동모드·정밀작성모드 글에 동일하게 적용한다.

### 3. 소제목 — 평문 + 네이버 구분선

```html
<hr data-reference-role="divider" data-naver-native-component="divider">
<h2 data-reference-role="section-heading"
  data-naver-native-component="subheading"
  style="margin:0;color:#4D4D4D;font-size:19px;line-height:1.7;font-weight:700;word-break:keep-all;">
  1. 한 자세가 이어지는 시간
</h2>
```

- 소제목 자체에 배경·테두리·padding을 주지 않는다.
- 구분선은 글 전체 2~6개 범위에서 필요한 위치에만 쓴다.
- 소제목은 2~4개다.

### 4. 정보 정리 — 네이버 표1

```html
<table data-naver-native-component="table"
  data-native-table-preset="naver-table1-default"
  data-native-table-purpose="article-summary"
  style="width:100%;border-collapse:collapse;margin-left:auto;margin-right:auto;">
  <tbody>
    <tr>
      <td style="width:34%;background-color:#C99F75;border:1px solid #D6D6D6;color:#FFFFFF;text-align:center;vertical-align:middle;font-weight:700;">살필 조건</td>
      <td style="width:66%;background-color:#C99F75;border:1px solid #D6D6D6;color:#FFFFFF;text-align:center;vertical-align:middle;font-weight:700;">기록할 내용</td>
    </tr>
    <tr>
      <td style="background-color:#F3E8DD;border:1px solid #D6D6D6;color:#7A5434;text-align:center;vertical-align:middle;font-weight:700;">자세</td>
      <td style="border:1px solid #D6D6D6;color:#4D4D4D;text-align:center;vertical-align:middle;">얼마나 오래 유지했는지</td>
    </tr>
  </tbody>
</table>
```

- `credential`은 “금손한의원 소개” 골드 제목 1행 + 고정된 짧은 경력·강점 6행의 1열 표다. 고정 운영정보는 `clinic-hours` 3열 진료시간표와 `clinic-info` 1열 위치·전화 정보표 두 개로 구성한다.
- `article-summary` 표는 행·열로 보는 편이 산문보다 분명할 때만 한 번 사용하고 첫 행을 금손 골드·흰 글자로 고정한다.
- 표는 산문을 다시 요약하는 장식이 아니라, 비교·조건·순서처럼 행과 열로 볼 때 더 분명한 정보를 대신 담는다.
- `credential`, `clinic-hours`, `clinic-info`는 각각 정확히 1개 쓰고 `article-summary`는 0개 또는 1개 쓴다.
- 가치입증 6행은 `assets/goldhand-value-proof-library.json`과 문구·순서가 정확히 같아야 한다.
- 모든 셀에 `1px solid #D6D6D6` 구분선을 넣고, 글자는 가로·세로 중앙 정렬한다.
- 표는 100% 너비, 붙은 셀 테두리, 좌우 자동 여백으로 중앙 배치한다.
- `clinic-hours`는 첨부 레퍼런스처럼 `요일 / 진료시간 / 비고` 3열로 만들고 폭은 `24% / 38% / 38%`로 고정한다. 첫 행은 금손 골드 `#C99F75`와 흰 글자, 요일 셀은 크림 `#F3E8DD`와 골드 브라운 `#7A5434`를 쓴다. 본문 행은 월·수·금, 화·목, 토·일만 사용하고 공휴일·설·추석 행은 만들지 않는다.

- `clinic-info`는 금손한의원 골드 제목띠 다음 위치·찾아오는 길·전화만 한 행씩 쌓는 1열 다행 표다. 카카오톡·네이버 예약 행은 만들지 않는다. 모든 셀은 `100%` 폭과 기본 높이·행간·줄바꿈을 동일하게 둔다.

```html
<td style="width:100%;height:64px;background-color:#C99F75;border:1px solid #D6D6D6;color:#FFFFFF;font-weight:700;text-align:center;vertical-align:middle;line-height:1.8;word-break:keep-all;">금손한의원</td>
<td style="width:100%;height:64px;border:1px solid #D6D6D6;color:#4D4D4D;text-align:center;vertical-align:middle;line-height:1.8;word-break:keep-all;">위치<br>전남광주통합특별시 서구 유림로98번길 3, 2층</td>
```

## 금지

- `data-goldhand-box`
- 1행×1열 표 또는 병합해 한 칸처럼 보이게 만든 표
- `section`, `div`, `h2`의 배경색·테두리·padding 카드
- 표 밖의 `border`, `border-radius`, `box-shadow`, 왼쪽·위쪽 강조선, 그라데이션
- 표 셀 밖의 크림·골드 배경색
- 레퍼런스마다 달라지는 박스나 표 프리셋
- 표와 산문에서 같은 의미 반복

## 실패 조건

- 일반 본문 묶음이 1줄이거나 4줄 이상
- 중앙 정렬 누락
- 노란 하이라이트·밑줄·빨간 글씨 개수 또는 허용 마크업 위반
- 가치입증 고정 6행 변경
- 한 시각 줄이 공백 제외 24자 초과
- 문맥과 무관한 위치에서 줄바꿈
- 네이버 순정 인용구·구분선·표1 마커 누락
- `credential`이 질문·인사·완성된 `solution-preview`보다 앞에 있거나 첫 정보 본문 구분선·소제목 뒤에 있음
- `solution-preview → credential → 첫 정보 본문 divider/section-heading` 사이에 다른 콘텐츠가 끼어 있음
- `clinic-info` 표 누락 또는 불필요한 `article-summary`로 산문을 반복함
- `clinic-hours` 셀의 24:38:38 폭 또는 `clinic-info` 셀의 100% 적층 행 폭·중앙 정렬·기본 높이 누락
- `clinic-hours`에 공휴일·설·추석 행이 있거나 `clinic-info`에 카카오톡·네이버 예약 행이 있음
- 1행×1열 가짜 표, CSS 카드, 외부 박스 스타일 발견
- `data-goldhand-design-system="goldhand-naver-native-v4"` 누락
