# writing-voice 최종 재청취 검수

이 단계는 금손한의원 글의 **마지막 글쓰기 검수**다. 레퍼런스와 금손 사실로 내용·순서·의료 경계·제목 약속을 모두 확정하고 SEO용 정확 키워드까지 자연스럽게 넣은 다음 실행한다. 이후에는 모바일 줄바꿈, 강조, 이미지, 표, 링크, HTML 같은 제작 조립만 한다.

이 문서는 `writing-voice` 스킬을 금손한의원 글에 적용한 휴대형 계약이다. 다른 사용자 환경에 별도 스킬 파일이 없어도 같은 검수 기준이 플러그인에 남는다. `writing-voice`가 함께 제공된 환경에서는 해당 스킬을 최종 문장 검수자로 사용하고, 이 문서가 금손 글에서 바꾸면 안 되는 범위를 정한다.

## 역할을 섞지 않는다

- 금손한의원 플러그인: 무엇을 넣고 어떤 순서로 말할지 결정한다.
- 선택 레퍼런스: 제목·도입·흐름·전환·마무리의 독자 심리를 결정한다.
- 금손 사실·의학 경계: 말할 수 있는 사실과 확신의 강도를 결정한다.
- `writing-voice`: 이미 선택된 내용을 박준희 원장의 말로 더 잘 들리게 한다.

`writing-voice` 검수는 문단을 추가·삭제·이동하거나, 근거·사례·감정·경험·의도를 새로 만들지 않는다. 자연스럽게 보이게 하려고 의료 경계를 약하게 하거나 단정을 세게 만들지도 않는다.

## 검수 전 동결값

아래 항목을 내부적으로 잠근다.

1. 확정 제목과 메인키워드
2. `orderedContentAtoms`와 `flowBeats`의 순서
3. 금손 사실, 일반 의학 정보, 예외와 안전 경계
4. 선택한 제목·도입·마무리 장치와 주제별 보상
5. 독자 고민, 소제목, 문단, 표, 이미지 앵커의 순서
6. 고정 가치입증 6행, 운영정보, `clinic-info` 이후 추가 요소 0개

최종 재청취 뒤에도 이 값은 같아야 한다. 이 값을 바꿔야만 해결되는 문제라면 문장 검수가 아니라 앞선 금손 작성 단계의 실패다. 해당 단계로 되돌려 고친 뒤 최종 재청취를 처음부터 다시 한다.

## 전체를 말하는 속도로 다시 듣기

문장 하나씩 금지어를 찾는 방식으로 끝내지 않는다. 제목부터 마무리까지 한 사람에게 설명하듯 실제 말하는 속도로 읽는다.

다음 지점을 표시한다.

- 의미 없이 문단을 잇는 상투적인 연결 문장
- 모든 문단이 같은 길이와 같은 종결로 눌린 곳
- 구체적인 환자 장면보다 블로그다운 요약이나 교훈으로 시선이 옮겨 간 곳
- 원장의 솔직한 확신·유보·주의가 무난한 공문체로 평평해진 곳
- 근거 없는 비유, 여운, 권위, 친절함을 덧칠한 곳
- 원래 살아 있던 짧은 단정, 질문, 반복, 호흡을 generic한 좋은 글로 정상화한 곳

문법적으로 더 매끈한 문장이 있다는 이유만으로 고치지 않는다. 현재 문장이 독자 관계, 확신의 강도, 강조점, 말의 호흡을 더 정확히 보여 준다면 그대로 둔다.

박준희 원장의 구체적인 낱말, 조금 비정형적인 말 순서, 짧은 반복이나 옆길이 실제 강조·유보·관계를 보여 주면 보존한다. 몇 개의 대화형 어미만 남기고 전체 자세를 generic한 친절한 전문가 말투로 바꾸면 실패다.

## 수정 방식

문제가 있는 보이는 문장만 국소적으로 고친다. 각 수정에는 `더 자연스럽게`가 아니라 표현이 수행할 일을 적는다.

좋은 설명의 예:

- 환자가 어느 동작에서 아픈지 바로 떠올리도록 추상 명사를 생활 장면으로 바꿈
- 지나치게 공손한 유보가 안전 지시를 흐려 직접적인 주의 문장으로 되돌림
- 같은 길이의 세 문장이 이어져 핵심 판단이 묻히므로 짧은 단정과 설명의 호흡을 되살림
- 원장의 확신보다 블로그 요약이 앞서 있던 문장을 독자 질문에 바로 답하도록 고침

수정이 필요하지 않으면 `no-change-needed`로 기록하고 문장을 억지로 바꾸지 않는다.

국소 수정처럼 보여도 원장의 확신, 독자와의 관계, 감정의 무게를 실질적으로 바꾸는 선택이라면 자동으로 적용하지 않는다. 정밀작성모드에서는 현재 문장과 제안 문장, 표현이 수행할 일을 보여 주고 사용자의 선택을 기다린다. 자동모드에서는 원문을 임의로 바꾸지 말고 앞선 금손 작성 단계로 돌아가 같은 사실과 구조 안에서 다시 쓴다. 그래도 해결되지 않으면 완성본으로 표시하지 않는다.

## 수정 뒤 전체 재청취

부분 수정이 끝나면 고친 문장만 보지 말고 제목부터 다시 읽는다. 다음을 모두 확인한다.

- 새 연결어가 앞뒤 문단의 리듬을 다시 평평하게 만들지 않았는가
- 독자의 고민보다 작성자의 설명 기술이 더 눈에 띄지 않는가
- 금손 특유의 구체적인 말과 솔직한 경계가 남아 있는가
- 사실·확신의 강도·의료 경계가 전과 같은가
- 내용 원자와 흐름 비트가 같은 순서로 모두 남아 있는가
- 키워드와 제목 약속이 그대로인가

내부 `speech-draft.json`의 각 case에는 다음 형태로 남긴다. `beforeBody`와 `finalBody`는 같은 수의 전체 문단이며, 실제로 달라진 문단만 `revisions`에 정확히 기록한다.

```json
{
  "title": "확정 제목",
  "finalBody": ["최종 1번 문단", "최종 2번 문단"],
  "writingVoiceReview": {
    "contractId": "writing-voice-final-rehear-v1",
    "skillName": "writing-voice",
    "stage": "after-complete-visible-prose-and-seo-before-production-assembly",
    "beforeTitle": "확정 제목",
    "beforeBody": ["검수 전 1번 문단", "최종 2번 문단"],
    "decision": "revised",
    "reviewChecks": {
      "wholeDraftReadAtSpeakingSpeed": true,
      "genericConnectiveTissueReviewed": true,
      "flattenedRhythmReviewed": true,
      "attentionAllocationReviewed": true,
      "unsupportedPolishReviewed": true,
      "distinctiveGrainPreserved": true,
      "wholeDraftReheardAfterEdits": true
    },
    "frozenMaterial": {
      "contentAndOrderPreserved": true,
      "factsAndMedicalBoundariesPreserved": true,
      "claimStrengthPreserved": true,
      "referenceMechanismsPreserved": true,
      "keywordAndTitlePromisePreserved": true,
      "htmlComponentsAndLinksPreserved": true
    },
    "revisions": [
      {
        "paragraphIndex": 1,
        "before": "검수 전 1번 문단",
        "after": "최종 1번 문단",
        "expressiveJob": "환자가 어느 동작에서 아픈지 바로 떠올리도록 추상 표현을 직접적인 말로 바꿈"
      }
    ],
    "finalStatus": "pass"
  }
}
```

수정이 없다면 `beforeBody`와 `finalBody`를 같게 두고 `decision`은 `no-change-needed`, `revisions`는 빈 배열로 둔다.

검수 기록은 `assets/writing-voice-final-review-contract.json`을 따르고 `scripts/validate_final_voice_review.py`로 확인한다. 통과한 글에만 `data-writing-voice-review="writing-voice-final-rehear-v1"`과 `data-writing-voice-status="pass"`를 표시한다. 이 속성은 제작 검수용이며 네이버 복사 본문에서는 제거한다.
