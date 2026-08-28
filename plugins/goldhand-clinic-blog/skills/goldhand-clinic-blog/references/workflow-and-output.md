# 실행·검수·출력 절차

## 고정 자동 작성 상태 흐름

`버전 브리핑 → 글 주제 → 메인키워드 → 제목 계약만 읽고 제목 5개 즉시 생성·빠른 검증 → 사용자 번호 선택 또는 제목 직접 입력 → 확정 제목 기준 저장 레퍼런스 여러 편의 일반 정보 검색·중복 제거 → 부족하면 한국어 네이버 백그라운드 검색 → 기존 구조용 편집 마스터 한 편 선택 → 제목 장치 대응·확정 제목 재검증 → content-sources.json과 동적 출처 차단어 검증 → 금손 사실 대응 → natural-speech-rewrite-protocol 읽기 → SEO·HTML 없는 생활어 초안 → 별도 진료실 발화 편집 → 내용 원자 전수 대응 → 내용 순서·말투·문장 중복 독립 검수 → 부분 수정 → SEO 1~2회 → 글별 마무리 소제목·핵심 회수·부담 없는 진료 안내 완성 → writing-voice 최종 전체 재청취 → 기존 구조와 사실 보존 검증 → 모바일 시각 분할 → 이미지 생성 시도 → 성공하면 full-media, 도구·호출·한도·게시 실패면 text-only-fallback → credential·순정 컴포넌트·운영정보 순서 유지 → HTML → 한 번 복붙 → 실검증 → 발행 게이트 → 이력 기록`

실행 모드 선택은 묻지 않는다. 글 주제와 메인키워드를 순서대로 한 번에 하나씩 받고, 이미 받은 값은 다시 묻지 않는다. 두 값이 모두 모이면 일반 정보 자산·편집 마스터·최근 글 이력·웹 자료를 읽지 않고 제목 후보 5개와 선택 질문을 한 번 보여 준다. 사용자가 추천 번호를 고르거나 제목을 직접 입력해 확정한 뒤에만 리서치와 편집 마스터 선택을 시작한다. 이후에는 확인된 사실이 없어 제목의 답을 만들 수 없는 경우를 제외하고 사전 질문 없이 끝까지 진행한다.

`scripts/select_general_information.py`는 `wipark-content-briefs.json`과 `user-general-information-references.json`에서 주제어가 실제로 맞는 모든 글의 일반 정보 원자를 찾는다. `원인·치료·2가지` 같은 공통 표현만 맞는 글은 제외하고, 의미가 같은 원자는 하나로 합친다. `INFO11`은 트라우마 명시 맥락, `INFO04`의 공황 원자는 정신건강 명시 맥락, `INFO10`은 갱년기 맥락에서만 연다. 불면증 자체에 관한 `INFO04-A1`·`INFO04-A3`은 불면 주제에 사용할 수 있다. 정보가 없거나 제목의 답이 부족하면 네이버를 한국어로 백그라운드 검색하며 사용자에게 다른 주제를 요구하지 않는다.

콘텐츠 정보와 편집 구조는 분리한다. 여러 저장·웹 출처의 `mergedInformationAtoms`가 사실 골격을 담당하고, `select_reference_master.py`가 고른 한 편의 `referenceWritingIntelligence`와 `flowBeats`만 **제목 심리·도입 설득·정보 공개 순서·전환·미세 표현 기능·마무리 감정**을 통제한다. `sourceProseWithheld=true`, `contentAtomCoverageRequired=true`, `sourceSentenceImitationBlocked=true`, `referenceEditorialReasoningEnabled=true`, `goldhandFactReplacementRequired=true`, `voiceProtocolId=natural-speech-rewrite-protocol-v1`, `voiceProfileId=goldhand-official-voice-v1`, `finalVoiceReviewRequired=true`가 아니면 쓰지 않는다. 꾸밈과 전체 article 구조는 기존 `goldhand-naver-native-v4` 그대로다.

