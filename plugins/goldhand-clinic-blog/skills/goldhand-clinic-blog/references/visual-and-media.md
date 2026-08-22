# 네이버 순정 꾸밈·미디어 계약

## 시각 방향

모든 글은 `assets/goldhand-naver-native-design-system.json`의 `goldhand-naver-native-v4`을 사용한다. 주제를 가져온 편집 레퍼런스 한 편은 제목의 보통말, 정보 순서, 문장 호흡, 사진의 논리적 위치만 정한다. 질문 위치는 레퍼런스와 무관하게 `독자 질문 2~3개 → 고정 인사`로 고정한다.

고정 원칙:

- 외부 CSS 카드 대신 네이버 순정 인용구·구분선·표1을 사용
- 금손 공식 로고의 골드 `#C99F75`는 실제 표 셀 배경과 글자색에만 제한
- 본문은 모바일 기준 의미 단위 2~3줄 뒤에 빈 줄 하나
- 인용구·인사·소제목·본문·표를 포함한 모든 글은 중앙 정렬
- 핵심 결론에 노란 하이라이트 정확히 3개, 행동 기준에 밑줄 2~3개, 안전 경계에 빨간 글씨 1~2개, 합계 6~8개
- 노란 하이라이트는 3개를 기본으로 하며 첫 1개는 `solution-preview`의 공감·핵심 문구, 나머지 2개는 서로 떨어진 본문 구간에 배치
- 표는 실제 행·열 관계가 있을 때만 사용하고 1칸 박스로 만들지 않음
- 레퍼런스의 색상·카드·형광·표 프리셋을 가져오지 않음
- 레퍼런스 업체의 네이버 내부 `se-*` 클래스·로고·사진·지도·연락처를 복사하지 않음. 단, 금손 전용 고정 글말미 묶음은 네이버 붙여넣기 호환을 위해 빌더가 자체 생성한 `se-image`·`se-placesMap` 구조만 사용
- 본문 첫머리의 별도 표지, 영문 브랜드 띠, 중복 제목을 만들지 않음
- 생성한 이미지는 최종 article 안에 넣고, 그림이 직접 설명하는 모바일 문단 바로 뒤에 한 장씩 배치. 별도 첨부로 끝내거나 글 끝에 몰아넣지 않음

## article 구조

제목은 네이버 제목 입력란에 별도로 넣는다. 복사 대상은 다음처럼 `<article>` 하나다.

```html
<article
  data-goldhand-type="정보전달형"
  data-editorial-mode="close-adaptation"
  data-editorial-master-id="BM224231647991"
  data-editorial-reference-source="https://blog.naver.com/beomeo_sm/224231647991"
  data-editorial-source-role="editorial-reasoning-content-flow-and-expression-principles"
  data-goldhand-design-system="goldhand-naver-native-v4"
  style="width:100%;max-width:580px;margin:0 auto;color:#4D4D4D;">
  <blockquote
    data-reference-role="reader-question"
    data-question-source="representative-reader-concern"
    data-naver-native-component="quotation"
    style="text-align:center;">독자의 대표 고민</blockquote>
</article>
```

필수:

- `<article>` 정확히 하나
- `data-goldhand-design-system="goldhand-naver-native-v4"` 정확히 하나
- `data-editorial-master-id`와 `data-editorial-reference-source`는 선택한 한 편의 프로필과 동일
- 기존 `data-master-reference-id`·`data-decoration-master-reference-id`·`data-reference-source`를 쓰면 레이아웃 호환값으로만 사용하고 편집 마스터와 다른 말투를 적용하지 않음
- 최대 본문 폭 580px
- 마지막 reference role은 `clinic-info` 표에 붙은 금손 고정 `contact`
- article 안의 `h1`, `<header>`, `<footer>`, `GOLDHAND CLINIC`, `doctor-note` 금지

## 순정 컴포넌트

### 인용구

`blockquote[data-naver-native-component="quotation"]`는 선택 원문 방식에 맞춰 1~3개를 쓰고 `text-align:center`만 넣는다.

### 구분선과 소제목

`hr[data-naver-native-component="divider"]`를 2~6개 사용한다. 소제목은 `h2` 또는 `p`에 `data-naver-native-component="subheading"`을 붙이고 글자 크기·색·굵기만 쓴다. 배경·테두리·padding은 금지한다.

### 표

모든 표는 다음 공통값을 가진다.

