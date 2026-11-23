# 도메인 문서

KR_Report는 단일 컨텍스트를 사용한다.

- 탐색 전에 [프로젝트 문서 index](../codex/documentation-index.md)에서 작업에 해당하는 문서를 읽는다.
- 루트의 `GLOSSARY.md`가 있으면 이슈 제목, 설계안, 테스트명에 정의된 용어를 사용한다.
- `docs/adr/`가 있으면 작업 범위에 해당하는 ADR을 읽는다. 기존 결정과 충돌하는 제안에는 해당 ADR과 재검토 이유를 적는다.
- `GLOSSARY.md`와 ADR은 팀이 용어나 결정을 확정한 시점에 기록한다.
