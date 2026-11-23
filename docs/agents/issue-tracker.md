# GitHub Issues

이슈와 스펙은 `Sync22/KR_Report`의 GitHub Issues에 저장한다.
`gh`로 작업하며, 첫 쓰기 전에 `gh repo view --json nameWithOwner`로 대상을 확인한다.

- 등록 또는 발행은 `gh issue create --title "<제목>" --body-file <파일>`을 사용한다.
- 티켓 조회는 `gh issue view <번호> --json number,title,body,labels,comments`를 사용한다.
- 열린 티켓 조회는 `gh issue list --state open`에 필요한 `--label` 필터를 추가한다.
- 라벨 변경은 `gh issue edit <번호>`의 `--add-label` 또는 `--remove-label`을 사용한다.
- 종료 사유는 `gh issue comment <번호> --body-file <파일>`로 남긴 뒤 `gh issue close <번호>`를 실행한다.
- 하위 이슈와 선행 이슈는 GitHub의 하위 이슈와 의존성 기능을 사용한다.
  기능을 사용할 수 없으면 본문 상단에 `Part of #<번호>` 또는 `Blocked by: #<번호>`를 기록한다.
  선행 이슈가 모두 닫히면 티켓을 진행할 수 있다.

## Pull requests as a triage surface

**PRs as a request surface: no.**

이 값을 `yes`로 바꾼 경우 외부 PR에도 이슈와 같은 분류 라벨을 사용한다.
본문, 댓글, 변경은 `gh pr view`, `gh pr view --comments`, `gh pr diff`로 읽는다.
유형이 불명확한 `#번호`는 PR 조회 후 이슈 조회로 확인한다.

## Wayfinder

맵에는 `wayfinder:map`을, 자식 이슈에는 `wayfinder:<type>`을 붙인다.
맵 순서대로 담당자가 없고 선행 이슈가 모두 닫힌 열린 자식 이슈를 찾는다.
작업을 맡을 때 `gh issue edit <번호> --add-assignee @me`를 실행한다.
해결 내용을 댓글에 남기고 이슈를 닫은 뒤 맵에 결정 요약과 링크를 추가한다.