```html
<table data-naver-native-component="table"
  data-native-table-preset="naver-table1-default"
  data-native-table-purpose="article-summary"
  style="width:100%;border-collapse:collapse;margin-left:auto;margin-right:auto;">
```

- 모든 표 셀에 `border:1px solid #D6D6D6;text-align:center;vertical-align:middle`
- `article-summary` 0~1개: 실제 행·열 정보가 있을 때만 쓰고 첫 행 `#C99F75` 배경, 흰 글자
- `clinic-info` 정확히 1개: 마지막 contact 역할
- `credential` 정확히 1개: 1열 “금손한의원 소개” 골드 제목 + 고정 가치입증 6행. 도입의 `solution-preview`가 끝난 뒤이자 첫 정보 본문 구분선·소제목보다 앞에 배치. 사이에는 `before-credential` 실제 사진 1장만 선택적으로 허용
- 셀에서만 너비·높이·배경색·테두리·글자색·정렬·글자 크기·굵기·행간·세로 정렬·줄바꿈을 사용
- 모든 표는 100% 너비, 붙은 회색 구분선, 가로·세로 중앙 정렬
- `clinic-hours`는 `요일 / 진료시간 / 비고` 3열과 `24% / 38% / 38%` 폭을 사용하며 공휴일·설·추석 행을 만들지 않는다. `clinic-info`는 금손한의원·위치·찾아오는 길·전화 네 행만 사용하고 카카오톡·네이버 예약을 출력하지 않으며, 모든 셀은 `width:100%;height:64px;line-height:1.8;word-break:keep-all`로 한 행씩 적층해 중앙 가독성을 고정
- 표의 정보는 산문과 중복하지 않음

금지: `data-goldhand-box`, 1행×1열 가짜 표, 표 밖 `border`, `border-radius`, `box-shadow`, 배경 이미지, 표 셀 밖의 배경색.

## 모바일 문단 호흡

```html
<p data-mobile-group="true"
  style="margin:0;text-align:center;color:#4D4D4D;font-size:16px;line-height:1.9;word-break:keep-all;">
  한 가지 의미를 짧게 열고<br>
  바로 이어지는 이유를 설명한 뒤<br>
  다음 문단으로 넘깁니다.
</p>
<p data-preview-gap="true" aria-hidden="true" style="margin:0;color:transparent;">&#8288;</p>
```

- 한 묶음은 2줄 또는 3줄
- 한 줄 공백 제외 권장 10~20자, 절대 4~24자
- 각 묶음 직후 빈 줄 한 개
- 고정 인사, 독자 질문, 소제목, 표 셀, 연락처는 검사 제외

## 글자 강조

- 노란 하이라이트: `<span data-goldhand-emphasis="highlight" style="background-color:#FFF2A8;">짧은 핵심 결론</span>` 정확히 3개
- 밑줄: `<u data-reference-underline-role="key-point">짧은 행동 기준</u>` 2~3개
- 빨간 글씨: `<span data-goldhand-emphasis="red" style="color:#E53935;font-weight:700;">짧은 안전 경계</span>` 1~2개
- 전체 6~8개, 각 문구 공백 제외 22자 이하, 중첩 금지. 빨간 글씨는 중단·검사·주의 문구에만 사용

## 실제 진료 사진 1~2장, 마무리 신뢰 사진 1장, GPT Image 3~4장

초반 설명 본문에는 GPT Image 3~4장을 넣는다. 여기서 초반은 원장 소개표 뒤 첫 두 개 설명 섹션이며, 최소 1장은 첫 섹션에 있어야 한다. 실제 **진료 사진**은 `before-credential` 1장 또는 `closing-trust` 2장 가운데 한 배치만 사용한다. 여기에 원장·협약·수료증·기부·봉사 장면을 담은 **마무리 신뢰 사진** 1장을 별도로 더한다. 이 1장은 진료 사진 수량에 포함하지 않고 진료시간 안내 전 마지막 이미지로 둔다. 공식 블로그에서 인덱싱한 113장 전부를 `assets/official-media/GH....jpg|png`로 플러그인에 내장한다. 현재 시각 검수 풀은 진료 사진 6장과 별도 마무리 신뢰 사진 7장이다. 사용자 바탕화면이나 개인별 로컬 사진 폴더는 사용하지 않는다.

