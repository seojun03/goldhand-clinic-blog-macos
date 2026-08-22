---
name: goldhand-clinic-blog
description: 금손한의원 정보형 네이버 블로그 글을 만든다. 직접 본문까지 검토한 위석부부한의원 정보글 11편 중 한 편을 고르고, 그 글의 제목 장치·독자 심리·도입 설득·정보 흐름·전환·디테일한 표현 기능·마무리 감정을 먼저 해석한 뒤 확인된 금손한의원 사실과 박준희 원장의 실제 생활어로 자연스럽게 재구성한다. 원문 완성 문장·업체 사실·경력·환자 수·사례·성과·프로그램·사진은 복사하지 않는다. 구체적인 읽기 시간 숫자는 모든 글의 공식이 아니라 부담을 낮추고 주제별 보상을 약속할 때만 1~5분에서 판단한다. 완성 산문과 SEO가 끝나면 writing-voice로 전체 글을 다시 듣고, 사실·순서·확신 강도·레퍼런스 장치를 보존한 채 문장 표현만 최종 검수한다. 동시 작업은 레퍼런스를 선점해 같은 글이 나오지 않게 한다. 꾸밈과 고정 자격·운영정보는 goldhand-naver-native-v4 계약을 유지하며, 글은 clinic-info 운영정보 표에서 끝낸다.
---

# 금손한의원 블로그 자동화

금손한의원 박준희 원장이 환자 한 명에게 차분히 설명하는 정보 글을 만든다. 내부 기획 라벨, 레퍼런스 ID, SEO 횟수, 검수표, 이미지 지시는 완성 본문에 노출하지 않는다.

## 운영체제별 실행기

- 플러그인은 macOS와 Windows에서 같은 글쓰기·검수·HTML 계약을 사용한다.
- Python 명령은 현재 운영체제에서 실제로 종료 코드 0으로 실행되는 Python 3 실행기를 먼저 확인한다. Windows에서는 한글 JSON 출력을 보존하도록 `py -3 -X utf8`, 다음으로 `python -X utf8`을 사용한다. macOS 공유 설치본에서는 먼저 `${CODEX_HOME:-$HOME/.codex}/state/goldhand-clinic-blog/bin/python3`, 다음으로 `python3`을 사용한다. 아래 예시의 `python3`는 이렇게 확인한 실행기로 치환한다.
- Windows 출력 폴더는 레지스트리에 등록된 실제 바탕화면을 우선 사용하므로 OneDrive 바탕화면도 따른다. 복사 안내는 Windows에서 `Ctrl+V`, macOS에서 `⌘V`로 표시한다.
- GPT Image 생성·본문 배치는 두 운영체제에서 동일하다. 공유용 설치기는 필요한 Node.js와 Vercel CLI를 자동으로 준비한다. 최초 설치 또는 첫 글에서 이미지 호스트 설정이 없으면 `scripts/setup_image_host.py`를 실행한다. 사용자는 브라우저에서 본인 Vercel 로그인만 승인하고, 프로젝트 생성·연결·첫 배포·고정 공개 주소 선택·`image-host.json` 저장은 스크립트가 맡는다. Vercel 토큰과 계정 정보는 플러그인에 넣지 않는다. 네이버가 읽을 공개 HTTPS 주소로 게시할 때 Windows에서는 npm의 `vercel.cmd`·`vercel.exe`·`vercel` 순서로 실제 실행 파일을 찾는다. macOS에서는 `${CODEX_HOME:-$HOME/.codex}/state/goldhand-clinic-blog/bin/vercel`을 먼저 확인한 뒤 `vercel`을 사용한다.

## 절대 계약

