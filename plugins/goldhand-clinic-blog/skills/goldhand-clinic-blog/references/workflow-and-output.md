# 실행·검수·출력 절차

## 자동모드 상태 흐름

`모드 확인 → 메인키워드 → 최근 3개 주제·직전 1개 글의 진료 사진·마무리 신뢰 사진 이력 읽기 → 검토 완료 위석 정보글 11편 중 겹치지 않는 한 편 선택 → 문장형 원문을 숨기고 orderedContentAtoms 고정 → 금손 사실 대응 → natural-speech-rewrite-protocol 읽기 → SEO·HTML 없는 생활어 초안 → 별도 진료실 발화 편집 → 내용 원자 전수 대응 → 내용 순서·말투·문장 중복 독립 검수 → 부분 수정 → SEO 2~3회 → writing-voice 최종 전체 재청취 → 수정 전후·표현의 일·구조와 사실 보존 검증 → 모바일 시각 분할 → 진료 사진 before-credential 1장 또는 closing-trust 2장 배치 → credential 고정 → GPT Image 3~4장 생성·설명 본문 배치 → 마무리 신뢰 사진 1장을 진료시간 전 마지막 이미지로 별도 배치 → 네이버 순정 구분선·필요한 표·운영정보에서 종료 → HTML → 한 번 복붙 → 실검증 → 발행 게이트 → 두 사진 풀의 ID·해시를 따로 이력 기록`

메인키워드 하나 외에는 사전 질문하지 않는다. 확인된 사실이 없어 제목의 답을 만들 수 없을 때만 누락값 하나를 묻는다.

`scripts/select_wipark_content_reference.py`는 본문 검토가 끝난 `wipark-content-briefs.json`의 11편만 사용한다. 최근 3개와 같은 레퍼런스·핵심 주제, 다른 진행 중 작업이 예약한 레퍼런스를 제외하고, 선택한 한 편만 **주제·독자 고민·핵심 일반 정보·제목 심리·도입 설득·정보 공개 순서·전환·미세 표현 기능·마무리 감정**을 통제한다. 선택기는 사실 골격인 `orderedContentAtoms`와 편집 판단인 `referenceWritingIntelligence`를 함께 내보내고 원문 완성 문장은 숨긴다. `sourceProseWithheld=true`, `contentAtomCoverageRequired=true`, `sourceSentenceImitationBlocked=true`, `referenceEditorialReasoningEnabled=true`, `goldhandFactReplacementRequired=true`, `voiceProtocolId=natural-speech-rewrite-protocol-v1`, `voiceProfileId=goldhand-official-voice-v1`, `finalVoiceReviewRequired=true`, `finalVoiceReviewerSkill=writing-voice`, `finalVoiceReviewContractId=writing-voice-final-rehear-v1`이 아니면 쓰지 않는다. 금손 말투는 레퍼런스 기능을 지우지 않고 문장을 생활어로 자연화하고, writing-voice는 완성 산문의 표현만 다시 듣는다. 꾸밈은 `goldhand-naver-native-v4`이다.

메인키워드가 포괄적인 지역·업종 표현이면 키워드 자체를 글감으로 확장하지 않는다. 선택한 주제의 `topicIdea`·`coverageQuestions`와 금손 `진료·콘텐츠 지도`를 연결해 하나의 구체적인 건강 문제 또는 치료 질문을 정한다. 추나요법·침·약침·골타·한약처럼 금손이 실제 사용하는 치료는 치료 목적·적용 기준·변화가 더딜 수 있는 조건·한계·다른 검사 우선 경계에 답한다. 위고비·마운자로처럼 일반 의료 정보로 다루는 주제는 금손의 제공 서비스로 오인시키지 않고, 필요한 권위 자료로 현재 정보와 안전 경계를 별도 확인한다. 한의원 선택 기준이나 업체 추천 이유를 답으로 만들지 않는다.