사용자가 입력한 글 주제를 실제 글의 주제로 고정하고 모든 선택기에 `--topic`으로 전달한다. 메인키워드가 포괄적인 지역·업종 표현이면 키워드 자체를 글감이나 정보 검색어로 확장하지 않는다. 저장 자료가 맞지 않으면 버리고 네이버로 보충하며 사용자의 주제를 바꾸지 않는다. 추나요법·침·약침·골타·한약처럼 금손이 실제 사용하는 치료는 치료 목적·적용 기준·변화가 더딜 수 있는 조건·한계·다른 검사 우선 경계에 답한다. 위고비·마운자로처럼 일반 의료 정보로 다루는 주제는 금손의 제공 서비스로 오인시키지 않는다. 한의원 선택 기준이나 업체 추천 이유를 답으로 만들지 않는다.

사용자가 입력한 주제는 최근 완료 글과 같거나 비슷해도 그대로 작성한다. `semanticTopicId`, `primarySubjectId`, `subjectIds`, `topicIntent`, `dedupeKeys`는 완료 기록의 설명용 메타데이터일 뿐, 사용자 지정 주제·확정 제목·본문 각도를 제외하거나 바꾸는 조건이 아니다. 최근 글 이력은 공식 사진 순환과 완료 기록에만 사용한다.

- `topicSource*`, `semanticTopicId`, `primarySubjectId`, `subjectIds`, `topicIntent`, `dedupeKeys`: 사용자가 지정한 주제와 완성 글을 설명하는 호환 메타데이터. 최근 글 중복 차단에는 사용하지 않음
- `contentSources`, `mergedInformationAtoms`: 여러 관련 출처의 일반 정보와 의미 중복 제거 기록
- `editorialMasterId`, `editorialReferenceTitle`, `editorialReferenceUrl`, `editorialSourceRole`: 기존 글 구조용 단일 편집 마스터 계약
- `voiceProfileId`: 금손 공식 말투 계약. 항상 `goldhand-official-voice-v1`
- `finalVoiceReviewContractId`: 완성 산문·SEO 뒤 적용할 최종 표현 검수. 항상 `writing-voice-final-rehear-v1`
- 기존 `ideaReference*`, `writingMaster*`: 하위 호환 메타데이터일 뿐 편집 마스터와 다른 글의 말투를 섞는 권한이 없음
- `goldhand-naver-native-v4`: 고정 모바일 문단·네이버 순정 컴포넌트 계약
- 업체 사실: `references/clinic-facts.md`만 사용. 일반 의료 정보와 업체 사실을 같은 출처로 취급하지 않음

## 동일 공통 원고 A/B 최종 윤문 테스트

사용자가 같은 주제·같은 원고를 `writing-voice`와 `humanize-korean`으로 비교해 달라고 명시했을 때만 이 모드를 사용한다. 정보 출처, 편집 마스터, 편집 판단 카드, 내용 원자표, 제목, 생활어 초안, 발화 편집, SEO 완성은 한 번만 수행한다. SEO까지 끝난 동일한 `sharedBeforeBody`를 두 안에 복제한 다음 마지막 윤문기만 다르게 적용한다.

- A안: 번들 `$writing-voice`와 `writing-voice-final-rehear-v1`
- B안: 설치된 `$humanize-korean`과 `humanize-korean-final-pass-v1`. B안에서는 `$writing-voice`, A안의 수정 문장, `writingVoiceReview`를 사용하지 않는다.

A안은 `validate_final_voice_review.py`, B안은 `validate_humanize_final_review.py`로 각각 검수한다. 두 안 모두 `validate_natural_speech_suite.py --expected-count 1`과 `validate_goldhand_voice.py`를 따로 통과시킨다. 공통 초안을 의도적으로 공유하므로 두 안을 한 suite에 넣어 `cross-draft-template-copy`를 실행하지 않는다.