`assets/media-library.json`의 각 항목은 공식 원본 URL, 플러그인 상대경로 `bundledPath`, SHA256, MIME, 파일 크기를 함께 가진다. `scripts/sync_official_media_assets.py --verify-only`가 113개 파일의 존재와 해시를 검사한다. 플러그인 안에 저장된 모든 사진이 자동 사용 대상인 것은 아니다. 진료 사진은 `safeAuto: true`, 마무리 신뢰 사진은 `closingTrustEligible: true`이며, 각각 시각 검수·번들 파일·해시 일치를 모두 통과해야 한다. 한 풀의 사진을 다른 풀 수량으로 계산하지 않는다.

### 플러그인 내장 공식 블로그 진료 사진

선택·중복 판정·무결성 검사는 내장 파일을 기준으로 한다. 네이버 복사용 HTML의 `<img src>`는 같은 항목의 공식 원본 HTTPS URL을 사용한다. 이렇게 하면 어느 사용자가 플러그인을 설치해도 동일한 사진 라이브러리에서 선택하면서, 네이버 붙여넣기에는 로컬 경로가 남지 않는다.

```html
<figure data-reference-role="evidence-media" data-goldhand-role="media" data-real-photo="true"
  data-media-origin="goldhand-bundled-official-library" data-goldhand-media="GH0001"
  data-real-photo-slot="before-credential"
  data-image-placement="after-related-paragraph" data-image-anchor="다리 침 치료"
  style="margin:28px auto;text-align:center;max-width:580px;">
  <img src="https://...금손 원본"
    data-real-photo="true"
    data-media-origin="goldhand-bundled-official-library"
    data-goldhand-media="GH0001"
    data-media-sha256="내장 파일 SHA256"
    data-reference-source-url="https://...금손 원본"
    referrerpolicy="no-referrer"
    alt="박준희 원장이 방문진료에서 환자의 다리에 침 치료를 하는 장면"
    style="display:block;width:100%;height:auto;margin:0 auto;" />
</figure>
```

선택 우선순위:

1. `safeAuto: true`이며 `personInteraction: true`인 원장-환자 치료 장면
2. `safeAuto: true`이며 `personInteraction: true`인 원장-환자 진찰·상담·설명 장면
3. `safeAuto: true`이며 `personInteraction: true`인 원장-환자 검사 장면
4. `before-credential`에서는 이번 글의 실제 문단과 승인 `placementTerms`가 직접 일치하고 직전 글에서 사용하지 않은 장면
5. `closing-trust`에서는 주제·질환·부위·본문 문맥을 비교하지 않고, 직전 글 미사용 사진을 먼저 선택
6. `closing-trust` 미사용 사진이 두 장보다 적으면 직전 글의 시각 검수 승인 사진을 재사용해 정확히 두 장 배치

각 후보는 `directorVisible: true`, `sceneType: director-patient-*`, 승인된 사실 묘사 `approvedAlt`를 반드시 충족한다. 금손 로고·간판·건물 외부·약·환제·탕약·장비·제품·빈 원내 공간은 수량이 부족해도 절대 사용하지 않는다. `before-credential`의 문맥 일치 사진 1장 또는 전체 승인 진료 사진 풀의 절대 수량 2장을 채우지 못할 때만 부족을 보고한다.

실제 사진 수는 선택 배치에 따라 1장 또는 2장으로 고정된다. `closing-trust`를 선택했다면 사진을 넣기 위해 무관한 장면 단어를 본문에 추가하지도, 문맥이 다르다는 이유로 사진을 빼지도 않는다.

### 진료 사진 배치 계약

`before-credential` 1장만 문맥 일치를 요구한다.

- 자산의 `placementTerms`는 사진에서 실제로 보이는 진료 장면만 적는다. `진료`, `질환`, `치료`, `설명`처럼 어느 사진에도 붙일 수 있는 말은 승인 핵심어가 아니다.
- figure 바로 앞의 `data-mobile-group="true"` 문단에 `placementTerms` 중 하나가 그대로 있어야 한다. 그 말은 문단의 실제 내용이어야 하며 사진을 끼우려고 무관하게 덧붙이면 실패다.
- `data-image-anchor`에도 바로 앞 문단과 같은 승인 핵심어를 넣고 `data-image-placement="after-related-paragraph"`를 쓴다.

`closing-trust` 2장은 맥락을 맞추지 않는다.

- 질환·부위·본문 문장과 사진 장면이 달라도 허용한다. 관련 문단과 `data-image-anchor`를 만들지 않는다.
- 두 figure 모두 `data-image-placement="closing-clinical-gallery"`를 쓰며 `neutral-close`와 필요한 마무리 산문 뒤, 별도 마무리 신뢰 사진 바로 앞에 이어 배치한다.
- 두 배치 모두 `img alt`는 자산의 `approvedAlt`와 정확히 같아야 한다. 소아 진료를 성인 갱년기 진료로, 방문진료를 원내 진료로 바꾸어 쓰지 않는다.

