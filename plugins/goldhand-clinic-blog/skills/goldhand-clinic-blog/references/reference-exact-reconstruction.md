# 레퍼런스 1편 정밀 재현 계약

본문까지 검토한 위석부부한의원 정보글 한 편을 주제·독자 고민·핵심 일반 정보·제목 심리·도입 설득·정보 공개 순서·전환·미세 표현 기능·마무리 감정의 콘텐츠·편집 레퍼런스로 고정한다. 다른 글을 끼우지 않는다. 원문 완성 문장은 복사하지 않고 금손 공식 `goldhand-official-voice-v1`로 생활어 자연화하며, 꾸밈은 `goldhand-naver-native-v4`로 고정한다.

## 핵심 정의

`레퍼런스 방식처럼 쓴다`는 말은 제목만 비슷하게 만드는 것이 아니다. 선택한 원문 한 편의 다음 내용 요소를 같은 순서로 재현한다.

- 고정 인사 앞 또는 뒤에 놓이는 대표 독자 고민 인용 2~3개
- 마지막 고민 뒤에서 무엇을 풀어줄지 예고하는 자연스러운 산문 문단
- 질문·인사·해결 방향 예고가 모두 끝난 뒤, 첫 정보 본문 직전에 고정되는 금손한의원 소개 표
- 인사, 배경, 권위, 직접 답이 나오는 순서
- 제목의 숫자·권위·대비·지식 공백·모순이 독자에게 작용하는 이유
- 구체적인 읽기 비용이나 다른 도입 장치가 주제별 보상으로 이어지는 방식
- 인용문, 질문, 소제목이 나오는 기능적 위치와 빈도
- 생활 장면, 반론 인정, 결론 우선, 대비 같은 미세 표현 기능
- 사진이 논리 사이에 들어가는 위치. 금손 완성 글에는 보이는 이미지 캡션을 만들지 않음
- 증거, 솔직한 한계, 구체적 회수, 감사나 안도 같은 마무리 감정의 위치

레퍼런스 원문의 HTML이나 네이버 `se-*` 클래스를 복사하지 않는다. 그 구조를 평범한 인라인 HTML로 다시 만들고, `data-reference-role`로 각 블록의 역할을 기록한다.

## 반드시 바꾸는 것

다음은 모두 금손한의원 자료 또는 새 문장으로 교체한다.

- 업체명, 대표자, 지역, 업력, 수치, 성과
- 독자 고민과 질문
- 사례, 대화, 직접 인용, 개인 경험
- 서비스·시술·가격·운영 설명
- 사진, 지도, 연락처, CTA

어느 콘텐츠 레퍼런스든 업체의 의학 주장, 경력·성과 수치는 근거가 아니다. 완성 원고의 업체 정보·원장 경험·사례는 금손한의원 자료만 사용한다. 위석에서 가져오는 의료 정보는 검토 브리프의 일반 정보이며, 변동 가능하거나 고위험인 내용은 필요한 권위 자료로 확인한다. 제목·도입·흐름·표현 기능은 `reference-writing-intelligence.json`에서 해석하고, 문장 호흡과 종결어미는 그 기능을 지우지 않는 범위에서 금손 공식 말투로 자연화한다.

레퍼런스의 고유 문장을 일부 단어만 바꿔 사용하지 않는다. 문장은 금손한의원 사실 팩에서 새로 쓰고 일반 용어를 제외한 7어절 이상 연속 일치를 차단한다. 도입 인용 2~3개는 실제 환자의 발화를 옮긴 것이 아니라 검색 독자의 대표 고민으로 표시하며, 실제 환자가 말했다고 서술하지 않는다.

## 한 편만 선택

완성 `<article>`에 다음 속성을 둔다.