비교 단계의 출력은 `shared-before.md`, `writing-voice-final.md`, `humanize-korean-final.md`, 두 검수 영수증이다. 모바일 분할·이미지·표·HTML·최근 글 이력은 사용자가 선택한 한 안에만 적용한다. 사용자가 두 안을 모두 게시용으로 달라고 명시하면 같은 공통 초안을 그대로 두 건 발행하지 말고 별도 제목·내용 각도를 다시 설계해야 한다고 알린다.

## 입력 수집 규칙

한 응답에서 질문 하나만 한다.

1. 글 주제가 없으면 `작성할 글의 주제를 입력해 주세요.`
2. 글 주제가 있고 메인키워드가 없으면 `메인키워드를 입력해 주세요.`
3. 두 값이 모두 있고 확정 제목이 없으면 검증된 추천 제목 5개를 번호로 제시한 뒤 `1~5번 중 사용할 제목을 선택하거나, 원하는 제목을 직접 입력해 주세요.`
4. 사용자가 1~5번을 입력하면 해당 제목을 확정하고, 그 밖의 제목 문장을 입력하면 직접 입력 제목으로 취급
5. 확정 제목까지 있으면 질문 없이 자동 작성

글 유형, 실행 모드, 추가 사실, 이미지 방식은 묻지 않는다. 항상 정보 본문형이며 도입 질문은 2~3개다. 사용자가 이미 제목을 직접 지정했다면 추천 단계를 건너뛰고 확정한 값을 임의로 바꾸지 않는다. 직접 입력 제목이 핵심 제목 검증에 실패하면 자동 수정하지 않고 문제 하나만 알려 준 뒤 새 제목만 받는다.

## 제목 추천·선택 규칙

- `assets/title-recommendation-contract.json`을 단일 기준으로 사용한다.
- 제목 확정 전에는 일반 정보 자산, 편집 마스터, 최근 글 이력, 웹 자료를 읽지 않는다. 추천 JSON은 `workflowStage=title-first`이며 `referenceMasterId`와 `titleMechanismId`를 넣지 않는다.
- 추천 제목은 정확히 5개이며 모두 정확 메인키워드로 시작하고 공백 제외 30자 이내다.
- 각 후보는 독자에게 돌아올 이득 또는 피할 손해가 바로 보이는 강한 표현과, `11년차` 또는 `1가지·2가지·3가지` 숫자 장치를 함께 사용한다.
- 다섯 개 중 `11년차` 후보는 최소 1개, 1~3가지 후보는 최소 3개다. 숫자 답을 약속한 후보의 `answerCount`는 제목 숫자와 같아야 한다.
- 각 후보에는 `readerStake=benefit|loss-prevention`만 내부적으로 기록한다. 제목 장치와 편집 마스터는 아직 정하지 않는다. 숫자 약속의 실제 답은 제목 확정 뒤 리서치에서 확보하고 같은 수인지 재검증한다.
- `scripts/validate_title_recommendations.py` 통과 전에는 후보를 사용자에게 보여 주지 않는다.
- 추천 제목을 고르면 해당 문구를 그대로 확정한다. 직접 입력 제목은 정확 문구를 보존하되 먼저 메인키워드 시작·공백 제외 30자·근거 수치·금지 표현을 검사한다. 리서치와 편집 마스터 선택 뒤 숫자 답 개수·제목 장치까지 다시 검사하며, 실패해도 제목을 임의로 고치지 않는다.

## 최근 3개 이력과 사용 범위

기본 파일은 사용자별 로컬 경로 `~/.codex/state/goldhand-clinic-blog/recent-articles.json`이다. 플러그인 소스나 설치 캐시에 상태를 저장하지 않는다.

이 파일은 완료 기록과 공식 사진 순환을 위한 상태다. 같은 주제·질환·치료·독자 의도가 이미 기록되어 있어도 사용자가 다시 지정하면 그대로 작성한다. 이력을 읽어 새 주제를 요구하거나 제목을 바꾸거나 다른 본문 각도로 돌리지 않는다.

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

