# humanize-korean 최종 윤문 검수

이 문서는 사용자가 같은 금손한의원 원고를 두 가지 최종 윤문기로 비교해 달라고 명시했을 때만 읽는다. 기본 단일 원고는 기존 `writing-voice-final-rehear-v1`을 그대로 사용한다.

## 비교 입력을 고정한다

레퍼런스 선택, 제목, 독자 질문, `orderedContentAtoms`, `flowBeats`, 금손 사실, 의료 경계, 확신 강도, 정확 키워드와 완성 문단까지 먼저 한 번만 확정한다. 이 공통 원고를 `sharedBeforeBody`로 저장한 뒤 A안과 B안에 똑같이 복제한다.

- A안은 번들 `$writing-voice`와 `final-writing-voice-review.md`를 사용한다.
- B안은 설치된 `$humanize-korean`만 사용한다. B안에서는 `$writing-voice`를 호출하거나 그 수정 결과를 입력으로 쓰지 않는다.

이 방식은 최종 윤문기 차이만 비교하기 위한 것이다. 비교 중에는 레퍼런스를 두 번 예약하거나 최근 글 이력을 두 건 기록하지 않는다.

## B안 실행

1. `$humanize-korean`의 `SKILL.md`와 `references/quick-rules.md`를 읽는다.
2. 장르는 `블로그`, 강도는 `기본`, 최소심각도는 `S1`로 둔다.
3. 고유명사, 수치, 날짜, 직접 인용, 내용 앵커, 금손 사실, 의료 경계와 서법을 그대로 보존한다.
4. quick-rules ID에 실제로 매핑되는 표현만 고친다. 규칙 ID가 없는 문장은 자연스럽게 보인다는 이유만으로 바꾸지 않는다.
5. 문단을 추가·삭제·이동하지 않는다. 확정 제목, 키워드 약속, 도입·흐름·마무리 장치와 고정 제작 요소도 바꾸지 않는다.
6. 변경률은 30% 이하여야 하며, 자체검증 6항을 모두 통과해야 한다. 등급 C·D는 금손 완성본으로 쓰지 않는다.
7. `humanizeKoreanReview`에 검수 전 전체 문단, 최종 문단, 실제 변경 문단, quick-rules ID, 변경률, 등급, 자체검증과 동결값을 기록한다.

## 비교 출력

비교 단계에서는 두 평문 원고와 각 검수 영수증만 저장한다. 모바일 줄바꿈, 강조, 이미지, 표, HTML 조립과 최근 글 이력 기록은 사용자가 둘 중 하나를 선택한 뒤 선택본에만 수행한다. 두 안을 모두 게시용으로 만들라는 별도 요청이 있으면 중복 콘텐츠 위험을 먼저 알리고, 같은 공통 초안을 그대로 두 건 발행하지 않는다.

B안 검수 기록은 `assets/humanize-korean-final-review-contract.json`을 따르고 `scripts/validate_humanize_final_review.py`로 확인한다. 같은 B안은 `validate_natural_speech_suite.py --expected-count 1`과 `validate_goldhand_voice.py`에도 통과시킨다. 의도적으로 공통 초안을 쓰는 A/B 두 안은 교차 원고 복제 검사에 한 묶음으로 넣지 않고 각각 한 편씩 검사한다.

선택된 B안만 HTML로 조립할 때 article 시작 태그에 아래 세 속성을 둔다.

```html
data-final-prose-reviewer="humanize-korean"
data-final-prose-review="humanize-korean-final-pass-v1"
data-final-prose-status="pass"
```

B안에는 `data-writing-voice-review`와 `data-writing-voice-status`를 넣지 않는다.