```html
<article
  data-goldhand-type="정보전달형"
  data-editorial-mode="reference-reasoning-goldhand-adaptation"
  data-editorial-master-id="WP224320052203"
  data-content-reference-source="https://blog.naver.com/wi-parkclinic/224320052203"
  data-editorial-reference-source="https://blog.naver.com/wi-parkclinic/224320052203"
  data-editorial-source-role="editorial-reasoning-content-flow-and-expression-principles"
  data-reference-writing-profile="INFO01"
  data-reference-writing-intelligence="goldhand-reference-writing-intelligence-v1"
  data-title-mechanism="candid-limit-plus-two-self-check-traits"
  data-closing-mechanism="two-condition-recap-and-shared-role"
  data-goldhand-voice-profile="goldhand-official-voice-v1"
  data-writing-voice-review="writing-voice-final-rehear-v1"
  data-writing-voice-status="pass"
  data-goldhand-design-system="goldhand-naver-native-v4">
  <blockquote data-reference-role="reader-question"
    data-question-source="representative-reader-concern"
    data-naver-native-component="quotation">첫 번째 대표 고민</blockquote>
  <blockquote data-reference-role="reader-question"
    data-question-source="representative-reader-concern"
    data-naver-native-component="quotation">두 번째 대표 고민</blockquote>
  <p data-reference-role="greeting-authority">안녕하세요, 금손한의원 박준희 원장입니다.</p>
  <section data-reference-role="solution-preview"
    data-intro-persuasion-device="candid-limit-before-benefit"
    data-reader-payoff="치료 뒤 다시 아픈 두 생활 조건">이번 글에서 풀 범위와 치료 뒤 다시 아픈 두 생활 조건을 예고하는 산문 문단</section>
  <table data-reference-role="credential-proof"
    data-native-table-purpose="credential"
    data-naver-native-component="table"
    data-native-table-preset="naver-table1-default">
    <!-- 금손한의원 소개 제목 1행 + 고정 가치입증 6행 -->
  </table>
  <hr data-reference-role="divider" data-naver-native-component="divider">
  <h2 data-reference-role="section-heading" data-naver-native-component="subheading">첫 정보 본문 소제목</h2>
```

편집 마스터 ID나 URL이 둘 이상 섞이면 발행하지 않는다. 기존 레이아웃 호환 ID가 있더라도 본문 편집 마스터는 `data-editorial-master-id` 한 편뿐이다. 다른 레퍼런스의 색상이나 카드를 가져오는 것도 금지한다.

## 제목과 본문 분리

네이버 제목 입력란에 넣을 제목은 복사 대상 `<article>` 안에 다시 넣지 않는다. `h1`, 브랜드 영문 띠, 별도의 표지 카드가 본문 첫머리에 생기면 실제 네이버 발행 시 제목이 두 번 보이고 AI 템플릿처럼 보이기 쉽다.

- 제목: 빌더의 `--title` 값과 채팅 결과로 별도 제공
- 복사되는 article: 레퍼런스 첫 본문 컴포넌트부터 시작
- article 안의 `h1`과 `GOLDHAND CLINIC` 고정 머리말: 금지

## 내용 재현과 금손 문체 적용

1. 선택기의 `topic`, `readerConcerns`, `orderedContentAtoms`, `referenceWritingIntelligence`, `approvedWritingLessons`, `blockedFromSource`를 먼저 읽는다. 원문의 완성 문장은 분석·복사 거리 대조 외의 초안 재료로 쓰지 않는다.
2. `reference-editorial-reasoning.md`의 판단 카드로 제목 장치의 심리, 도입 장치와 주제별 보상, 흐름 비트, 미세 표현 기능, 원문 사실 슬롯의 교체·생략, 마무리 감정을 결정한다.
3. 질문 2~3개를 고정 인사 앞이나 뒤에 둔다.
4. 질문과 고정 인사를 모두 마친 뒤, 첫 정보 소제목 전에 선택된 도입 장치와 보상이 보이는 `solution-preview`를 한 번 완성한다.
5. 완성된 `solution-preview` 뒤 `credential` 표를 정확히 한 번 둔다. `before-credential` 실제 사진 1장 구성에서만 둘 사이에 그 사진을 허용한다. 그 다음 첫 콘텐츠 컴포넌트는 첫 정보 본문의 `divider` 또는 `section-heading`이어야 한다. 이 고정 소개 위치는 편집 마스터의 다른 역할 순서를 바꾸지 않으며 모든 글에 우선 적용한다.
6. 각 `orderedContentAtoms[].id`와 `flowBeats[].id`에 금손 사실, 권위 자료, 환자 장면, 다음 문단으로 넘어갈 이유를 대응시킨다.
7. `natural-speech-rewrite-protocol.md`의 분리 패스로 설득 기능을 유지한 모든 문장을 `goldhand-official-voice-v1`로 새로 쓴다. SEO까지 반영한 뒤 `final-writing-voice-review.md`의 최종 전체 재청취로 표현만 국소 수정하고 구조·사실 보존을 검증한다. 통과한 일반 본문만 의미 단위의 모바일 시각 줄 2~3개로 나눈다.
8. 매 절마다 `원인-설명-예외-자가관리`를 기계적으로 반복하지 않는다. 선택한 원문의 진행 방식과 전환 논리를 따른다.
9. `첫째, 둘째, 셋째`, `핵심은`, `정리하면`을 자동으로 반복하지 않는다. 선택 프로필에서 같은 기능을 채택했을 때만 사용한다.
10. 박준희 원장의 확인된 태도와 판단은 일반 본문 속 자연스러운 1인칭으로 쓴다. 별도의 `박준희 원장의 판단` 카드로 고정하지 않는다.
11. 도입과 각 절 끝에서 앞 문장을 다시 요약하지 않는다. 선택 흐름 비트의 전환으로 다음 정보에 진행한다.
12. 정규화된 `topicIdea`의 추상 표현을 제목이나 소제목으로 전용하지 않는다.