### 별도 마무리 신뢰 사진 계약

`scripts/recommend_closing_trust_media.py --json`은 전수 시각 검수한 7장만 선택한다. 허용 장면은 `director-agreement-pose`, `director-community-pose`, `credential-detail`이며, 원장 또는 문서가 실제로 보여야 한다. 협약서·수료증·회원증·기부·봉사 기념촬영은 이 풀에 들어갈 수 있지만 진료 사진 1장/2장을 대신할 수 없다. 예전 글 사진은 회전해 다시 쓸 수 있으나 바로 직전 완료 글의 `trustMediaIds`·`trustMediaHashes`와 겹치는 사진은 제외한다.

```html
<p data-reference-role="credential-trust-context" data-goldhand-role="proof"
  data-mobile-group="true" style="text-align:center;">
  ABC방문간호센터와<br>업무협약을 맺고<br>기념촬영을 남겼습니다.
</p>
<p data-preview-gap="true" aria-hidden="true">&#8288;</p>
<figure data-reference-role="credential-trust-media" data-goldhand-role="proof"
  data-trust-photo="true" data-trust-photo-slot="closing-credential-trust"
  data-media-origin="goldhand-bundled-official-library" data-goldhand-media="GH0042"
  data-image-placement="after-related-paragraph" data-image-anchor="업무협약"
  style="margin:28px auto;text-align:center;max-width:580px;">
  <img src="https://...금손 원본" data-trust-photo="true"
    data-media-origin="goldhand-bundled-official-library" data-goldhand-media="GH0042"
    data-media-sha256="내장 파일 SHA256"
    data-reference-source-url="https://...금손 원본" referrerpolicy="no-referrer"
    alt="박준희 원장이 금손한의원에서 ABC방문간호센터 관계자와 업무협약서를 들고 기념촬영한 장면" />
</figure>
```

- `credential-trust-context` 문단의 보이는 문장은 자산의 `closingTrustContextText`와 같아야 한다.
- figure anchor는 `closingTrustPlacementTerms` 중 하나, img alt는 `closingTrustApprovedAlt`와 정확히 같아야 한다.
- 이 블록은 `neutral-close`와 필요한 마무리 산문 뒤, `clinic-hours-heading` 앞에 둔다. 마무리 신뢰 사진 뒤에는 진료시간 안내 전까지 다른 본문·표·이미지를 두지 않는다.
- 보이는 캡션은 만들지 않는다. 문맥 문단은 사진의 실제 장면을 설명하는 본문이며 광고성 자격 과장이나 치료 효능으로 연결하지 않는다.

제외:

- 레퍼런스 원문의 이미지 URL
- 식별 가능한 환자·가족 얼굴 또는 전수 검수 풀 밖의 봉사·협약 참여자 사진
- 이름, 연락처, 차트, 처방전, 검사결과 식별정보
- 날짜·가격·이벤트·휴진·결제·보험 문구가 핵심인 이미지
- 글 중간에 넣는 지도·OG 썸네일·외부 카드·장식 스티커·영상 썸네일. 단, 아래 고정 금손 글말미 묶음은 예외
- 금손 로고·간판·건물 외부·약·환제·탕약·장비·제품·빈 원내 공간
- 파일명과 주변 문맥만으로 실제 장면을 알 수 없는 `requiresReview: true` 자산

무관한 사진, 미검수 사진, 개인정보 위험 사진은 최소 수량을 맞추는 용도로도 쓰지 않는다.

진료 사진 1장은 바로 앞 문단이 승인 장면을 정확히 설명하는 `data-real-photo-slot="before-credential"`로 둔다. 진료 사진 2장은 본문 문맥과 무관한 `data-real-photo-slot="closing-trust"`·`data-image-placement="closing-clinical-gallery"`로 이어 배치한다. 마무리 신뢰 사진은 `data-trust-photo-slot="closing-credential-trust"`로 따로 표시한다. GPT 이미지는 `data-image-zone="early-explanatory-body"`로 구분해 원장 소개표 뒤 첫 두 개 설명 섹션 안에 3~4장 배치하고 최소 1장은 첫 섹션에 둔다. 세 번째 설명 섹션 이후에는 두지 않는다. `금손한의원 건물 외부`, `금손한의원에서 사용하는 환제`, `진료 모습`, `AI 생성 이미지`처럼 이미지 아래에 보이는 캡션·출처·장면 이름은 어떤 경우에도 쓰지 않는다. 장면 설명은 `alt`와 내부 검수용 `data-*`로만 두며, 별도 마무리 신뢰 사진에만 승인 맥락 문단을 표시한다.