최근 3개 글은 제목 단어가 아니라 `semanticTopicId`, `primarySubjectId`, `subjectIds`, `topicIntent`, `dedupeKeys`로 비교한다. 같은 의미 ID 또는 핵심 대상은 바로 제외한다. 같은 대상이면서 검색 의도까지 같거나, 정규화 동의어 키의 자카드 유사도가 0.5 이상이어도 제외한다. `추나/추나요법`, `일자목/거북목`, `위고비/마운자로/GLP-1`처럼 표면 단어가 달라도 같은 묶음으로 본다. `topicCluster`는 서로 다른 세부 주제를 모두 막지 않고 다양성 순위를 조절하는 값으로만 사용한다. 새 후보가 없으면 중복 후보로 되돌아가지 않는다.

- `topicSource*`, `semanticTopicId`, `primarySubjectId`, `subjectIds`, `topicIntent`, `dedupeKeys`: 주제 선택과 최근 3개 의미 중복 방지
- `editorialMasterId`, `editorialReferenceTitle`, `editorialReferenceUrl`, `editorialSourceRole`: 선택한 위석 한 편의 주제·독자 고민·일반 정보·정보 공개 순서 계약
- `voiceProfileId`: 금손 공식 말투 계약. 항상 `goldhand-official-voice-v1`
- `finalVoiceReviewContractId`: 완성 산문·SEO 뒤 적용할 최종 표현 검수. 항상 `writing-voice-final-rehear-v1`
- 기존 `ideaReference*`, `writingMaster*`: 하위 호환 메타데이터일 뿐 편집 마스터와 다른 글의 말투를 섞는 권한이 없음
- `goldhand-naver-native-v4`: 고정 모바일 문단·네이버 순정 컴포넌트 계약
- 업체 사실·치료 답·사례·사진: 금손한의원 자료와 필요한 권위 있는 일반 의학 정보만 사용

## 정밀작성모드 상태 흐름

한 응답에서 질문 하나만 한다.

1. `메인키워드를 입력해 주세요.`
2. `select_wipark_content_reference.py --count 3`으로 최근 3개와도, 후보끼리도 의미가 겹치지 않는 주제 세 개를 고른다. 각 후보는 주제·독자 고민·핵심 내용·정보 순서를 가져올 `콘텐츠 레퍼런스` 한 편과 금손 말투로 만든 후보 제목을 함께 보여 준다.
3. 선택한 위석 원문 한 편을 콘텐츠 레퍼런스로 고정한다. 말투는 `goldhand-official-voice-v1`, 꾸밈은 `goldhand-naver-native-v4`로 고정한다.
4. `추가할 사실·원장 판단·실제 장면이 있나요? 없으면 없음이라고 적어 주세요.`
5. 플러그인 `assets/official-media`에 내장된 공식 블로그 사진 가운데 시각 검수 승인 사진을 자동 사용한다. 별도 이미지 방식이나 사용자 로컬 사진 폴더는 묻지 않는다.
6. 작성과 검수는 더 묻지 않고 끝까지 진행한다.

글 유형은 묻지 않는다. 항상 정보 본문형이며 도입 질문은 2~3개다. 사용자가 이미 제목을 직접 지정했다면 제목 선택 단계는 건너뛰고 확정한 값을 임의로 바꾸지 않는다.

## 최근 3개 이력

기본 파일은 사용자별 로컬 경로 `~/.codex/state/goldhand-clinic-blog/recent-articles.json`이다. 플러그인 소스나 설치 캐시에 상태를 저장하지 않는다.

저장 항목:

- title
- mainKeyword
- topicSourceId
- topicSourceTitle
- topicSourceUrl
- topicSourceBlogId
- topicSourceRole
- topicSourcePublishedAt
- topicSourcePostIds
- topicIdea
- coverageQuestions
- semanticTopicId
- topicCluster
- primarySubjectId
- subjectIds
- topicIntent
- dedupeKeys
- ideaReferenceId
- ideaReferenceTitle
- ideaReferenceUrl
- ideaType
- titlePatternId
- writingMasterId
- writingReferenceUrl
- editorialMasterId
- editorialReferenceTitle
- editorialReferenceUrl
- editorialSourceRole
- editorialProfileStatus
- type
- writtenAt
- realMediaIds
- realMediaHashes
- trustMediaIds
- trustMediaHashes