새 이력은 스키마 5로 저장하며, 예전 스키마 1·2·3·4 이력은 호환을 위해 제목·주제·키워드에서 설명용 의미 서명을 추론해 읽는다. 해당 사진 이력이 없는 예전 항목은 빈 목록으로 취급한다. 주제·레퍼런스·제목 장치는 최근 이력과 겹쳐도 허용한다. `before-credential` 진료 사진과 별도 마무리 신뢰 사진은 바로 직전 완료 글 1편과 겹치지 않게 하며, `closing-trust` 진료 사진은 직전 글 미사용 사진을 우선하되 두 장이 안 되면 승인 사진을 재사용한다.

## 독립 검수 입력

검수 패스에는 다음만 전달한다.

1. 확정 제목과 정확 메인키워드
2. 사실 팩
3. 확정 주제·제목과 편집 마스터의 질문 기능으로 쓴 대표 독자 고민 2~3개와 해결 방향 예고 문단
4. `content-sources.json`의 출처 차단 계약과 `mergedInformationAtoms` 원자 ID. 저장·웹 원문과 문장형 요약은 제외
5. `goldhand-naver-native-v4` 계약
6. `clinic-facts.md`에서만 가져온 금손 사실과 `goldhand-official-voice-v1`
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
- user-topic-overridden-by-history
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

1. 확정 제목, 메인키워드, `mergedInformationAtoms`, 단일 편집 마스터의 `flowBeats`, 사실·의료 경계, 제목·도입·마무리 장치, 기존 고정 구성 요소를 동결한다.
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
- 일반 본문 정확 키워드 1회 또는 2회
- 한 문단 한 번, 서로 다른 1~2개 역할에 자연스럽게 배치
- 표, 이미지 `alt`, 고정 정보, 연락처, CTA는 횟수에서 제외
- 부족한 횟수를 채우는 새 문장·새 요약 블록 금지
- 키워드 조사와 문장 호응이 어색하면 문단 전체를 다시 쓴다.
- SEO 횟수가 맞은 뒤 일반 본문을 의미 단위의 모바일 시각 줄 2~3개로 나눈다.
- 각 시각 줄은 공백 제외 4~24자, 각 묶음 뒤에는 빈 줄 하나를 둔다.

## HTML 조립