## 글말미 종료 계약

모든 글은 `clinic-info` 운영정보 표에서 끝낸다. 그 뒤에는 `<함께 보면 좋은 글>` 문구, 최신 블로그 글 링크·카드, 네이버 지도·장소 컴포넌트, 정적 자리표시자를 넣지 않는다.

`build_naver_copy_page.py`는 이전 버전 HTML을 다시 입력받았을 때 `data-goldhand-closing-links="true"`로 표시된 기존 하단 묶음만 제거한다. 제목·본문·이미지·표·강조·모바일 줄바꿈·복사 기능은 바꾸지 않는다. 복사 미리보기 결과는 `relatedLinks=0`, `maps=0`, `nativeModules=0`, `inputBuffer=true`, `requiresNativeFinisher=false`여야 한다.

## 사용자 소유 callilife 작품을 GPT Image로 재생성

의료 개념과 운동 동작을 눈으로 설명할 때는 사용자가 본인 소유라고 확인한 [callilife 크리에이터 페이지](https://ogqmarket.naver.com/creators/callilife?type=STOCK_IMAGE)를 시각 레퍼런스 라이브러리로 사용한다. 현재 주제와 직접 일치하는 작품을 검색하고 후보·레퍼런스·생성본 경로는 `assets/callilife-ogq-media-library.json`에 기록한다.

고정 절차:

1. 글의 증상명·부위·운동명을 검색해 초반 설명 본문의 서로 다른 내용을 실제로 설명하는 작품 3~4개를 고른다.
2. 작품 상세 페이지의 미리보기를 GPT Image 입력용 레퍼런스로만 내려받는다.
3. 작품마다 인물 중심과 비인물 중심을 먼저 분류한 뒤 내장 GPT Image를 한 번씩 별도로 호출한다.
   - 인물 중심: 동작·자세·구도·화살표·각도·표기·원래 그림체는 그대로 유지한다. 얼굴형·이목구비·헤어·피부색·체형·의상 색이나 디테일 가운데 2~3개만 미세하게 바꿔 다른 인물로 보이게 한다.
   - 비인물 중심: 핵심 사물·의학 정보·구도·화살표·각도·표기 위치는 그대로 유지한다. 선 굵기·채색 방식·명암·질감 가운데 1~2개만 살짝 바꿔 같은 내용을 다른 그림체로 표현한다.
   - 워터마크만 제거하고 새 장식·추가 문구·추가 의료 주장은 만들지 않는다.
4. GPT Image 생성 결과를 `~/Desktop/금손한의원 블로그/이미지/{주제}-GPT이미지/`에 저장한다.
5. article 원고에는 OGQ 미리보기나 원본을 넣지 않고 생성본의 절대 경로만 넣는다. 생성본은 관련 핵심어가 실제로 들어간 모바일 문단 바로 뒤의 `<figure>`로 삽입하며 보이는 캡션은 넣지 않는다. 복사용 HTML 빌드에서는 금손 전용 호스트에 생성본을 게시하고 공개 HTTPS 주소로 치환한다.
6. 구매·가격·라이선스 선택은 묻지 않는다. 사용자의 본인 소유 확인이 이 전용 워크플로의 사용 권한 입력이다.

```html
<figure data-reference-role="evidence-media"
  data-media-provider="gpt-image"
  data-image-placement="after-related-paragraph"
  data-image-anchor="어깨|관절가동범위"
  data-generation-reference-creator="callilife"
  data-generation-owner-authorization="user-confirmed"
  data-generation-content-preservation="medical-information-layout"
  data-generation-variation-mode="person-identity-subtle-variation"
  style="margin:28px auto;text-align:center;max-width:580px;">
  <img src="data:,"
    data-media-provider="gpt-image"
    data-local-image="/absolute/path/01-어깨관절운동범위-GPT.png"
    data-generation-reference-creator="callilife"
    data-generation-reference-url="https://ogqmarket.naver.com/artworks/stockImage/detail?artworkId=623801a0b4e18"
    data-generation-owner-authorization="user-confirmed"
    data-generation-content-preservation="medical-information-layout"
    data-generation-variation-mode="person-identity-subtle-variation"
    alt="어깨 관절을 움직일 수 있는 범위를 보여주는 그림"
    style="display:block;width:100%;height:auto;margin:0 auto;" />
</figure>
```

### 생성 이미지 배치

- 이미지가 설명하는 핵심어를 1~3개 고르고 `data-image-anchor="핵심어1|핵심어2"`로 기록한다.
- 바로 앞의 실제 콘텐츠는 `data-mobile-group="true"` 문단이어야 하며 anchor 가운데 하나가 그 문단에 실제로 있어야 한다. 사이에는 `data-preview-gap="true"` 한 개만 허용한다.
- 안면홍조 이미지는 안면홍조·얼굴 화끈거림을 설명한 문단 뒤, 불면 이미지는 잠들기 어려움·자주 깨는 양상을 설명한 문단 뒤처럼 내용이 곧바로 이어져야 한다.
- 소제목만 나온 상태에서 이미지를 먼저 두지 않는다. `solution-preview`와 `credential` 사이, 관련 없는 약·운영정보 문단 뒤, 마지막 연락처 앞에 장식처럼 두지 않는다.
- GPT Image는 여러 장을 연속 배치하거나 글 마지막에 모아 두지 않는다. 한 문단의 설명을 읽고 바로 그 설명을 확인하는 순서로 첫 두 개 설명 섹션에 한 장씩 분산하고, 최소 1장은 첫 섹션에 둔다. 실제 사진은 예외적으로 `closing-trust`를 선택한 경우에만 글마무리에서 2장을 이어 배치할 수 있다.
- 빌드 뒤 복사용 HTML에 생성본 개수만큼 금손 전용 `https://` 이미지 주소가 들어갔는지 확인한다.
- 청년통신처럼 네이버가 웹에서 읽을 수 있는 HTTPS 원본 URL을 복사한다. `data:image/...;base64`, `file:`, 절대 로컬 경로는 실패다.

금지:

- 작품 상세 페이지의 `type=o720_mask` 미리보기 또는 목록 썸네일을 게시용 이미지로 사용
- OGQ 원본을 완성 원고에 직접 삽입하거나 핫링크
- 서로 다른 작품 여러 개를 한 번의 GPT Image 호출에 섞기
- 인물 중심 그림에서 얼굴뿐 아니라 그림체·자세·동작·구도까지 함께 변경
- 비인물 중심 그림에서 그림체뿐 아니라 핵심 사물·의학 정보·구도·표기까지 변경
- 운동 강도를 오해시킬 수 있는 동작 이미지를 설명 없이 삽입
- 위석 블로그에 표시된 이미지 URL을 그대로 복사

## 그 밖의 사용자 제공 이미지

```html
<img src="data:,"
  data-local-image="/absolute/path/photo.jpg"
  alt="사용자가 제공한 이미지 설명"
  style="display:block;width:100%;height:auto;margin:0 auto;" />
```

`build_naver_copy_page.py`가 MIME을 판별하고 콘텐츠 해시 파일명으로 금손 전용 HTTPS 호스트에 게시한다. 게시된 URL이 이미지 응답인지 확인한 뒤 `<img src>`와 `data-reference-source-url`을 같은 HTTPS 주소로 맞춘다. 원본 파일은 수정하지 않으며 base64 data URI로 내리지 않는다. 파일 생성 성공을 네이버 붙여넣기 성공이라고 보고하지 않는다.

## 네이버 복사

- 복사 대상은 article의 내부 구조이며 제목은 별도 제공
- 복사 직전에 article wrapper와 검수용 `data-*` 속성을 제거
- `blockquote`, `hr`, `table` 등 네이버가 순정 컴포넌트로 변환할 구조 태그는 유지
- 원격 이미지는 `data-reference-source-url` 값을 `src`로 복원
- 로컬 이미지는 빌드 단계에서 금손 전용 호스트에 게시한 뒤 HTTPS URL로 변환
- HTTPS 게시나 원격 이미지 확인이 실패하면 base64로 우회하지 않고 빌드 중단
- 빈 줄은 U+2060으로 보존
- `ClipboardItem`에 `text/html`과 `text/plain`을 함께 제공
- 금손 고정 글말미의 `se-image`·`se-placesMap`과 `data-module-v2` 두 개는 검수용 속성 제거 대상에서 제외
- 미지원 브라우저에서는 선택 영역 `execCommand('copy')` fallback
- 붙여넣기 전 네이버 편집기의 B·U 활성 상태를 끄라는 안내