본문, 환자 정보, 이미지 바이너리, 외부 조사 본문은 저장하지 않는다. 진료 사진과 마무리 신뢰 사진은 중복 방지용 ID와 파일 해시만 각자 저장한다. 가장 최근 3개만 유지한다.

새 이력은 스키마 5로 저장하며, 예전 스키마 1·2·3·4 이력은 제목·주제·키워드에서 의미 서명을 추론해 읽는다. 해당 사진 이력이 없는 예전 항목은 빈 목록으로 취급한다. 주제·레퍼런스·제목 장치 중복은 최근 3개를 본다. `before-credential` 진료 사진과 별도 마무리 신뢰 사진은 바로 직전 완료 글 1편과 겹치지 않게 하며, `closing-trust` 진료 사진은 직전 글 미사용 사진을 우선하되 두 장이 안 되면 승인 사진을 재사용한다.

## 독립 검수 입력

검수 패스에는 다음만 전달한다.

1. 확정 제목과 정확 메인키워드
2. 사실 팩
3. 선택 원문의 실제 고민을 바꿔 쓴 대표 독자 고민 2~3개와 해결 방향 예고 문단
4. 선택기의 `orderedContentAtoms`와 원자 ID 순서. 위석 원문과 `orderedGeneralInformation` 문장은 제외
5. `goldhand-naver-native-v4` 계약
6. 콘텐츠 브리프에 대응시킨 금손 사실과 `goldhand-official-voice-v1`
7. SEO·HTML·모바일 줄바꿈을 적용하기 전의 생활어 초안 본문

초안 작성 패스와 발화 편집 패스를 분리한다. 발화 편집 패스는 `references/natural-speech-rewrite-protocol.md`를 읽고 각 원자 ID가 어느 문단에 남았는지 대응표를 만든다. 원자 누락, 같은 의미의 반복 문장, 대칭형 안전 문장, 치료명 나열, 검수 숫자를 채우기 위한 1인칭·접속어·대화형 어미 삽입은 모두 수정 대상으로 잡는다.

작성자의 자기평가, 예상 정답, 의심 문장 목록은 전달하지 않는다.

포괄 키워드 글은 독립 검수에서 지역명·상호·운영정보를 가린 사본도 함께 읽는다. 증상형은 원인 또는 이유·관찰 장면·실행할 관리·진료 경계가, 치료 정보형은 치료 목적·적용 전 구분·고려 상황·한계·다른 검사나 치료 우선 경계가 이해되지 않으면 `information-value-missing`으로 발행을 막는다.

검수 결과는 내부 JSON으로 관리한다.

```json
{
  "scores": {
    "titleMatch": 2,
    "factSafety": 2,
    "formulaFidelity": 2,
    "medicalSafety": 2,
    "informationProgress": 2,
    "spokenVoice": 2,
    "finalWritingVoice": 2,
    "seoReadiness": 2,
    "productionCleanliness": 2
  },
  "issues": []
}
```

`0=발행 차단`, `1=수정 필요`, `2=통과`다. 모든 점수가 2여야 한다.

주요 실패 신호:

- title-mismatch
- unsupported-claim
- formula-drift
- reader-question-count
- reader-question-title-disconnect
- solution-preview-missing
- solution-preview-after-body
- credential-intro-position
- mixed-reference-master
- editorial-source-mismatch
- editorial-beat-order
- source-copy-overlap
- reference-role-order
- naver-native-component-drift
- one-cell-fake-table
- custom-card-css
- mobile-group-line-count
- mobile-line-too-long
- reference-business-leak
- medical-guarantee
- certification-misattribution
- fabricated-case
- semantic-duplicate
- abstract-chain
- dangling-reference
- seo-damage
- voice-dropout
- goldhand-voice-profile-missing
- wipark-tone-leak
- ai-template-phrase
- literary-body-location
- abstract-gait-description
- abstract-editorial-predicate
- source-prose-exposed-to-draft
- content-atom-coverage-missing
- symmetric-caveat-chain
- repeated-clinical-predicate
- treatment-catalogue
- quota-driven-voice-signal
- paragraph-cadence-single-template
- paragraph-cadence-dominance
- paragraph-cadence-run
- priority-transition-overuse
- binary-contrast-overuse
- cross-draft-template-copy
- final-writing-voice-review-missing
- final-writing-voice-unaccounted-change
- final-writing-voice-frozen-material-changed
- final-writing-voice-generic-edit-account
- final-writing-voice-forced-edit
- emoticon-or-hashtag
- production-residue
- aggressive-cta
- fixed-info-missing
- image-privacy-risk
- generated-image-placement

## writing-voice 최종 전체 재청취

초안 발화 편집과 독립 검수가 끝난 뒤 SEO까지 반영한 완성 산문에서 실행한다. 이 단계 뒤에는 모바일 줄바꿈·강조·이미지·표·링크·HTML 조립만 남아야 한다. 자세한 판단은 [final-writing-voice-review.md](final-writing-voice-review.md)를 따른다.

1. 확정 제목, 메인키워드, `orderedContentAtoms`, `flowBeats`, 사실·의료 경계, 제목·도입·마무리 장치, 고정 구성 요소를 동결한다.
2. `writingVoiceReview.beforeBody`에 최종 검수 직전 전체 문단을 순서대로 둔다.
3. 제목부터 마무리까지 실제 말하는 속도로 읽고 generic한 연결, 평평해진 리듬, 독자 초점 이탈, 근거 없는 윤색, 원장의 확신·유보·주의가 사라진 곳을 표시한다.
4. 문제가 있는 보이는 문장만 고친다. 내용의 추가·삭제·이동과 확신 강도 변경은 하지 않는다.
5. 바뀐 문단마다 1부터 시작하는 `paragraphIndex`, 정확한 `before`, 정확한 `after`, `더 자연스럽게`가 아닌 구체적인 `expressiveJob`을 기록한다.
6. 수정이 없으면 `decision=no-change-needed`, 수정이 있으면 `decision=revised`로 둔다. 통과를 위해 억지로 한 문장을 바꾸지 않는다.
7. 수정 뒤 제목부터 전체를 다시 읽고 `reviewChecks`와 `frozenMaterial`을 모두 참으로 확인한다.
8. `scripts/validate_final_voice_review.py`와 이를 포함한 `validate_natural_speech_suite.py`가 모두 통과한 뒤에만 제작 조립으로 넘어간다.

최종 검수는 문법 교정기가 아니다. 어색함이 내용·순서·의료 판단을 바꿔야만 해결된다면 이 단계에서 강제로 고치지 않고 앞선 금손 작성 단계로 되돌린다.

## 부분 수정

- 지적된 문장과 필요한 앞뒤 문장만 고친다.
- 반복은 다른 말로 바꾸지 말고 삭제한다.
- 추상어는 사실 팩의 실제 증상·움직임으로 바꾼다. `아픈 자리`, `걷기가 달라지다`, `자세가 이어지다`, `부담이 반복되다`, `치료 방향에 차이를 만들다`처럼 환자가 바로 떠올리기 어려운 표현은 낱말만 바꾸지 말고 `아픈 곳`, `평소보다 걷기 힘들다`, `오래 같은 자세로 일하면 목이 다시 뻐근하다`처럼 문장 구조부터 생활어로 다시 쓴다.
- 근거 없는 주장은 삭제하고 필요하면 제목을 다시 검증한다.
- 문제가 없는 문단은 고정한다.
- 부분 수정은 최대 두 번, 제목·논리가 바뀐 전체 재작성은 최대 한 번으로 제한한다.

## SEO 후처리

초안이 자연스럽게 완성된 뒤에만 실행한다.