1. `content-sources.json`의 다중 일반 정보와 `select_reference_master.py`가 선택한 편집 마스터 한 편을 분리해 확인한다. `validate_information_sources.py`가 통과하고 `voiceProfileId=goldhand-official-voice-v1`인지 다시 확인한다.
2. 검수 완료 본문을 `<article>` 하나로 만든다. 기본 writing-voice 원고에는 `data-writing-voice-review="writing-voice-final-rehear-v1" data-writing-voice-status="pass"`를 둔다. humanize-korean 선택본에는 대신 `data-final-prose-reviewer="humanize-korean" data-final-prose-review="humanize-korean-final-pass-v1" data-final-prose-status="pass"`를 두며 writing-voice 속성을 섞지 않는다. 나머지 `data-goldhand-type="정보전달형"`, 편집 레퍼런스, 금손 말투와 `goldhand-naver-native-v4` 속성은 두 경로에서 같다.
3. 제목은 article 안에 넣지 않는다. `h1`, 고정 영문 브랜드 띠, 고정 doctor-note 카드를 만들지 않는다.
4. 독자 고민 질문 2~3개는 첫 보이는 문장으로 연속 배치하고 style 없는 `<blockquote data-reference-role="reader-question" data-question-source="representative-reader-concern" data-naver-native-component="quotation">`로 만든다. 그 뒤에만 고정 인사를 정확히 한 번 둔다. 인사를 질문 앞이나 질문 사이에 두지 않는다. 독자 고민과 고정 인사가 모두 끝난 뒤 해결 방향 예고를 무배경 산문 블록 `data-reference-role="solution-preview"`로 완성한다.
5. `solution-preview` 전체가 끝난 뒤 `credential`을 정확히 한 번 둔다. 후보를 고르지 않고 `assets/goldhand-value-proof-library.json`의 고정 6행을 같은 순서로 넣는다. `before-credential` 배치를 선택했을 때만 둘 사이에 실제 사진 1장을 허용한다. credential 다음 첫 콘텐츠 컴포넌트는 첫 정보 본문의 `divider` 또는 `section-heading`이어야 하며, 이미지·일반 본문·`article-summary`·다른 표를 사이에 끼우지 않는다. 시각 간격용 `data-preview-gap="true"`는 허용한다.
6. 첫 정보 소제목은 `data-naver-native-component="subheading"`, 그 앞 구분선은 `data-naver-native-component="divider"`를 쓴다. 구분선과 소제목을 함께 쓰면 `credential`을 첫 구분선 바로 앞에 둔다. CSS 카드와 1행×1열 가짜 표를 만들지 않는다.
7. 실제 행·열 정보에는 `data-naver-native-component="table" data-native-table-preset="naver-table1-default"`를 둔다. `credential`·`clinic-hours`·`clinic-info`는 각각 정확히 한 번 사용하고 `article-summary`는 실제 비교 정보가 있을 때만 한 번 사용한다. 모든 셀에 회색 구분선과 가로·세로 중앙 정렬을 적용한다.
8. 모든 글은 중앙 정렬하고, 노란 하이라이트 정확히 3개·밑줄 2~3개·안전 경계용 빨간 글씨 1~2개를 합계 6~8개 적용한다.
9. 일반 문단은 `data-mobile-group="true"`와 `<br>`로 2~3줄을 만들고, 직후 `<p data-preview-gap="true">&#8288;</p>`를 둔다.
10. 정보 본문 마지막에는 `neutral-close`를 정확히 한 번 둔다. 안에는 글별 `closing-heading` 소제목, 그 직후 순정 `divider`, 제목의 직접 답을 회수하는 산문, `closing-invitation`인 부담 없는 진료 안내를 순서대로 둔다. `25년 경험이 전하는 한 가지` 같은 레퍼런스 표면 문구나 동일한 내원 문장을 여러 글에 반복하지 않는다.
11~14번은 `full-media` 경로에만 적용한다. 이미지 생성 도구 부재·호출 실패·사용 한도 도달 또는 생성본 게시 실패가 생기면 성공한 일부 이미지도 모두 제거하고 article 루트에 `data-image-output-mode="text-only-fallback"`와 실제 허용 사유를 기록한다. 이때 11~14번의 이미지 수량을 맞추려 하지 않고 `<figure>`·`<img>`·`data-local-image`·캡션·깨진 자리표시자 0개로 15번부터 계속한다. 글과 HTML을 중단하거나 사용자에게 재시도·API 키·작품 링크를 요구하지 않는다.
11. `sync_official_media_assets.py --verify-only`로 `assets/media-library.json`의 113개 레코드와 `assets/official-media`의 내장 파일·SHA256이 모두 일치하고, 진료 사진 6장과 마무리 신뢰 사진 7장이 검수 풀에 잡히는지 확인한다. 새 공식 글을 인덱싱해 사진을 추가한 경우에만 동기화 모드로 번들을 갱신한 뒤 플러그인을 재배포한다.
12. 진료 사진 배치를 원장 소개표 직전 1장(`before-credential`) 또는 글마무리 2장(`closing-trust`) 중 하나로 고르고 `recommend_media.py --placement-mode 선택모드`로 내장 승인본을 고른다. `before-credential`은 바로 직전 완료 글과 겹치지 않고 이번 글의 승인 `placementTerms`와 맞는 한 장만 쓴다. `closing-trust`는 주제·질환·부위·본문 문맥을 비교하지 않고 `personInteraction: true`, `directorVisible: true`, `sceneType: director-patient-*`, 정확한 `approvedAlt`가 있는 치료·진찰·상담·검사 사진 두 장을 쓴다. 직전 글 미사용 사진을 우선하고 부족하면 직전 글 승인 사진을 재사용한다. 전체 승인 진료 사진 풀 자체가 두 장 미만이면 발행을 멈추지 않고 텍스트 중심 HTML로 전환한다.
13. 진료 사진과 별도로 `recommend_closing_trust_media.py --json`으로 `closingTrustEligible: true`인 원장·협약·수료증·기부·봉사 사진 1장을 고른다. 바로 직전 완료 글의 `trustMediaIds`·`trustMediaHashes`는 제외한다. 별도 소개·맥락·캡션 문장 없이 `data-trust-photo="true" data-trust-photo-slot="closing-credential-trust" data-image-placement="closing-credential-trust"`로 넣고, 진료시간 안내 전 마지막 이미지로 둔다. 이 1장은 진료 사진 수량을 채우지 않는다.
14. 모든 공식 사진은 선택과 무결성 검사에는 플러그인 내장 파일을 사용하고, 네이버 HTML에는 같은 레코드의 **금손한의원 원본** HTTPS URL을 `src`와 `data-reference-source-url`에 함께 넣는다. 진료 사진은 `data-real-photo`, 마무리 신뢰 사진은 `data-trust-photo`로 분리하고 정확한 origin·ID·SHA256을 표시한다. `before-credential` figure에만 `data-image-placement="after-related-paragraph"`와 승인 anchor를 두고 `placementTerms`·`approvedAlt`를 맞춘다. `closing-trust` 두 figure는 anchor 없이 `data-image-placement="closing-clinical-gallery"`와 정확한 `approvedAlt`를 쓴다. 마무리 신뢰 사진은 관련 문단이나 anchor 없이 `data-image-placement="closing-credential-trust"`와 정확한 `closingTrustApprovedAlt`를 쓴다. GPT Image 3~4장은 첫 두 개 설명 섹션에만 둔다. 모든 이미지에서 `<figcaption>`과 이미지 앞뒤 설명·출처 문단을 만들지 않는다.
15. 고정 문의·운영정보는 중앙 정렬한 `진료시간 안내` 제목, `data-native-table-purpose="clinic-hours"`인 3열 표, `data-goldhand-role="contact" data-reference-role="contact" data-native-table-purpose="clinic-info"`인 1열 다행 표 순서로 마지막 본문 정보에 한 번만 둔다. `clinic-hours`는 제목 행과 월·수·금·화·목·토·일의 세 행만 두고 공휴일·설·추석 행은 만들지 않는다. `clinic-info`는 금손한의원 제목 행과 위치·찾아오는 길·전화 세 행만 두며 카카오톡·네이버 예약은 만들지 않는다. `clinic-hours` 열 폭은 `24% / 38% / 38%`, `clinic-info` 셀 폭은 `100%`로 고정하고 모든 셀에 `height:64px;line-height:1.8;word-break:keep-all`을 적용한다. 진료시간 표 첫 행과 위치정보 표 제목 행은 금손 골드 배경과 흰 글자로 표현한다.
16. 빌더가 `clinic-info` 운영정보 표에서 article을 끝내는지 확인한다. 운영정보 뒤에는 `<함께 보면 좋은 글>`, 최신 블로그 글 링크·카드, 네이버 지도·장소 컴포넌트, 자리표시자를 넣지 않는다. 이전 버전 HTML에 하단 묶음이 있으면 그 묶음만 제거한다.
17. HTML 전 `validate_general_information_library.py`, `validate_information_sources.py --input content-sources.json --article article.html`, 선택된 윤문기에 맞는 `validate_final_voice_review.py` 또는 `validate_humanize_final_review.py`, `validate_natural_speech_suite.py --expected-count 1`을 통과시킨다. 그 뒤 `validate_article.py --editorial-close`, `validate_reference_reconstruction.py --editorial-close`, `validate_copy_overlap.py`, `validate_goldhand_voice.py`를 모두 통과시킨다. article의 선택 윤문기 계약 ID와 pass 상태를 다시 확인한다. `full-media`이면 진료 사진 1장 또는 2장·별도 마무리 신뢰 사진 1장·GPT Image 3~4장과 각 이미지의 안전·무결성·수량·배치를 검사한다. `text-only-fallback`이면 허용 사유 정확히 1개와 이미지 요소·로컬 경로·깨진 자리 0개를 검사한다.
18. `build_naver_copy_page.py`를 실행하고 `validate_html.py`를 통과시킨다. `full-media` 빌더는 모든 로컬 이미지에 콘텐츠 해시 파일명을 부여해 금손 전용 HTTPS 호스트에 게시한다. 출력 HTML의 이미지 수가 원고와 같고 모든 `src`가 공개 HTTPS인지 확인한다. 게시 설정·배포·URL 검증이 실패하면 빌더가 `image-publication-failed`인 텍스트 중심 HTML로 자동 전환한다. 생성 단계에서 이미 실패했다면 `--text-only-fallback-reason 허용값`으로 실행한다. fallback 출력에는 이미지가 0개이고 복사 버튼이 즉시 활성화되어야 한다. 어느 경로든 `data:image/...;base64`, `file:`, 절대 로컬 경로, `사진 설명을 입력하세요.`, 빈 `se-caption`이 하나라도 남으면 실패다.
19. 브라우저에서 복사 버튼을 실제로 한 번 누른 뒤 네이버 빈 초안에 한 번만 붙여넣는다. `text/html`·`text/plain`, 입력 버퍼, 내부 검수용 `data-*` 제거, `images == imageDataLinks`, `orphanImageCaptions == 0`, `relatedLinks=0`·`maps=0`·`nativeModules=0`·`inputBuffer=true`·`requiresNativeFinisher=false`, 580px·375px 줄바꿈을 확인한다. `full-media`이면 본문 이미지 수 유지와 각 이미지가 비어 있지 않고 실제 표시되는지도 확인한다. `text-only-fallback`이면 `images=0`·`imageDataLinks=0`인 상태에서 산문·표·강조·운영정보가 그대로 복사되는지 확인한다. 글이 운영정보 표에서 끝나는지도 확인한다. 브라우저 제어가 없으면 정적 검증까지만 했다고 정확히 알린다.