## 고정 꾸밈 적용

1. 모든 글에 `data-goldhand-design-system="goldhand-naver-native-v4"`을 둔다.
2. 독자 질문은 중앙 정렬만 지정한 네이버 순정 blockquote, 소제목 사이는 순정 hr, 정보는 구분선과 중앙 정렬을 적용한 순정 표1을 쓴다.
3. 해결 방향 예고와 소제목에는 배경·테두리·padding을 넣지 않는다. `data-goldhand-box`, 1행×1열 가짜 표, 둥근 카드, 그림자, 강조선은 금지한다.
4. `article-summary` 표는 실제 비교 정보가 있을 때만 쓰며 첫 행에만 금손 골드·흰 글자를 쓴다. 표와 산문에서 같은 의미를 반복하지 않는다.
5. `credential`은 “금손한의원 소개”와 고정된 짧은 경력·강점 6행을 넣은 1열 다행 표다. 질문·인사·완성된 `solution-preview` 뒤이자 첫 정보 본문 `divider`·`section-heading` 앞에 정확히 한 번 고정하며, 다른 콘텐츠를 사이에 끼우지 않는다. 시각 간격용 `data-preview-gap="true"`만 허용한다. 모든 표의 셀에 `1px solid #D6D6D6`과 가로·세로 중앙 정렬을 적용한다.
6. 인용구·인사·소제목·본문까지 모든 글을 중앙 정렬하고, 노란 하이라이트 정확히 3개·밑줄 2~3개·안전 경계용 빨간 글씨 1~2개를 합계 6~8개 사용한다.
7. 일반 본문은 `data-mobile-group="true"`를 두고 `<br>`로 2~3줄을 만든다. 한 줄은 공백 제외 4~24자이며 각 묶음 다음에 `data-preview-gap="true"`를 둔다.
8. 이미지 위치는 원문의 논리적 슬롯을 따른다. 이미지 자체는 금손 공식 블로그의 `safeAuto: true` 자산 또는 사용자 제공 파일만 사용한다.
9. 안전한 관련 이미지가 부족하면 슬롯을 비운다. 레퍼런스의 이미지 개수를 맞추려고 무관한 금손 사진이나 레퍼런스 사진을 넣지 않는다.
10. 연락처는 레퍼런스에 따라 바꾸지 않는다. `진료시간 안내` 제목 아래 `clinic-hours` 3열 표를 `24% / 38% / 38%` 폭으로 두되 월·수·금·화·목·토·일만 표시하고 공휴일·설·추석 행은 만들지 않는다. 이어서 금손 골드 제목띠와 위치·찾아오는 길·전화만 한 행씩 쌓은 `clinic-info` 1열 표를 한 번만 두며 카카오톡·네이버 예약은 출력하지 않는다.

## 발행 전 대조

- 한 줄 요약만 보고 재현했다고 판단하지 않는다.
- `<article>`의 편집 마스터 ID, 유형, 원문 URL이 프로필과 일치해야 한다.
- `data-reference-writing-profile`, 제목 장치, 도입 장치와 보상, 마무리 장치와 회수 문구가 선택된 편집 판단 프로필과 일치해야 한다.
- `data-writing-voice-review="writing-voice-final-rehear-v1"`와 `data-writing-voice-status="pass"`가 있어야 하며 최종 재청취에서 내용·순서·사실·의료 경계·확신 강도를 바꾸지 않아야 한다.
- `reader-question`은 선택 원문의 실제 고민을 바꿔 쓴 2~3개, `solution-preview`는 정확히 1개이며 마지막 질문 뒤·본문 전에 와야 한다.
- `credential`은 질문·인사·완성된 `solution-preview` 뒤에 정확히 한 번 있고, 첫 정보 본문 `divider` 또는 `section-heading` 바로 앞의 콘텐츠 컴포넌트여야 한다.
- `data-reference-role` 순서가 프로필의 필수 순서를 포함해야 한다.
- `goldhand-naver-native-v4` 속성, 허용 팔레트, 순정 컴포넌트와 표1 계약을 만족해야 한다.
- 일반 본문이 모두 2~3줄 의미 묶음이며 묶음 뒤에 빈 줄이 있어야 한다.
- 고정 금손 헤더, 영문 브랜드 띠, doctor-note 카드, CSS 박스가 없어야 한다.
- 편집 레퍼런스 업체의 상호·인명·지역·연락처·경력·성과·프로그램·사례·사진 URL이 없어야 한다.
- 일반 용어를 제외한 원문 7어절 연속 일치와 고유 문장 복사가 없어야 한다.
- SEO·의료·금손 사실 검증도 별도로 모두 통과해야 한다.