1. 작성 형식은 정보 본문형 하나뿐이며 HTML 유형 값은 `정보전달형`이다. 일상글은 말투 분석 자료일 뿐 생성하지 않는다.
2. 도입의 대표 독자 고민은 선택한 위석 정보글 한 편의 실제 고민을 금손 내용으로 바꿔 2~3개 둔다. 이 질문 2~3개를 글의 첫 보이는 문장으로 연속 배치한 뒤에만 고정 인사를 쓴다. 같은 뜻을 늘려 개수를 맞추지 않는다.
3. 마지막 고민 뒤, 첫 정보 소제목 전에 독자가 헷갈리는 이유와 이번 글에서 풀 범위·금손의 설명 기준·읽고 얻게 될 판단을 예고한다. 이 부분은 배경·테두리가 없는 일반 산문 문단으로 쓴다.
4. 업체소개형·사례공유형·스토리텔링형·일상글·공지·이벤트는 자동 선택, 최근 이력 회전, 무작위 선택, 기본값, 자료 부족 fallback 어디에도 넣지 않는다.
5. 자동 주제는 `assets/wipark-content-briefs.json`의 본문 검토 완료 11편에서만 고른다. 최근 3개와 같은 레퍼런스·핵심 대상·검색 의도는 후보에서 제외한다.
6. 한 글에서는 주제를 가져온 위석 원문 한 편을 `content and editorial reference`로 고정한다. `orderedContentAtoms`로 사실 골격을 지키고, 같은 ID의 `referenceWritingIntelligence`로 제목 심리·도입 설득·정보 공개 순서·전환·미세 표현 기능·마무리 감정을 함께 재구성한다. 여러 글을 섞거나 평균 내지 않는다.
7. 위석 원문의 완성 문장, 7어절 이상 연속 표현, 업체명·지역·원장·경력·환자 수·성과·프로그램·장비·사진·연락처는 가져오지 않는다. 다만 종결어미 하나를 흉내 내는 수준이 아니라 질문의 기능, 구체성, 리듬 변화, 반론 인정, 대비, 호기심 공백, 보상 약속이 왜 효과적인지는 분석해 금손 내용으로 바꾼다.
8. `assets/goldhand-official-voice-profile.json`, `references/goldhand-official-voice.md`, `references/natural-speech-rewrite-protocol.md`는 레퍼런스의 설득 구조를 지우는 대체 템플릿이 아니다. 해석한 기능을 유지한 채 모든 완성 문장을 박준희 원장이 실제 진료실에서 말할 생활어로 자연화한다. 의료 답은 검토된 일반 정보, 금손 최신 사실, 필요한 권위 자료가 결정한다.
9. 꾸밈은 편집 마스터와 무관하게 `goldhand-naver-native-v4`로 고정한다. 네이버 순정 인용구·구분선·표1 외의 CSS 카드, 둥근 박스, 그림자, 왼쪽·위쪽 강조선, 1행×1열 가짜 표는 쓰지 않는다.
10. 인용구 2~3개는 실제 환자 발화라고 주장하지 않는다. 확인된 직접 인용이 아니라 검색 독자를 대표하는 고민으로 쓴다.
11. 기본 화자는 박준희 원장이다. 글은 대표 독자 고민 인용구 2~3개로 바로 시작하고, 그 다음에 `안녕하세요, 금손한의원 박준희 원장입니다.`를 정확히 한 번 쓴다. 인사·병원명·원장 소개를 첫 질문보다 앞에 두거나 질문 사이에 끼우면 실패다.
12. 이모지, `^^`, `ㅎㅎ`, `ㅠㅠ`, 하트, 해시태그 장식, 강한 내원 유도, 치료 보장을 쓰지 않는다.
13. 예시 금지어만 피해 비슷한 문장으로 바꾸지 않는다. `조금 더 분명히 구분할 수 있습니다`, `차분히 살펴보겠습니다`, `구체적인 단서가 될 수 있습니다`를 포함해 번역투 명령문, 독자에게 기록·관찰·정리를 숙제처럼 시키는 문장, 감성적 여운을 위한 추상 결론을 만드는 생성 방식 자체를 쓰지 않는다. `판단·기준·구분·확인`은 실제 동작보다 많이 반복하지 않는다.
14. 문법적으로 자연스러운 것만으로 통과시키지 않는다. 지나치게 완곡하게 돌려 말하는 안내, 독자에게 교훈을 주거나 여운을 남기는 결말, 실제 대화보다 블로그 작문을 위해 만든 티가 나는 문장도 실패다. `아픈 자리`, `걷기가 달라지다`, `자세가 이어지다`, `부담이 반복되다`, `치료 방향에 차이를 만들다`처럼 추상 명사에 작문용 서술어를 붙인 압축 표현도 같은 원리에서 모두 제거한다. `아픈 곳`, `평소보다 걷기 힘들다`, `같은 자세로 오래 일하면 목이 다시 뻐근하다`처럼 환자가 듣자마자 동작과 불편을 떠올릴 수 있는 생활어로 문장 구조부터 다시 쓴다.
15. 완성물은 항상 `제목 + 본문 + 네이버 복사용 HTML`이다. 사용자가 HTML을 명시적으로 제외한 경우에만 파일을 생략한다.
16. 인용구·인사·해결 방향·소제목·일반 본문·표를 포함한 모든 글은 중앙 정렬한다. 왼쪽 정렬을 섞지 않는다.
17. 핵심 결론에는 노란 하이라이트 정확히 3개, 실제로 필요한 구체적 행동에는 네이버 순정 밑줄 2~3개, 중단·검사·주의 같은 안전 경계에는 빨간 글씨 1~2개를 넣되 합계는 6~8개다. 밑줄 개수를 맞추려고 기록·관찰·회상 숙제를 만들지 않는다.
18. 가치입증은 후보나 주제별 선택이 아니다. `assets/goldhand-value-proof-library.json`의 고정 6행을 모든 글에서 같은 문구·순서로 사용한다.
19. `금손한의원 소개` 가치입증 표는 모든 글에서 도입 질문·인사·`solution-preview`가 모두 끝난 뒤, 첫 정보 본문의 구분선·소제목·설명보다 앞에 둔다. `before-credential` 배치를 선택했을 때만 `solution-preview`와 표 사이에 실제 사진 1장을 허용하며, 그 밖의 본문·이미지·표는 끼우지 않는다.
20. 제목은 선택 프로필의 `titleMechanism`이 맡은 독자 심리를 금손 내용으로 옮긴다. 권위 숫자는 `clinic-facts.md`에서 확인되고 주제와 관련 있을 때만 쓰며, 위석의 경력·환자 수·원장 수는 버린다. `2가지`, `3가지` 같은 답 개수를 실제로 약속한 제목에서만 같은 개수의 번호 답을 둔다. 숫자 제목은 필수가 아니다.
21. `solution-preview`에는 `data-intro-persuasion-device`와 보이는 `data-reader-payoff`를 둔다. `specific-number-low-friction-topic-payoff`를 선택한 경우에만 `reading-time-hook`을 한 번 쓰고, 실제 분량에 맞는 1~5분의 숫자와 제목·독자 고민에 직접 연결되는 보상을 함께 제시한다. 3분을 모든 글에 반복하거나 숫자 뒤에 막연한 도움만 약속하면 실패다.
22. 도입에서 오십견 핵심 또는 독자의 불편을 설명하는 한 구절을 노란색으로 표시한다. 노란 하이라이트 3개 가운데 1개는 반드시 `solution-preview`에, 나머지 2개는 서로 다른 본문 구간에 둔다.
23. 시각 자료는 사용자가 본인 소유라고 확인한 [네이버 OGQ마켓 callilife](https://ogqmarket.naver.com/creators/callilife?type=STOCK_IMAGE)에서 주제와 직접 맞는 작품 3~4개를 찾는다. 작품마다 내장 GPT Image를 별도로 호출한다. 인물 중심 그림은 동작·자세·구도·화살표·각도·표기·그림체를 유지하고 얼굴형·이목구비·헤어·피부색·의상 색이나 디테일 가운데 2~3개만 미세하게 바꾼다. 비인물 중심 그림은 핵심 사물·정보·구도·표기를 유지하고 선 굵기·채색·명암·질감 가운데 1~2개만 살짝 바꾼다.
24. 원고 article에는 OGQ 미리보기나 원본을 넣지 않고 GPT Image 생성본의 절대 로컬 경로만 넣는다. 빌드할 때는 생성본을 금손 전용 HTTPS 이미지 호스트에 게시하고, 청년통신 복사 페이지와 동일하게 공개 HTTPS 주소를 `<img src>`와 `data-reference-source-url`에 넣는다. 네이버가 제외하는 `data:image/...;base64`는 만들지 않는다. 실제 진료 사진·마무리 신뢰 사진·GPT 이미지 모두 `<figcaption>`이나 이미지 아래 설명 문단을 만들지 않는다. 작품 상세 URL·사용자 소유 확인·의학 정보 및 배치 보존·허용된 변형 모드는 보이지 않는 검수용 `data-*`와 `alt`에만 남기며 네이버 복사 본문에서는 내부 `data-*`를 제거한다. 인물 중심 그림의 그림체 변경, 비인물 중심 그림의 내용·배치 변경은 실패다. 구매·가격 확인·라이선스 요청 단계는 없다.
25. 생성한 이미지는 별도 첨부로 끝내지 않고 최종 `<article>`과 네이버 복사용 HTML 안에 반드시 삽입한다. 각 이미지는 그 그림이 직접 설명하는 증상·동작·치료 원칙을 적은 모바일 문단 바로 뒤에 한 장씩 둔다. 3~4장 모두 원장 소개표 뒤 첫 두 개 설명 섹션 안에 배치하고, 그중 최소 1장은 첫 번째 설명 섹션에 둔다. 각 figure에는 `data-image-zone="early-explanatory-body"`를 표시한다. 세 번째 설명 섹션 이후, 도입과 본문 사이, 소제목 직후, 관련 없는 문단 뒤, 글 끝에 몰아넣는 배치는 금지한다. `<figure>`에는 `data-image-placement="after-related-paragraph"`와 직전 문단에서 실제로 확인되는 `data-image-anchor`를 둔다.
26. GPT Image 3~4장과 별도로 실제 **진료 사진**은 두 배치 중 하나만 사용한다. `before-credential`은 해결 방향 예고 뒤·`금손한의원 소개` 표 바로 위에 정확히 1장, `closing-trust`는 `neutral-close` 뒤의 마지막 신뢰 구간에 정확히 2장이다. 진료 사진을 설명 본문 중간에 분산하거나 두 배치를 섞으면 실패다. 공식 블로그에서 수집한 113장 전부는 플러그인 `assets/official-media`에 들어 있으며, `assets/media-library.json`에서 진료 사진으로 `safeAuto: true`이고 번들 파일·해시가 확인된 6장만 이 수량에 사용할 수 있다. 사용자 바탕화면이나 개인별 사진 폴더를 요구하지 않는다.
27. 실제 사진은 `원장이 환자를 치료하는 장면 → 원장이 환자를 진찰·상담·설명하는 장면 → 원장이 환자를 검사하는 장면`만 선택한다. `personInteraction: true`, `directorVisible: true`, `sceneType: director-patient-*`를 모두 충족해야 한다. 금손한의원 로고·간판·건물 외부·약·환제·탕약·장비·제품·빈 원내 공간은 수량이 부족해도 절대 fallback으로 쓰지 않는다. `before-credential`은 바로 직전 완료 글과 다른 사진만 쓰고, `closing-trust`는 다른 사진을 우선하되 두 장을 채우지 못하면 직전 글의 시각 검수 승인 사진을 재사용한다.
28. 진료 사진과 **별도로**, 시각 검수된 원장·협약·수료증·기부·봉사 장면을 글마다 정확히 1장 더 사용한다. `recommend_closing_trust_media.py`로 `closingTrustEligible: true`인 7장 중 직전 완료 글과 겹치지 않는 사진을 고른다. `neutral-close`와 필요한 마무리 산문 뒤, 진료시간 안내 앞에 `data-trust-photo="true" data-trust-photo-slot="closing-credential-trust"`로 두며 진료시간 전 마지막 이미지여야 한다. 이 사진은 진료 사진 1장/2장 수량에 절대 포함하지 않는다.
29. `before-credential` 진료 사진은 `placementTerms`·`approvedAlt`를 정확히 사용하고 바로 앞 문단과 `data-image-anchor`가 같은 승인 장면을 가리켜야 한다. `closing-trust` 진료 사진 2장은 질환·부위·본문 문맥과 맞지 않아도 되며, `data-image-placement="closing-clinical-gallery"`로 두고 `data-image-anchor`나 관련 문단을 요구하지 않는다. 다만 자산의 정확한 `approvedAlt`는 유지한다. 별도 마무리 신뢰 사진은 `closingTrustPlacementTerms`·`closingTrustApprovedAlt`·`closingTrustContextText`를 정확히 사용하고, 앞 문단을 `data-reference-role="credential-trust-context" data-goldhand-role="proof"`로 표시한다. 환자·가족 얼굴, 이름, 연락처, 차트, 처방전, 검사결과가 식별되거나 시각 검수를 통과하지 않은 사진은 사용하지 않는다.
30. `before-credential`의 문맥 일치 승인 사진 1장을 고르지 못하거나, 시각 검수된 실제 진료 사진 풀 자체가 `closing-trust` 2장에 못 미치거나, 별도 마무리 신뢰 사진 1장을 고르지 못하면 자동모드라도 HTML 조립과 발행을 중단한다. `closing-trust`에서는 주제 불일치나 직전 글 사용 이력만으로 중단하지 않고 승인 사진을 재사용해 정확히 2장을 넣는다. 두 사진 풀은 서로 대체하지 않는다.
31. 모든 글의 고정 운영정보는 공휴일 행이 없는 `clinic-hours` 진료시간 3열 표 다음, 위치·찾아오는 길·전화만 담은 `clinic-info` 1열 다행 표 순서로 둔다. 카카오톡·네이버 예약은 출력하지 않는다. 글은 `clinic-info` 표에서 끝내며, 그 뒤에는 `<함께 보면 좋은 글>` 문구, 최신 블로그 글 링크·카드, 네이버 지도·장소 컴포넌트, 해당 자리표시자를 넣지 않는다.
32. 완성 산문과 정확 키워드 배치가 끝나면 [references/final-writing-voice-review.md](references/final-writing-voice-review.md)를 읽고 `writing-voice-final-rehear-v1` 최종 재청취를 실행한다. 이 패스는 글 전체를 말하는 속도로 다시 듣고 generic한 연결·평평한 리듬·독자 초점 이탈·근거 없는 윤색만 국소 수정한다. 특히 첫 질문 2~3개를 한 세트로 소리 내어 읽고, `증상명 때문에 …나요?` 틀을 연속 복제하거나 증상을 쉼표로 묶어 `이어지나요?`로 끝내는 요약형 질문을 생활 장면 질문으로 다시 쓴다. 내용 추가·삭제·순서 변경, 사실·의료 경계·확신 강도·제목·도입·흐름·마무리 장치 변경, SEO 약속·고정 HTML 구성 변경은 금지한다. 고칠 곳이 없으면 `no-change-needed`로 통과시키며 억지로 수정하지 않는다.

### 진료실 발화 가능성 검사

완성 문장마다 `금손한의원 원장님이 환자 앞에서 실제로 이렇게 말할까?`를 다시 묻는다. 조금이라도 글말처럼 들리면 단어만 바꾸지 말고 짧고 직접적인 생활어 문장으로 다시 쓴다.

`제가·사실·그런데·~죠`와 대화형 어미의 집계값은 검수 보조값이지 작성 목표가 아니다. `A라고 단정할 수 없습니다 → 반대로 B라고 볼 수도 없습니다 → 사람마다 다릅니다 → 진찰이 필요합니다` 같은 대칭형 전개, 환자 상태와 연결되지 않은 치료명 나열, `확인합니다·봅니다·정합니다`의 반복은 개별 금지어가 없어도 다시 쓴다.

### writing-voice 최종 재청취 검사

초안 단계의 발화 편집과 별개로, SEO까지 반영된 완성 산문을 마지막에 한 번 더 읽는다. 먼저 제목, 내용 원자와 흐름 비트 순서, 사실과 의료 경계, 선택한 설득 장치, 고정 구성 요소를 동결한다. 그런 다음 제목부터 마무리까지 실제 말하는 속도로 듣고 상투적인 연결 문장, 같은 호흡의 반복, 박준희 원장의 확신·유보·주의가 무난하게 평평해진 곳, 독자 고민보다 블로그다운 요약이 앞선 곳만 찾는다.

수정한 문단마다 `더 자연스럽게`가 아니라 `환자가 어느 동작에서 아픈지 바로 떠올리게 함`, `지나친 유보 때문에 흐려진 안전 지시를 직접 들리게 함`처럼 표현이 수행할 일을 내부 기록에 남긴다. 부분 수정 뒤에는 글 전체를 다시 읽는다. `assets/writing-voice-final-review-contract.json`과 `scripts/validate_final_voice_review.py`를 통과하지 못하면 HTML 조립이나 완료 보고로 넘어가지 않는다.

## 필요한 자료만 읽기

- 금손 사실·운영·진료 태도: [references/clinic-facts.md](references/clinic-facts.md)
- 단일 글 구조와 문장 역할: [references/content-formulas.md](references/content-formulas.md)
- 주제·일반 정보·내용 순서: [references/wipark-content-source-policy.md](references/wipark-content-source-policy.md), `assets/wipark-content-briefs.json`, [references/reference-master-library.md](references/reference-master-library.md)
- 제목 심리·도입 설득·흐름·디테일한 표현·마무리 판단: 자동·정밀작성 모두 초안 전에 [references/reference-editorial-reasoning.md](references/reference-editorial-reasoning.md)와 선택된 `assets/reference-writing-intelligence.json` 프로필을 읽는다.
- 금손 공식 말투: [references/goldhand-official-voice.md](references/goldhand-official-voice.md), `assets/goldhand-official-voice-profile.json`
- 모든 초안의 내용 분리·생활어 재작성: [references/natural-speech-rewrite-protocol.md](references/natural-speech-rewrite-protocol.md)
- 완성 산문·SEO 뒤 마지막 문장 검수: 플러그인에 함께 들어 있는 `$writing-voice`, [references/final-writing-voice-review.md](references/final-writing-voice-review.md), `assets/writing-voice-final-review-contract.json`. 외부 사용자 스킬 폴더의 동명 스킬에 의존하지 않는다.
- 레퍼런스 역할·복사 거리 대조: [references/reference-exact-reconstruction.md](references/reference-exact-reconstruction.md)
- 치료·인증·수치·의학 표현: [references/medical-writing-guardrails.md](references/medical-writing-guardrails.md)
- 모바일 문단·네이버 순정 꾸밈: [references/mobile-readability-and-brand-boxes.md](references/mobile-readability-and-brand-boxes.md), `assets/goldhand-naver-native-design-system.json`
- 고정 가치입증 6행: `assets/goldhand-value-proof-library.json`을 그대로 사용하며 선택·교체·순서 변경 금지
- HTML·이미지: [references/visual-and-media.md](references/visual-and-media.md)
- 글말미 제외 계약: `assets/goldhand-closing-links.json`에서 비활성 상태와 `clinic-info` 종료를 확인한다.
- 사용자 소유 callilife 작품 후보·GPT 재현 상태: `assets/callilife-ogq-media-library.json`
- 모드·검수·저장: [references/workflow-and-output.md](references/workflow-and-output.md)
- 금손 공식 글 조사 범위·이미지: [references/official-blog-inventory.md](references/official-blog-inventory.md)

## 실행 모드

사용자가 모드를 말하지 않았다면 다른 질문을 섞지 말고 다음 한 문장만 묻는다.

`1. 자동모드  2. 정밀작성모드`

이미 모드가 명시되면 반복하지 않는다.

### 자동모드

메인키워드가 없으면 `메인키워드를 입력해 주세요.`만 출력한다.

메인키워드를 받으면 추가 확인 없이 끝까지 진행한다.

1. 입력한 메인키워드의 띄어쓰기와 표기를 정확히 고정한다.
2. `scripts/select_wipark_content_reference.py --reserve`로 본문 검토 완료 위석 정보글 11편 중 한 편을 원자적으로 선점한다. 최근 3개와 같은 레퍼런스·핵심 대상·검색 의도뿐 아니라 다른 진행 중 작업이 예약한 레퍼런스도 제외한다. 새 후보가 없으면 중복으로 되돌아가지 않는다.
3. `광주 한의원`, `광주 한의원 추천`처럼 포괄적인 지역·업종 키워드는 SEO 앵커일 뿐 글의 주제가 아니다. 선택된 위석 글의 실제 건강 문제를 주제로 쓴다.
4. 선택 결과의 `topic`, `readerConcerns`, `orderedContentAtoms`, `referenceWritingIntelligence`, `approvedWritingLessons`, `blockedFromSource`를 한 묶음으로 고정한다. 제목 장치만 빌리고 다른 흐름을 쓰거나 여러 글을 섞지 않는다.
5. `sourceProseWithheld=true`, `contentAtomCoverageRequired=true`, `sourceSentenceImitationBlocked=true`, `referenceEditorialReasoningEnabled=true`, `goldhandFactReplacementRequired=true`, `voiceProtocolId=natural-speech-rewrite-protocol-v1`, `voiceProfileId=goldhand-official-voice-v1`, `finalVoiceReviewRequired=true`, `finalVoiceReviewerSkill=writing-voice`, `finalVoiceReviewContractId=writing-voice-final-rehear-v1`을 확인한 뒤에만 초안을 쓴다.
6. [references/reference-editorial-reasoning.md](references/reference-editorial-reasoning.md)에 따라 `독자 상태 → 제목 장치와 이유 → 도입 장치와 이유 → 주제별 보상 → 흐름 비트별 역할과 전환 → 원문 사실 슬롯을 금손 사실로 교체하거나 생략 → 마무리 감정` 판단 카드를 내부적으로 만든다. 이어 `내용 원자 ID → 확인된 금손 사실·권위 정보 → 환자가 겪는 장면`을 대응한다.
7. `referenceWritingIntelligence.titleMechanism.allowedIds` 중 한 장치를 골라 제목을 만든다. 답 개수 숫자를 실제로 약속한 경우에만 `--answer-count N`을 추가하고, 항상 `scripts/validate_title.py --editorial-close --reference-master-id 선택ID --title-mechanism-id 선택장치`로 검사한다. 위석의 환자 수·경력·원장 수·성과 숫자는 가져오지 않는다.
8. `orderedContentAtoms`의 사실 순서와 `flowBeats`의 독자 심리·전환을 함께 사용해 SEO·HTML·이미지·모바일 줄바꿈이 없는 평문을 먼저 쓴다. `microExpressionPatterns`의 기능을 금손 내용으로 새로 표현하고, 별도 발화 편집 패스에서 이 기능을 지우지 않은 채 반복·추상어·대칭형 안전 문장·치료명 나열을 고친다. 모든 원자와 흐름 비트가 대응된 뒤 선택한 도입 설득 장치·주제별 보상·프로필별 마무리와 정확 키워드 2~3회를 반영한다. 완성 산문을 `writing-voice-final-rehear-v1`로 최종 재청취해 표현만 국소 수정하고 전체를 다시 읽은 다음에만 모바일 줄바꿈·강조·이미지·순정 꾸밈을 적용한다.
9. callilife에서 주제에 맞는 작품 3~4개를 고르고 작품 상세 미리보기를 생성 레퍼런스로 확보한다. 각 작품이 인물 중심인지 비인물 중심인지 먼저 분류한다. 인물 중심이면 표현·그림체를 유지하고 인물만 미세하게 바꾸며, 비인물 중심이면 내용·배치를 유지하고 그림체만 미세하게 바꾼다. 생성본만 로컬에 저장하고, 원장 소개표 뒤 첫 두 개 설명 섹션에서 각 생성본이 설명하는 핵심 단어가 실제로 들어간 모바일 문단 바로 뒤에 한 장씩 삽입한다. 최소 1장은 첫 번째 설명 섹션에 둔다. 세 번째 설명 섹션 이후나 글 끝에 모아 두지 않는다. 구매·가격·라이선스 선택은 묻지 않는다.
10. 진료 사진 배치를 `before-credential` 1장 또는 `closing-trust` 2장 중 하나로 정한다. `before-credential`은 `recommend_media.py`가 주제의 실제 장면과 맞고 바로 직전 완료 글에 쓰지 않은 사진만 고른다. `closing-trust`는 질환·부위·본문 문맥을 비교하지 않고 시각 검수된 원장-환자 치료·진찰·상담·검사 사진 2장을 고른다. 직전 글 미사용 사진을 먼저 쓰고 부족하면 직전 글 승인 사진도 재사용한다. 모든 후보는 `bundledPath`·SHA256·공식 원본 URL·`approvedAlt`가 일치해야 한다.
11. 진료 사진과 별도로 `recommend_closing_trust_media.py --json`을 실행해 검수된 협약·수료증·기부·봉사 사진 1장을 고른다. 진료 사진은 `data-real-photo="true"`와 `data-real-photo-slot="before-credential|closing-trust"`, 마무리 신뢰 사진은 `data-trust-photo="true"`와 `data-trust-photo-slot="closing-credential-trust"`로 완전히 분리한다. 신뢰 사진은 `credential-trust-context` 문단 바로 뒤, 진료시간 안내 전 마지막 이미지로 두며 이 별도 신뢰 사진은 바로 직전 완료 글과 겹치지 않게 회전한다.
12. `validate_reference_learning.py`, `validate_final_voice_review.py`, `validate_natural_speech_suite.py`, `validate_reference_reconstruction.py --editorial-close`, `validate_copy_overlap.py`, `validate_goldhand_voice.py`, `validate_article.py --editorial-close`를 모두 통과한 원고만 완성한다. 최종 article에는 `data-writing-voice-review="writing-voice-final-rehear-v1"`과 `data-writing-voice-status="pass"`를 둔다. 최근 3개 이력에는 선택한 위석 레퍼런스, 제목·도입·마무리 장치와 의미 주제, 진료 사진 ID·파일 해시(`realMedia*`), 마무리 신뢰 사진 ID·파일 해시(`trustMedia*`)를 따로 기록한다. `record_article_state.py`에 선택기의 reservation master ID와 run ID를 함께 넘겨 완료 시 예약을 해제한다. 실패로 중단하면 선택기의 `--release-master-id`·`--release-run-id`로 예약을 해제한다.
13. `build_naver_copy_page.py`가 글을 `clinic-info` 운영정보 표에서 끝내고, 운영정보 뒤의 `<함께 보면 좋은 글>`·최신 블로그 링크·네이버 지도를 만들지 않는지 확인한다. 복사 미리보기는 `relatedLinks=0`, `maps=0`, `nativeModules=0`, `inputBuffer=true`, `requiresNativeFinisher=false`여야 하며 다른 본문 출력은 이전 계약과 같아야 한다.
14. 제목의 실제 답을 만들 필수 사실이 없거나, `before-credential` 문맥 사진·전체 승인 진료 사진 풀·별도 마무리 신뢰 사진 풀의 절대 수량이 부족할 때만 필요한 결정을 짧게 묻는다. `closing-trust`는 주제와 안 맞거나 직전 글에 썼다는 이유로 멈추지 않는다. 두 풀은 서로 대체하지 않는다.

자동모드 완성 글은 지역명·상호·운영정보를 가려도 독자가 가져갈 수 있는 원인 설명, 자가 점검, 생활관리, 치료·검사 판단이 남아야 한다. `한의원 고르는 법`, `추천하는 이유`, `선택 기준`, `잘하는 곳의 조건`처럼 업체 선택을 본문 주제로 삼지 않는다. 포괄 키워드를 받았다는 이유로 업체소개형이나 병원 비교형으로 전환하지 않는다.

자동모드의 정보 주제는 증상형에만 고정하지 않는다. 주제 후보가 치료 적용·중단·시기·주의를 묻는 글이면, 금손에서 실제 사용하는 치료 또는 독자가 이미 사용 중이라고 가정할 수 없는 일반 의료 주제를 중심으로 `무엇을 위한 치료인가 → 어떤 상태를 먼저 구분하는가 → 언제 고려하는가 → 치료만으로 부족할 수 있는 조건 → 다른 검사·치료가 먼저인 경계`를 설명한다. 추나요법의 적용 기준·치료 뒤 관리뿐 아니라 위고비·마운자로 사용 중단 뒤 체중관리처럼 독자 판단에 실제 도움이 되는 주제도 포함할 수 있다. 다만 금손한의원이 해당 약을 처방하거나 특정 장비·프로그램을 제공한다고 쓰지 않는다. 최근 글이 한 축에 치우쳤다면 가능한 범위에서 다른 핵심 대상과 검색 의도로 회전한다.

### 정밀작성모드

한 번에 하나만 질문하며 이미 답한 값은 다시 묻지 않는다.

1. 메인키워드
2. `select_wipark_content_reference.py --count 3 --no-reserve`로 최근 3개와 겹치지 않는 주제 후보 3개를 고른다. 각 후보에는 주제·핵심 내용뿐 아니라 제목 심리·도입 설득·흐름·마무리를 가져올 `콘텐츠·편집 레퍼런스` 링크 한 편을 표시한다. 최종 후보를 고르면 `--preferred-master-id 선택ID --reserve`로 같은 ID를 예약한 뒤 진행한다.
3. 후보 중 최종 제목
4. 글에 추가할 사실·원장 판단·실제 장면. 없으면 내장 사실만 사용
5. 플러그인 `assets/official-media`의 공식 블로그 내장 사진 가운데 시각 검수 승인 사진을 자동 사용한다. 이미지 방식이나 사용자 로컬 폴더는 묻지 않는다.

글 유형은 묻지 않는다. 항상 정보형이다. 확정한 원문 한 편에서 주제·질문·핵심 내용뿐 아니라 제목 장치의 심리, 도입 설득, 전환, 디테일한 표현 기능, 마무리 감정을 해석해 가져온다. 원문 완성 문장은 복사하지 않고 확인된 금손 사실과 박준희 원장의 생활어로 새로 쓴다. 꾸밈은 네이버 순정 시스템을 쓴다.

## 제목 계약

- 정확 메인키워드는 제목에 한 번만 넣고 가능한 앞부분에 자연스럽게 둔다.
- 공백 제외 22~40자를 권장하고 50자를 넘으면 발행하지 않는다.
- 제목은 본문이 실제로 답할 구체적인 원인·기준·주의점·시기·원칙을 약속하면서 선택 프로필의 제목 장치가 독자에게 작용한 이유를 유지한다.
- 숫자 후킹은 필수가 아니다. 답 개수, 확인된 권위, 대비, 지식 공백, 생활 장면, 결과의 모순 가운데 `titleMechanism.allowedIds`가 허용한 장치를 선택한다.
- 레퍼런스의 `29,000명`, 경력, 원장 수 같은 권위 수치는 가져오지 않는다. 같은 신뢰 기능에 맞는 금손 사실이 `clinic-facts.md`에 있고 주제와 관련될 때만 교체한다. 없으면 생략하고 진찰·설명 방식이나 독자의 구체적인 궁금증으로 신뢰를 만든다.
- `11년차`는 원장 경력에만 연결한다. 누적환자, 누적추나, 만족도, 재방문율, 지역 1위는 쓰지 않는다.
- 레퍼런스 제목의 흔한 검색 표현과 질문형·이유형 문법뿐 아니라 권위, 대비, 궁금증, 구체적 약속이 왜 작동하는지 해석해 옮길 수 있다. 경력·수치·업체명·지역·치료 성과·고유 프로그램은 확인된 금손 사실 없이 바꾸어 옮기지 않는다.
- `살이 안 빠진다`처럼 사람이 흔히 쓰는 말을 표절 회피 목적으로 `체중이 그대로라면 먼저 볼 기록` 같은 추상어로 치환하지 않는다.
- 후보마다 독자가 얻을 판단을 한 문장으로 답할 수 없으면 폐기한다.
- 포괄적인 지역·업종 키워드가 들어와도 제목의 실제 약속은 구체적인 증상·원인·생활 조건 또는 특정 치료의 원리·적용 기준·효과가 더딘 조건·주의점이어야 한다. 한의원 자체를 고르는 법이나 추천 이유를 제목의 답으로 삼지 않는다.
- 최종 제목은 `scripts/validate_title.py`를 통과시킨다.

## 작성 순서

아래 단계의 작업 흐름은 유지하되 내용은 모두 금손 계약으로 수행한다.

1. **단일 콘텐츠 레퍼런스 선택**: 최근 3개와 겹치지 않는 검토 완료 위석 정보글 한 편을 고정한다.
2. **편집 판단 카드 작성**: 선택된 `referenceWritingIntelligence`에서 독자 상태, 제목 장치와 심리, 도입 장치와 보상, 흐름 비트와 전환, 미세 표현 기능, 신뢰 사실 슬롯, 마무리 감정을 적는다. 원문 문장은 적지 않는다.
3. **내용 원자표·사실 팩 작성**: `orderedContentAtoms`의 순서와 관찰 장면을 고정하고, 확인된 금손 사실, 권위 있는 일반 의학 설명, 예외, 자가관리, 금지 주장을 분리한다. 원문 업체 사실 슬롯은 금손 사실로 교체하거나 생략한다.
4. **제목 생성·검증**: 허용된 제목 장치 중 하나를 골라 왜 이 제목이 독자를 붙잡는지 설명할 수 있을 때만 확정한다. 숫자 답을 약속한 경우에만 `--answer-count N`을 추가한다.
5. **도입 작성**: 선택 글의 독자 고민을 금손 맥락으로 바꾼 질문 2~3개를 첫 보이는 문장으로 연속 배치하고, 그 뒤에 고정 인사를 정확히 한 번 둔다. 이어 선택 프로필의 도입 설득 장치와 주제별 보상을 배치한다. 두 질문을 `증상명 때문에 …나요?` 같은 틀로 나란히 쓰지 않고, 각 질문이 서로 다른 생활 장면과 다른 호흡을 갖게 한다. 분 단위 숫자 장치를 선택했을 때만 실제 분량에 맞는 1~5분을 쓴다. 공감 또는 핵심 문구 한 곳을 노란색으로 강조한다.
6. **1:1 흐름 대응표 작성**: 각 `flowBeats[].id`와 `orderedContentAtoms[].id`에 금손 사실, 환자가 겪는 장면, 다음 문단이 필요한 이유를 대응한다.
7. **생활어 평문 초안 작성**: `microExpressionPatterns`의 기능을 유지하고 `natural-speech-rewrite-protocol.md`를 읽어 SEO·HTML·이미지·강조·모바일 줄바꿈 없이 쓴다. `제가·저는·저도`, 독자 질문, 접속어, `~죠·~거든요·~세요`는 실제 판단과 말 연결이 필요할 때만 쓰며 횟수를 채우지 않는다.
8. **독립 발화 편집**: 새 패스에는 편집 판단 카드·내용 원자표·금손 사실 팩·평문 초안을 전달한다. 문장마다 `박준희 원장이 환자를 앞에 두고 실제로 이렇게 말할까?`, `환자가 듣자마자 어느 동작에서 어디가 어떻게 불편한지 떠올릴 수 있을까?`, `앞 문장과 다른 새 정보를 주는가?`, `레퍼런스에서 배운 설득 기능이 금손식 표현 안에 남아 있는가?`를 묻는다. 번역투·작문체·감성 문장·추상 압축 표현·대칭형 안전 문장·치료명 나열은 단어만 바꾸지 말고 문장 구조부터 다시 쓴다.
9. **독립 검수**: 제목, 편집 판단 카드, 사실 팩, 원자·흐름 비트별 본문 대응, 금손 말투 프로필, 발화 편집이 끝난 평문을 새 패스에서 읽는다. 원문 완성 문장을 대조 자료로만 보고 7어절 이상 복사를 막되, 제목 심리·도입 보상·전환·마무리 감정이 사라졌다면 다시 쓴다.
10. **사전 평문 검수와 부분 수정**: 같은 세 문장 문단 연속, `먼저`·`반대로` 남용, 8어절 문장 틀 복제, 원자 누락, 같은 의미 반복을 찾는다. 실패 문장과 필요한 앞뒤 문장만 고치며 문제가 없는 문단은 고정한다.
11. **SEO 산문 완성**: 자연스러운 글의 새 정보를 늘리지 않고 정확 키워드를 2~3회 넣는다. 제목 약속, 공백 제외 분량, 각 원자 근거 구절이 모두 남았는지 확인한다.
12. **writing-voice 최종 재청취**: 내부 JSON에 `iteration`, `briefId`, `keyword`, `title`, 검수 직전 전체 문단 `writingVoiceReview.beforeBody`, 최종 문단 `finalBody`, 원자별 정확 구절 `atomCoverage`, 직접 낭독 결과 `manualReview`, `writingVoiceReview`를 기록한다. [references/final-writing-voice-review.md](references/final-writing-voice-review.md)에 따라 전체를 말하는 속도로 읽고 필요한 표현만 국소 수정한다. 바뀐 문단마다 수정 전·후 문장과 표현의 일을 기록하고 전체를 다시 읽는다. `validate_final_voice_review.py`와 `validate_natural_speech_suite.py --expected-count 1`을 모두 통과시킨다. 여러 후보는 같은 suite에 생성 순서대로 추가해 교차 원고 중복도 검사한다.
13. **모바일·이미지·순정 컴포넌트·HTML 조립**: 최종 재청취가 끝난 문장의 표현을 바꾸지 않은 채 모바일 시각 줄로 나눈다. GPT Image 생성본 3~4장은 원장 소개표 뒤 첫 두 개 설명 섹션에 관련 문단별로 배치하고 최소 1장은 첫 섹션에 둔다. 승인 원장-환자 실제 사진은 원장 소개표 바로 위 1장 또는 글마무리 신뢰 구간 2장 중 한 방식만 쓴다. 원장 소개표 위 1장은 바로 앞 문단·anchor·승인 장면을 맞춘다. 글마무리 2장은 본문과 장면이 달라도 되며 `closing-clinical-gallery`로 이어 붙이고, 직전 글 미사용 사진을 우선한 뒤 부족하면 승인 사진을 재사용한다. 모든 글을 중앙 정렬하고 필요한 순정 컴포넌트를 배치한다.
14. **발행 게이트·이력 기록**: 최종 writing-voice 상태, 내용 순서, 금손 말투, 진료실 발화 가능성, 원문 문장 중복, 의료·업체 사실, 실제 진료 사진 1장 또는 2장·별도 마무리 신뢰 사진 1장·GPT Image 3~4장, 각 이미지 구간, 안전·무결성·수량, 별도 신뢰 사진의 직전 글 중복 0장을 검사한 뒤 제목·키워드·주제·콘텐츠 레퍼런스·두 종류 사진의 ID·해시를 최근 3개 이력에 따로 기록한다.

## 본문과 SEO 계약

- 제목과 실제 본문을 합쳐 공백 제외 1,400~1,800자다.
- 정확 메인키워드는 제목 1회, 일반 본문 2회 또는 3회다.
- 표, 이미지 `alt`, 고정 운영정보, 연락처, CTA는 키워드 횟수에서 제외한다.
- 한 문단에는 정확 키워드를 한 번만 쓰며 도입·중반·후반 중 자연스러운 2~3곳에 분산한다.
- 키워드 수를 맞추려고 의미 없는 문장이나 요약 블록을 덧붙이지 않는다.
- 일반 본문은 `data-mobile-group="true"` 한 묶음에 시각 줄 2개 또는 3개를 두고 `<br>`로 나눈다.
- 한 시각 줄은 공백 제외 10~20자를 목표로 하고 4~24자를 벗어나지 않는다. 글자 수보다 조사·체언·서술어가 어색하게 끊기지 않는 것이 우선이다.
- 모든 일반 본문 묶음 뒤에 `data-preview-gap="true"` 빈 줄을 한 개 둔다.
- 모든 일반 본문과 고정 인사도 `text-align:center`로 출력한다.
- 노란 하이라이트는 `<span data-goldhand-emphasis="highlight" style="background-color:#FFF2A8;">짧은 핵심 결론</span>`, 밑줄은 `<u data-reference-underline-role="key-point">짧은 행동 기준</u>`, 빨간 글씨는 `<span data-goldhand-emphasis="red" style="color:#E53935;font-weight:700;">짧은 안전 경계</span>`만 사용한다.
- 노란 하이라이트는 3개를 사용한다. 1개는 도입의 공감·핵심 문구, 2개는 서로 떨어진 본문 핵심 문구에 둔다.
- 분 단위 읽기 안내는 의료 성과 수치는 아니지만 고정 구조도 아니다. 사용할 때는 1~5분의 구체적인 읽기 비용과 그 글에서만 얻는 보상을 같은 도입 안에 두고, 레퍼런스 완성 문장을 복사하지 않는다.
- 빨간 글씨는 중단·검사·주의 같은 안전 경계에만 쓰고 치료 효과, 가치입증, 예약 유도에는 쓰지 않는다.
- 같은 증상도 원인이 다를 수 있음을 설명하고, 필요하면 다른 검사·기관을 먼저 권하는 경계를 함께 쓴다.
- 시술명을 나열하기 전에 왜 반복되는지, 무엇을 구분하는지, 집에서 무엇을 살필지 설명한다.
- 독자에게 무언가를 시킬 때는 실제 치료·안전·진료에 필요한 행동만 말한다. `스스로 운동을 이어가지 마세요`처럼 번역한 듯 완곡하게 말하지 않고 `혼자 판단해서 운동을 계속하시면 안 됩니다`처럼 바로 알아듣게 쓴다.
- `다시 아파지는 순간을 적어보세요. 그게 다음 실마리가 됩니다`처럼 기록을 권한 뒤 추상적 보상을 붙이지 않는다. 정보가 필요하면 `언제, 어떤 동작에서 다시 아픈지 진료할 때 말씀해 주세요`처럼 왜 필요한지 드러나는 실제 말로 바꾼다.
- 문단마다 독자에게 `적어 보세요·떠올려 보세요·살펴보세요`라고 숙제를 주지 않는다. 꼭 기록이 필요한 주제라도 기록 방법과 사용 목적이 구체적일 때만 한 번 설명한다.
- 추상적인 상태명보다 환자가 실제로 하는 동작과 느끼는 불편을 쓴다. `아픈 자리`는 `아픈 곳`, `걷기가 달라지다`는 `평소보다 걷기 힘들다`처럼 바꾸되, 예시만 치환하지 않고 모든 문장을 같은 생활어 기준으로 다시 읽는다.
- `반응·부담·조건·방향·양상` 같은 명사를 썼다면 바로 뒤에 언제, 어떤 동작에서, 어디가 어떻게 아픈지가 보이는지 검사한다. 보이지 않으면 그 문장을 생활 장면으로 다시 쓴다.
- 합성 환자 사례, 허위 직접 인용, 근거 없는 수치, 결과 보장을 만들지 않는다.
- 강한 예약 유도 대신 필요한 경우 현재 상태를 의료진과 상의해도 좋다는 정도로 끝낸다.

## 이미지와 HTML 계약

- 의료 개념·동작 설명 이미지는 사용자 소유 callilife OGQ 작품을 레퍼런스로 우선한다. `assets/callilife-ogq-media-library.json`에서 주제와 직접 연결된 작품 3~4개를 고르고 `safeAuto=true`와 `ownershipBasis=user-confirmed-2026-08-21`을 확인한다.
- 작품 미리보기는 GPT Image 입력에만 사용한다. 최종 원고에는 `data-media-provider="gpt-image"`, 생성본 `data-local-image`, callilife 작품 상세 URL, `data-generation-owner-authorization="user-confirmed"`, `data-generation-content-preservation="medical-information-layout"`, 그리고 `data-generation-variation-mode="person-identity-subtle-variation"` 또는 `nonperson-style-subtle-variation`을 가진 이미지 3~4개만 넣는다.
- 각 GPT Image `<figure>`에는 `data-image-zone="early-explanatory-body"`, `data-image-placement="after-related-paragraph"`, `data-image-anchor="핵심어1|핵심어2"`를 둔다. 직전의 `data-mobile-group="true"` 문단에는 anchor 가운데 하나가 실제로 있어야 한다. 3~4장 모두 원장 소개표 뒤 첫 두 개 설명 섹션 안에 두고 최소 1장은 첫 섹션에 둔다. 생성본은 이 figure로 최종 article에 들어가야 하며, 별도 파일 링크만 전달하면 실패다.
- HTML 조립 전에 `~/.codex/state/goldhand-clinic-blog/image-host.json`이 없거나 연결 프로젝트가 없으면 확인 질문으로 멈추지 말고 현재 운영체제의 Python으로 `scripts/setup_image_host.py`를 실행한다. 로그인되지 않은 경우 브라우저 승인 안내를 사용자에게 한 번 보여 주고, 승인 완료까지 같은 실행을 기다린다. 프로젝트 이름·폴더·공개 주소·JSON 입력을 사용자에게 요구하지 않는다. 사용자가 로그인을 취소하거나 외부 연결이 실패했을 때만 생성된 로컬 이미지를 보존하고 자동 이미지 연결이 끝나지 않았다고 정확히 알린다.
- `build_naver_copy_page.py`는 설정된 금손 전용 호스트를 읽어 로컬 생성본을 콘텐츠 해시 파일명으로 게시한다. 게시된 각 URL이 HTTP 200·이미지 MIME인지 확인한 뒤에만 HTML을 저장하며, 게시 실패 시 base64로 우회하지 않고 빌드를 중단한다.
- GPT Image와 별도로 실제 진료 사진은 `before-credential` 1장 또는 `closing-trust` 2장 중 한 구성을 사용한다. `scripts/recommend_media.py`가 `safeAuto: true`인 진료 장면만 고른다. 여기에 `scripts/recommend_closing_trust_media.py`가 `closingTrustEligible: true`인 협약·수료증·기부·봉사 사진 1장을 별도로 골라 진료시간 전 마지막 이미지로 둔다. 두 풀은 수량과 이력을 서로 대체하지 않는다.
- 실제 사진은 `personInteraction: true`, `directorVisible: true`, `sceneType: director-patient-*`로 검수된 원장-환자 치료·진찰·상담·검사 장면만 사용한다. 로고·건물·약·장비·제품·빈 원내 공간은 절대 사용하지 않는다.
- 실제 사진과 GPT 이미지 모두 이미지 아래에 보이는 설명, 출처, `AI 생성 이미지`, 장면 이름을 쓰지 않는다. `<figcaption>`이 하나라도 있으면 발행하지 않는다. 장면 의미와 출처는 `alt`와 검수용 `data-*`로만 관리한다.
- `before-credential`은 바로 직전 완료 글의 ID·파일 해시와 겹치지 않는 문맥 일치 사진 1장을 쓴다. `closing-trust`는 직전 글 미사용 사진을 먼저 쓰되 두 장이 안 되면 직전 글의 승인 사진을 재사용한다. 주제와 장면이 달라도 사진을 빼지 않는다.
- `before-credential` 사진 바로 앞 모바일 문단에는 승인 `placementTerms` 중 하나가 그대로 있어야 하고 figure의 `data-image-anchor`에도 같은 말을 둔다. `closing-trust` 두 장은 관련 문단·anchor를 요구하지 않고 `data-image-placement="closing-clinical-gallery"`를 쓴다. 두 배치 모두 `alt`는 자산의 `approvedAlt`와 정확히 같아야 한다.
- 식별 가능한 환자·가족 얼굴, 이름, 차트, 연락처가 보이는 공식 이미지는 자동 사용하지 않는다.
- 선택한 위석 블로그 본문의 사진 URL은 복사하지 않는다. 필요한 시각 자료는 callilife 본인 작품 목록에서 별도로 찾고 GPT Image로 재생성한다.
- `<article>` 안에는 제목 `h1`, 영문 브랜드 띠, 고정 원장 카드가 없어야 한다.
- `<article>`에는 `data-goldhand-type="정보전달형"`, `data-editorial-mode="reference-reasoning-goldhand-adaptation"`, 선택한 한 편의 `data-editorial-master-id`, `data-content-reference-source`, `data-editorial-reference-source`, `data-editorial-source-role="editorial-reasoning-content-flow-and-expression-principles"`, `data-reference-writing-profile="선택 INFO ID"`, `data-reference-writing-intelligence="goldhand-reference-writing-intelligence-v1"`, `data-title-mechanism="선택 제목 장치"`, `data-closing-mechanism="선택 마무리 장치"`, `data-goldhand-voice-profile="goldhand-official-voice-v1"`, `data-writing-voice-review="writing-voice-final-rehear-v1"`, `data-writing-voice-status="pass"`를 둔다. 레퍼런스는 설득 기능과 흐름을 통제하고 금손 말투는 문장을 자연화하며 writing-voice는 완성 산문의 표현만 최종 재청취한다.
- `<article>`에 `data-goldhand-design-system="goldhand-naver-native-v4"`을 정확히 한 번 둔다. `data-decoration-master-reference-id`는 레퍼런스의 논리 배치 대조용일 뿐 꾸밈을 바꾸지 않는다.
- 독자 고민 2~3개는 각각 `<blockquote data-reference-role="reader-question" data-question-source="representative-reader-concern" data-naver-native-component="quotation" style="text-align:center;">`로 만든다. blockquote에는 중앙 정렬 외의 배경·테두리·padding 스타일을 넣지 않는다.
- 해결 방향 예고는 `data-reference-role="solution-preview" data-intro-persuasion-device="선택 도입 장치" data-reader-payoff="본문에 실제로 보이는 주제별 보상"`이 붙은 무배경 산문 블록을 정확히 한 번 둔다. 분 단위 장치를 고른 경우에만 내부에 `reading-time-hook`과 `data-reading-minutes="1~5"`를 둔다.
- 선택 프로필의 마무리를 재구성한 `data-reference-role="neutral-close" data-closing-payoff="본문에 실제로 보이는 회수 문구"`를 정확히 한 번 둔다. 같은 중립 문장을 모든 글에 반복하지 않는다.
- 소제목은 `h2` 또는 `p`에 `data-reference-role="section-heading" data-naver-native-component="subheading"`을 두고, 앞뒤에 필요한 네이버 순정 `<hr data-naver-native-component="divider">`를 사용한다.
- 표는 실제 행·열 관계가 있는 정보에만 쓰고, 모든 표에 `data-naver-native-component="table" data-native-table-preset="naver-table1-default"`를 둔다. 표 자체는 `width:100%;border-collapse:collapse;margin-left:auto;margin-right:auto`로 중앙 배치한다.
- 모든 `td`·`th`에 `border:1px solid #D6D6D6;text-align:center;vertical-align:middle`을 빠짐없이 적용한다. 표 안의 라벨·설명·운영정보도 예외 없이 가로·세로 중앙 정렬한다.
- `credential` 가치입증 표를 정확히 한 번 둔다. 첫 행은 “금손한의원 소개” 골드 제목 한 칸, 다음 6행은 `assets/goldhand-value-proof-library.json`의 짧은 경력·강점 문구를 같은 순서로 넣는다. 후보 선택, 주제별 교체, 문장 확장은 금지한다. 위치는 완성된 `solution-preview` 뒤이자 첫 `divider`·`section-heading`·정보 설명 문단 직전으로 고정한다. `before-credential` 구성에서만 표 바로 위 실제 사진 1장을 허용한다.
- `article-summary` 정보표는 행·열 비교가 산문보다 분명할 때만 한 번 둔다. 고정 운영정보는 `진료시간 안내` 중앙 제목, `clinic-hours` 3열 표, `clinic-info` 1열 다행 표 순서로 둔다. `clinic-hours`는 `요일 24% / 진료시간 38% / 비고 38%`이며 첫 행은 금손 골드 배경과 흰 글자, 본문은 월·수·금·화·목·토·일만 표시한다. 공휴일·설·추석 행은 만들지 않는다. 요일 셀은 크림 배경과 골드 브라운 글자를 쓴다. `clinic-info`는 금손 골드 제목띠 뒤에 위치·찾아오는 길·전화만 각각 100% 폭 행으로 적고 카카오톡·네이버 예약은 넣지 않는다. 두 표의 모든 셀은 `height:64px;line-height:1.8;word-break:keep-all`과 중앙 정렬을 사용한다.
- 가치입증처럼 실제 여러 사실을 한 행씩 구분하는 1열 다행 표는 허용한다. 1행×1열 가짜 표, 등록되지 않은 가치입증 문구, 표와 산문의 장황한 중복은 금지한다.
- `data-goldhand-box`, `border-radius`, `box-shadow`, 표 밖의 `border`·임의 왼쪽/위쪽 선·배경색을 쓰지 않는다. `border`는 순정 표의 셀 구분선에만 허용한다.
- 선택 원문의 다른 역할에는 `data-reference-role`을 붙이고 네이버 내부 `se-*` 클래스는 복사하지 않는다. 복사 단계에서는 내부 `data-*`를 제거하고 순정 구조 태그만 네이버로 보낸다.
- 기본 저장 폴더는 `~/Desktop/금손한의원 블로그`, 파일명은 `금손한의원_{제목}.html`이며 충돌 시 `_2`, `_3`을 붙인다.

## 고정 운영정보

고유 결론 뒤에 부담 없는 문의 안내와 아래 정보를 한 번만 둔다. 이 블록은 일반 본문 SEO 횟수 계산에서 제외한다.

- 금손한의원
- 전남광주통합특별시 서구 유림로98번길 3, 2층
- 동천파출소·동천동 행정복지센터 건너편
- 전화 062-515-7582
- 월·수·금 09:30~20:00
- 화·목 09:30~18:00
- 토·일 09:00~13:00

고정 운영정보 블록에는 공휴일·설·추석, 카카오톡, 네이버 예약을 출력하지 않는다. `365일 진료`를 단독으로 쓰지 않는다. 임시휴진·원장 휴가는 고정 블록에 넣지 않는다.

## 검증 명령

```bash
python3 scripts/select_wipark_content_reference.py --keyword "정확 메인키워드" --topic "희망 주제"
python3 scripts/validate_reference_learning.py
python3 scripts/validate_title.py --title "확정 제목" --keyword "정확 메인키워드" --editorial-close --reference-master-id "선택 INFO ID" --title-mechanism-id "선택 제목 장치" --json
python3 scripts/validate_final_voice_review.py --input speech-draft.json --json
python3 scripts/validate_natural_speech_suite.py --input speech-draft.json --expected-count 1 --json
python3 scripts/validate_article.py --input article.html --title "확정 제목" --keyword "정확 메인키워드" --editorial-close
python3 scripts/validate_reference_reconstruction.py --input article.html --profile "선택한 INFO 마스터 ID" --editorial-close
python3 scripts/validate_goldhand_voice.py --input article.html --json
python3 scripts/validate_copy_overlap.py --input article.html --source-text "원문 추출 텍스트"
python3 scripts/sync_official_media_assets.py --verify-only
real_photo_placement_mode="before-credential"  # 또는 closing-trust
python3 scripts/recommend_media.py --topic "확정 주제" --keyword "정확 메인키워드" --type "정보전달형" --placement-mode "$real_photo_placement_mode" --json
python3 scripts/recommend_closing_trust_media.py --json
python3 scripts/build_naver_copy_page.py --title "확정 제목" --article-html article.html
python3 scripts/validate_html.py --input "생성된 HTML 경로"
python3 scripts/record_article_state.py --title "확정 제목" --keyword "정확 메인키워드" --topic-source-id "선택 INFO ID" --topic-source-title "콘텐츠·편집 레퍼런스 제목" --topic-source-url "콘텐츠·편집 레퍼런스 URL" --topic-source-blog-id "wi-parkclinic" --topic-source-role "editorial-reasoning-content-flow-and-expression-principles" --topic-idea "선택 주제" --writing-master-id "선택 INFO ID" --writing-reference-url "콘텐츠·편집 레퍼런스 URL" --editorial-master-id "선택 WP ID" --editorial-reference-title "콘텐츠·편집 레퍼런스 제목" --editorial-reference-url "콘텐츠·편집 레퍼런스 URL" --editorial-source-role "editorial-reasoning-content-flow-and-expression-principles" --editorial-profile-status "ready" --reference-writing-intelligence-id "goldhand-reference-writing-intelligence-v1" --title-mechanism-id "선택 제목 장치" --intro-persuasion-device-id "선택 도입 장치" --closing-mechanism-id "선택 마무리 장치" --reservation-master-id "선택 INFO ID" --reservation-run-id "선택 결과 runId" --real-media-id "GH0001" --real-media-hash "진료 사진 SHA256" --trust-media-id "GH0042" --trust-media-hash "마무리 신뢰 사진 SHA256" --type "정보전달형"
```

제목이 `2가지`, `3단계`처럼 답 개수를 실제로 약속한 경우에만 `validate_title.py --answer-count N`을 추가한다. 제목·도입·마무리 장치 검증 가운데 하나라도 실패하면 완성본처럼 제시하지 않는다.

## 발행 차단 조건

- 독자 고민 인용이 선택 원문의 실제 고민과 다르거나 2~3개 범위를 벗어남
- 인용 고민들이 제목과 연결되지 않거나 같은 뜻을 반복함
- 해결 방향 예고가 없거나 첫 정보 본문 뒤에 나옴
- 최근 3개 글 중 하나와 `semanticTopicId` 또는 핵심 대상이 같거나, 같은 대상·검색 의도 또는 동의어 키가 겹치는 주제
- 선택한 위석 한 편과 다른 글의 주제·독자 고민·핵심 내용·제목 장치·도입 설득·정보 흐름·마무리를 혼합함
- 선택 결과에 `sourceProseWithheld=true`·`contentAtomCoverageRequired=true`·`referenceEditorialReasoningEnabled=true`·`goldhandFactReplacementRequired=true`가 없거나, 선택된 `referenceWritingIntelligence`를 읽지 않고 초안을 시작함
- 선택 레퍼런스의 `orderedContentAtoms`를 빼거나 원자 ID 순서를 임의로 뒤섞거나, 완성 본문에 대응되지 않은 원자가 남음
- 위석 완성 문장·고유 비유·사례를 복사하거나 7어절 이상 연속 일치함. 반대로 질문의 기능·구체성·리듬·설득 심리를 전혀 해석하지 않고 금손 공통 템플릿만 덮어쓴 경우도 실패
- `goldhand-official-voice-v1` 누락, 1인칭·대화형 종결·솔직한 연결·생활 장면 부족
- `natural-speech-rewrite-protocol-v1` 누락, SEO·HTML 없는 평문 초안과 별도 발화 편집 패스 미실행
- `writing-voice-final-rehear-v1` 누락, 완성 산문·SEO 뒤 전체 재청취 미실행, `data-writing-voice-status=pass` 누락, 수정 전후 문단·표현의 일 기록 불일치
- writing-voice 검수에서 문단·사실·의료 경계·확신 강도·레퍼런스 제목·도입·흐름·마무리 장치·키워드 약속·고정 HTML 구성을 바꾸거나, 고칠 곳이 없는데 억지로 문장을 수정함
- `제가·사실·그런데·~죠`를 검수 횟수에 맞춰 끼워 넣거나, 대칭형 안전 문장·치료명 나열·`확인합니다·봅니다·정합니다` 반복으로 전개함
- 열 문단이 넘는 평문에서 같은 문장 수의 문단 비율이 88%를 넘거나 같은 문장 수가 7문단 이상 연속됨, `먼저` 6회 이상, `반대로` 3회 이상, 여러 원고에 같은 8어절 문장 틀이 남음
- `ㅎㅎ`, `ㅠㅠ`, `^^`, 이모지 또는 등록된 AI 템플릿 문장 사용
- 실제 원장이 환자에게 입으로 말하지 않을 번역투 명령문, 독자 숙제형 행동 유도, 감성적·은유적 결론, 추상 명사로 마무리하는 작문체 사용
- 예시 문구만 다른 단어로 치환하고 `기록·관찰·회상 권유 → 실마리·단서·출발점·첫걸음 같은 추상 보상` 구조를 그대로 유지함
- 필요한 지시를 `~하는 편이 좋습니다`, `~해 보셔도 좋습니다`, `하나의 방법입니다`처럼 지나치게 완곡하게 만들어 환자가 무엇을 해야 하는지 흐림
- `이번 글에서는`, `이 글을 통해`, `함께 살펴보겠습니다`처럼 실제 진료 대화가 아니라 블로그 형식을 설명하는 문장으로 내용을 시작하거나 끝냄
- `기억해 주세요`, `잊지 마세요`, `도움이 되었으면 합니다`처럼 교훈·다짐·여운을 만들기 위한 결말
- 레퍼런스 업체명·프로그램·경력·성과·고유 수치·사진·연락처를 옮김
- 업체소개형·사례공유형·스토리텔링형·일상글·공지
- 레퍼런스 업체 사실·문장·사례·사진·연락처 혼입
- 금손 사실과 사용자 최신 정정 위반
- 합성 사례·허위 환자 발화·효과 보장·강한 내원 유도
- 제목 약속과 실제 답 불일치
- 선택한 `titleMechanism`과 제목 장치가 다르거나, 제목이 실제 답 개수를 약속했는데 숫자와 번호 소제목 개수가 다름
- `solution-preview`의 선택 도입 장치·주제별 보상·도입 하이라이트 누락. 분 단위 장치를 선택했는데 1~5분 숫자·읽기 표현·주제별 보상 중 하나가 없거나, 분 단위 장치를 선택하지 않았는데 관성적으로 3분 문장을 삽입함
- 선택한 `closingMechanism`과 마무리 감정·회수 내용이 다르거나 모든 글을 같은 중립 문장으로 끝냄
- callilife 주제 일치 작품 검색 누락, GPT Image 생성본 3~4개 누락, OGQ 미리보기·원본을 완성 글에 직접 사용, 생성본 절대 경로·작품 상세 URL·사용자 소유 확인·의학 정보 및 배치 보존·허용 변형 모드 누락, 인물 중심 그림의 그림체를 바꾸거나 비인물 중심 그림의 핵심 내용·배치를 바꿈
- GPT Image 생성본을 최종 article·복사용 HTML에서 누락하거나, 복사용 HTML에 HTTPS 게시 URL 대신 로컬 경로·`data:image`를 남기거나, `data-image-placement`·`data-image-anchor` 없이 소제목 직후·관련 없는 문단 뒤·글 끝에 몰아서 배치함
- 실제 진료 사진이 1~2장 범위를 벗어남, 1장인데 원장 소개표 위가 아니거나 2장인데 마무리 진료 구간이 아님, 설명 본문 중간에 분산함, 원장-환자 치료·진찰·상담·검사 장면이 아님, 진료 사진 ID·해시·시각 검수·`approvedAlt` 누락. `before-credential`에서만 `placementTerms`·anchor·바로 앞 문단 대응 누락도 실패
- 마무리 신뢰 사진이 별도 1장이 아니거나 진료 사진 수량으로 대체됨, `closingTrustEligible`이 아닌 사진 사용, `credential-trust-context`·`closingTrustPlacementTerms`·`closingTrustApprovedAlt`·`closingTrustContextText` 누락, 진료시간 안내 전 마지막 이미지가 아님, 또는 바로 직전 완료 글의 별도 신뢰 사진 ID·해시를 재사용함
- 실제 사진이나 GPT 이미지 아래에 `<figcaption>` 또는 별도 설명·출처 문단을 표시함
- 지역·업종 키워드를 글의 주제로 오인해 한의원 선택법·추천 이유·업체 비교를 설명하거나, 지역명·상호를 가렸을 때 실질적인 건강 정보가 남지 않음
- 1,400~1,800자 또는 제목 1회·본문 2~3회 SEO 실패
- 일반 본문이 2~3줄 묶음이 아니거나, 한 줄이 공백 제외 24자를 초과하거나, 묶음 뒤의 빈 줄이 누락됨
- 인용구·인사·소제목·본문 중 하나라도 중앙 정렬이 아님
- 노란 하이라이트 정확히 3개, 밑줄 2~3개, 빨간 글씨 1~2개, 합계 6~8개 계약 위반 또는 강조 효과 중첩
- 가치입증 6행의 문구·순서 변경 또는 주제별 후보 선택
- `금손한의원 소개` 가치입증 표가 `solution-preview`보다 앞에 있거나 첫 정보 본문의 구분선·소제목·설명 뒤에 있음
- `goldhand-naver-native-v4` 속성 누락, CSS 카드 흔적, 1행×1열 가짜 표, 표 구분선·중앙 정렬 누락, `clinic-hours` 24:38:38 폭 또는 `clinic-info` 100% 적층 행 누락, 순정 컴포넌트·표1 계약 위반, 허용 팔레트 밖의 색상 혼입
- 고정 운영정보 누락, 진료시간표에 공휴일·설·추석 행이 있거나 운영정보 표에 카카오톡·네이버 예약이 출력됨, `clinic-info` 운영정보 뒤에 `<함께 보면 좋은 글>`·최신 블로그 링크·네이버 지도·해당 자리표시자 중 하나라도 추가됨, 또는 제작 지시·출처 목록 노출

## 완료 보고

최종 응답에는 제목, `콘텐츠·편집 레퍼런스` 링크 한 편, 실제로 옮긴 제목·도입·흐름·마무리 장치, 금손 공식 말투·생활어 검수, `writing-voice` 최종 전체 재청취와 구조·사실 보존 통과, 최근 3개 주제 및 진행 중 예약 중복 검사, 선택한 진료 사진 배치 모드와 수량, `closing-trust`라면 주제 무관 배치와 직전 글 사진 재사용 수, 별도 마무리 신뢰 사진 1장과 장면 유형·직전 글 중복 0장, 진료 사진 자리에 로고·건물·약·장비·빈 공간 사용 0장, 설명 본문 GPT Image 3~4장, 공백 제외 글자 수, 제목·본문 키워드 횟수, 내용 순서·복사 거리, 전 문단 중앙 정렬, 노란 하이라이트·밑줄·주의용 빨간 글씨, 고정 가치입증 6행, 금손 색상의 3열 진료시간표와 1열 위치·전화 정보표, `clinic-info` 이후 추가 요소 0개, 모바일 2~3줄 문단·네이버 순정 컴포넌트, 의료·사실·HTML 검사 결과와 저장 경로를 간단히 적는다.