## 기본 출력

- 채팅: 확정 제목과 완성 본문
- 파일: `~/Desktop/금손한의원 블로그/금손한의원_{slug}.html`
- 같은 이름이 있으면 `_2`, `_3`으로 새 파일 생성
- 본문 밖의 짧은 안내: 파일 절대경로, 검증 통과, 편집 마스터 링크, 이미지 출력 방식. fallback이면 실패 사유와 이미지 0개 HTML 통과를 함께 표시. 정보 출처 목록은 사용자가 요청할 때만 표시
- 실제로 네이버 붙여넣기까지 확인하지 못했다면 파일·정적 HTML·HTTPS 게시 검증까지만 완료했다고 한 줄로 구분

완성 응답에는 내부 ID 대신 구조에 사용한 편집 마스터 한 편을 표시한다.

```text
편집 마스터: [제목·도입·전환·마무리 구조를 참고한 글](editorialReferenceUrl)
```

이 한 편은 기존 글 구조에만 사용했고 일반 정보는 관련 출처에서 분리·중복 제거했다고 설명한다. 모든 출처의 말투·문장·업체 사실·고유 프로그램·사례·수치·이미지는 사용하지 않았고 금손 정보는 사실 팩에서만 넣었다고 밝힌다. 꾸밈은 네이버 순정 고정값이다.

완성 응답에 내부 검수 JSON, 외부 조사 출처 목록, 이미지 점수, 키워드 위치표를 기본 출력하지 않는다.
