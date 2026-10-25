### 최건영 — DB·로그 (`00skgun`)

담당 파일: `app/database.py`, `app/crud.py`, `app/models.py`의 `ChatLog`,
`app/routers/logs.py`, `scripts/create_tables.py`, `scripts/check_logs.sql`, `docs/ERD.md`

사용자와 대화 데이터를 저장·조회하는 DB 계층과 본인 대화 기록 조회 API를 맡았다.
인증과 챗봇 담당자가 같은 DB 함수를 재사용할 수 있도록 동기 SQLAlchemy Session과
ORM 객체 반환 방식으로 조회·저장 함수의 사용 방법을 맞췄다.

- **DB 환경과 연결 기반** — Neon PostgreSQL을 제공자로 선정하고 development·production
  브랜치를 분리해 pooled 연결 정보를 임익화에게 비공개로 전달했다. SQLAlchemy·psycopg
  의존성을 추가하고, `DATABASE_URL` 환경변수를 사용하는 `engine`, `SessionLocal`,
  ORM 공통 기반인 `Base`를 구성했다.
  ([#70](https://github.com/Teamb7-1/ai-chatbot-service/issues/70),
  [#36](https://github.com/Teamb7-1/ai-chatbot-service/issues/36))
- **사용자 조회·저장** — 사용자명 또는 ID로 사용자를 조회하고, 이미 해시된 비밀번호를
  받아 사용자를 생성하는 함수를 구현했다. 저장 중 DB 오류가 발생하면 rollback한 뒤
  예외를 전달하도록 해, 실패한 작업을 되돌리고 같은 세션을 다시 사용할 수 있게 했다.
  ([#66](https://github.com/Teamb7-1/ai-chatbot-service/issues/66))
- **대화 모델과 저장** — 질문·답변, 사용자 ID, 요청 ID, 성공 여부, 오류 코드, 제공자·모델,
  소요 시간 등을 담는 11개 컬럼의 `ChatLog` 모델을 구현했다. 사용자 외래키, 상태·소요 시간
  제약, 조회용 인덱스를 정의하고, AI 성공·실패 결과를 저장하는 `create_chat_log`와
  DB 저장 성공·실패 로그를 추가했다.
  ([#36](https://github.com/Teamb7-1/ai-chatbot-service/issues/36))
- **사용자별 대화 조회** — `recent_turns`는 해당 사용자의 최근 성공 대화 n개를 선택한 뒤
  과거 → 현재 순서로 반환하도록 구현했다. 기본값은 5개이며 AI 대화 문맥 구성에 사용한다.
  `list_chat_logs`는 해당 사용자의 성공·실패 기록을 최신순으로 반환하고 `limit`·`offset`으로
  나누어 조회할 수 있게 했다.
  ([#36](https://github.com/Teamb7-1/ai-chatbot-service/issues/36))
- **본인 기록 조회 API** — 공통 인증·DB 세션 의존성을 재사용하는 `GET /api/me/chats`를
  구현했다. 로그인한 사용자 ID로만 기록을 조회하고, ORM 객체를 공통 응답 모델로 변환했다.
  DB 조회 오류는 공통 오류 응답으로 처리하도록 연결했다.
  ([#36](https://github.com/Teamb7-1/ai-chatbot-service/issues/36))
- **테스트** — DB 설정, 대화 모델, 사용자·대화 CRUD, 기록 조회 API, 초기화 스크립트의
  테스트를 추가했다. 별도 PostgreSQL을 이용하는 통합 테스트로 실제 저장·조회, 사용자별
  조회 범위와 정렬, 제약 위반 시 rollback 및 세션 재사용을 검증했다. 테스트마다 고유
  스키마와 트랜잭션으로 격리하고, `TEST_DATABASE_URL`이 없으면 DB 통합 테스트를 명시적으로
  건너뛰도록 했다.
  ([#70](https://github.com/Teamb7-1/ai-chatbot-service/issues/70),
  [#66](https://github.com/Teamb7-1/ai-chatbot-service/issues/66),
  [#36](https://github.com/Teamb7-1/ai-chatbot-service/issues/36))
- **초기화·검증 도구와 문서** — 명시적 확인 후 없는 테이블을 생성하는
  `scripts/create_tables.py`, 데이터를 변경하지 않는 확인 SQL, ERD, README의 DB 구조와
  초기화·검증 절차를 작성했다. 초기화 스크립트는 기존 테이블 구조를 변경하는
  마이그레이션 도구와 구분해 설명했다.
  ([#36](https://github.com/Teamb7-1/ai-chatbot-service/issues/36))

사용자 모델·비밀번호 해싱·인증은 임대균, AI 호출과 대화 처리 흐름은 손재현의 구현과 연결했다.
앱에 라우터를 등록하고 지난 대화 화면에 연결하는 작업, Vercel 환경변수 등록 및 실제 Neon
테이블 초기화 실행은 임익화가 담당했다.

관련 병합 PR: [DB 연결 기반 #77](https://github.com/Teamb7-1/ai-chatbot-service/pull/77),
[사용자 CRUD #85](https://github.com/Teamb7-1/ai-chatbot-service/pull/85),
[대화 DB·조회 API·검증 문서 #90](https://github.com/Teamb7-1/ai-chatbot-service/pull/90).