- 제목+실제 본문 공백 제외 1,400~1,800자
- 제목 정확 키워드 1회
- 일반 본문 정확 키워드 2회 또는 3회
- 한 문단 한 번, 서로 다른 2~3개 역할에 자연스럽게 분산
- 표, 이미지 `alt`, 고정 정보, 연락처, CTA는 횟수에서 제외
- 부족한 횟수를 채우는 새 문장·새 요약 블록 금지
- 키워드 조사와 문장 호응이 어색하면 문단 전체를 다시 쓴다.
- SEO 횟수가 맞은 뒤 일반 본문을 의미 단위의 모바일 시각 줄 2~3개로 나눈다.
- 각 시각 줄은 공백 제외 4~24자, 각 묶음 뒤에는 빈 줄 하나를 둔다.

## HTML 조립

1. `select_wipark_content_reference.py` 결과를 최근 3개 중복과 내용 순서에 쓴다. 선택된 `masterId` 한 편과 `voiceProfileId=goldhand-official-voice-v1`을 다시 확인한다.
2. 검수 완료 본문을 `<article data-goldhand-type="정보전달형" data-editorial-mode="reference-reasoning-goldhand-adaptation" data-editorial-master-id="WP..." data-content-reference-source="..." data-editorial-reference-source="..." data-editorial-source-role="editorial-reasoning-content-flow-and-expression-principles" data-reference-writing-profile="INFO..." data-reference-writing-intelligence="goldhand-reference-writing-intelligence-v1" data-title-mechanism="..." data-closing-mechanism="..." data-goldhand-voice-profile="goldhand-official-voice-v1" data-writing-voice-review="writing-voice-final-rehear-v1" data-writing-voice-status="pass" data-goldhand-design-system="goldhand-naver-native-v4">` 하나로 만든다.
3. 제목은 article 안에 넣지 않는다. `h1`, 고정 영문 브랜드 띠, 고정 doctor-note 카드를 만들지 않는다.
4. 독자 고민 질문 2~3개는 첫 보이는 문장으로 연속 배치하고 style 없는 `<blockquote data-reference-role="reader-question" data-question-source="representative-reader-concern" data-naver-native-component="quotation">`로 만든다. 그 뒤에만 고정 인사를 정확히 한 번 둔다. 인사를 질문 앞이나 질문 사이에 두지 않는다. 독자 고민과 고정 인사가 모두 끝난 뒤 해결 방향 예고를 무배경 산문 블록 `data-reference-role="solution-preview"`로 완성한다.
5. `solution-preview` 전체가 끝난 뒤 `credential`을 정확히 한 번 둔다. 후보를 고르지 않고 `assets/goldhand-value-proof-library.json`의 고정 6행을 같은 순서로 넣는다. `before-credential` 배치를 선택했을 때만 둘 사이에 실제 사진 1장을 허용한다. credential 다음 첫 콘텐츠 컴포넌트는 첫 정보 본문의 `divider` 또는 `section-heading`이어야 하며, 이미지·일반 본문·`article-summary`·다른 표를 사이에 끼우지 않는다. 시각 간격용 `data-preview-gap="true"`는 허용한다.
6. 첫 정보 소제목은 `data-naver-native-component="subheading"`, 그 앞 구분선은 `data-naver-native-component="divider"`를 쓴다. 구분선과 소제목을 함께 쓰면 `credential`을 첫 구분선 바로 앞에 둔다. CSS 카드와 1행×1열 가짜 표를 만들지 않는다.
7. 실제 행·열 정보에는 `data-naver-native-component="table" data-native-table-preset="naver-table1-default"`를 둔다. `credential`·`clinic-hours`·`clinic-info`는 각각 정확히 한 번 사용하고 `article-summary`는 실제 비교 정보가 있을 때만 한 번 사용한다. 모든 셀에 회색 구분선과 가로·세로 중앙 정렬을 적용한다.
8. 모든 글은 중앙 정렬하고, 노란 하이라이트 정확히 3개·밑줄 2~3개·안전 경계용 빨간 글씨 1~2개를 합계 6~8개 적용한다.
9. 일반 문단은 `data-mobile-group="true"`와 `<br>`로 2~3줄을 만들고, 직후 `<p data-preview-gap="true">&#8288;</p>`를 둔다.
10. `sync_official_media_assets.py --verify-only`로 `assets/media-library.json`의 113개 레코드와 `assets/official-media`의 내장 파일·SHA256이 모두 일치하고, 진료 사진 6장과 마무리 신뢰 사진 7장이 검수 풀에 잡히는지 확인한다. 새 공식 글을 인덱싱해 사진을 추가한 경우에만 동기화 모드로 번들을 갱신한 뒤 플러그인을 재배포한다.
11. 진료 사진 배치를 원장 소개표 직전 1장(`before-credential`) 또는 글마무리 2장(`closing-trust`) 중 하나로 고르고 `recommend_media.py --placement-mode 선택모드`로 내장 승인본을 고른다. `before-credential`은 바로 직전 완료 글과 겹치지 않고 이번 글의 승인 `placementTerms`와 맞는 한 장만 쓴다. `closing-trust`는 주제·질환·부위·본문 문맥을 비교하지 않고 `personInteraction: true`, `directorVisible: true`, `sceneType: director-patient-*`, 정확한 `approvedAlt`가 있는 치료·진찰·상담·검사 사진 두 장을 쓴다. 직전 글 미사용 사진을 우선하고 부족하면 직전 글 승인 사진을 재사용한다. 전체 승인 진료 사진 풀 자체가 두 장 미만일 때만 발행을 멈춘다.
12. 진료 사진과 별도로 `recommend_closing_trust_media.py --json`으로 `closingTrustEligible: true`인 원장·협약·수료증·기부·봉사 사진 1장을 고른다. 바로 직전 완료 글의 `trustMediaIds`·`trustMediaHashes`는 제외한다. `closingTrustContextText`와 같은 `credential-trust-context` 문단 뒤에 `data-trust-photo="true" data-trust-photo-slot="closing-credential-trust"`로 넣고, 진료시간 안내 전 마지막 이미지로 둔다. 이 1장은 진료 사진 수량을 채우지 않는다.
13. 모든 공식 사진은 선택과 무결성 검사에는 플러그인 내장 파일을 사용하고, 네이버 HTML에는 같은 레코드의 **금손한의원 원본** HTTPS URL을 `src`와 `data-reference-source-url`에 함께 넣는다. 진료 사진은 `data-real-photo`, 마무리 신뢰 사진은 `data-trust-photo`로 분리하고 정확한 origin·ID·SHA256을 표시한다. `before-credential` figure에만 `data-image-placement="after-related-paragraph"`와 승인 anchor를 두고 `placementTerms`·`approvedAlt`를 맞춘다. `closing-trust` 두 figure는 anchor 없이 `data-image-placement="closing-clinical-gallery"`와 정확한 `approvedAlt`를 쓴다. 마무리 신뢰 사진은 `closingTrustPlacementTerms`·`closingTrustApprovedAlt`·`closingTrustContextText`와 정확히 맞아야 한다. GPT Image 3~4장은 첫 두 개 설명 섹션에만 둔다. 모든 이미지에서 `<figcaption>`과 이미지 아래 설명·출처 문단을 만들지 않는다.
14. 고정 문의·운영정보는 중앙 정렬한 `진료시간 안내` 제목, `data-native-table-purpose="clinic-hours"`인 3열 표, `data-goldhand-role="contact" data-reference-role="contact" data-native-table-purpose="clinic-info"`인 1열 다행 표 순서로 마지막 본문 정보에 한 번만 둔다. `clinic-hours`는 제목 행과 월·수·금·화·목·토·일의 세 행만 두고 공휴일·설·추석 행은 만들지 않는다. `clinic-info`는 금손한의원 제목 행과 위치·찾아오는 길·전화 세 행만 두며 카카오톡·네이버 예약은 만들지 않는다. `clinic-hours` 열 폭은 `24% / 38% / 38%`, `clinic-info` 셀 폭은 `100%`로 고정하고 모든 셀에 `height:64px;line-height:1.8;word-break:keep-all`을 적용한다. 진료시간 표 첫 행과 위치정보 표 제목 행은 금손 골드 배경과 흰 글자로 표현한다.
15. 빌더가 `clinic-info` 운영정보 표에서 article을 끝내는지 확인한다. 운영정보 뒤에는 `<함께 보면 좋은 글>`, 최신 블로그 글 링크·카드, 네이버 지도·장소 컴포넌트, 자리표시자를 넣지 않는다. 이전 버전 HTML에 하단 묶음이 있으면 그 묶음만 제거한다.
16. HTML 전 완성 산문은 `validate_final_voice_review.py`와 `validate_natural_speech_suite.py --expected-count 1`을 통과시키고, 여러 후보를 생성했다면 같은 suite에 누적해 8어절 교차 복제까지 확인한다. 그 뒤 `validate_article.py --editorial-close`, `validate_reference_reconstruction.py --editorial-close`, `validate_copy_overlap.py`, `validate_goldhand_voice.py`를 모두 통과시킨다. article의 writing-voice 계약 ID와 pass 상태를 다시 확인하고 진료 사진 1장 또는 2장, 별도 마무리 신뢰 사진 1장, GPT Image 3~4장, 각 이미지 구간, 안전·무결성·수량, 별도 신뢰 사진의 직전 글 중복 0장을 검사한다. `closing-trust` 진료 사진의 직전 글 재사용 수는 허용된 회전 정보로 따로 기록한다.
17. `build_naver_copy_page.py`를 실행하고 `validate_html.py`를 통과시킨다. 빌더는 모든 로컬 이미지에 콘텐츠 해시 파일명을 부여해 금손 전용 HTTPS 호스트에 게시한다. 출력 HTML의 이미지 수가 원고와 같고 모든 `src`가 공개 HTTPS인지 확인한다. `data:image/...;base64`, `file:`, 절대 로컬 경로가 하나라도 남으면 실패다.
18. 브라우저에서 복사 버튼을 실제로 한 번 누른 뒤 네이버 빈 초안에 한 번만 붙여넣는다. `text/html`·`text/plain`, 입력 버퍼, 내부 검수용 `data-*` 제거, 본문 이미지 수 유지, `relatedLinks=0`·`maps=0`·`nativeModules=0`·`inputBuffer=true`·`requiresNativeFinisher=false`, 580px·375px 줄바꿈을 확인한다. 글이 운영정보 표에서 끝나고 다른 본문 출력이 그대로인지 확인한다. 브라우저 제어가 없으면 정적 검증까지만 했다고 정확히 알린다.

## 기본 출력

- 채팅: 확정 제목과 완성 본문
- 파일: `~/Desktop/금손한의원 블로그/금손한의원_{slug}.html`
- 같은 이름이 있으면 `_2`, `_3`으로 새 파일 생성
- 본문 밖의 짧은 안내: 파일 절대경로, 검증 통과, 선택한 단일 참고 글 링크
- 실제로 네이버 붙여넣기까지 확인하지 못했다면 파일·정적 HTML·HTTPS 게시 검증까지만 완료했다고 한 줄로 구분

완성 응답에는 내부 ID 대신 선택한 한 편을 표시한다.

```text
콘텐츠 레퍼런스: [주제·독자 고민·핵심 내용·정보 순서를 참고한 글](editorialReferenceUrl)
```

이 한 편의 주제와 핵심 내용 순서를 따랐다고 설명한다. 말투는 금손 공식 74편 기준이며, 원문 말투·문장·업체 사실·고유 프로그램·사례·수치·이미지는 사용하지 않았다고 밝힌다. 꾸밈은 네이버 순정 고정값이다.

완성 응답에 내부 검수 JSON, 외부 조사 출처 목록, 이미지 점수, 키워드 위치표를 기본 출력하지 않는다.
