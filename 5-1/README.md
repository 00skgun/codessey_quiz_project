# SQL로 만드는 나만의 데이터베이스 — 카페 주문(Cafe Order)

AI/SW 기초 · 데이터베이스와 백엔드 미션 결과물입니다.
백엔드 프레임워크 없이 **SQLite** 만으로 *데이터 모델링 → 데이터 입력 → 요구사항을 SQL로 해결* 하는 전 과정을 담았습니다.

## 1. 주제와 설계
- **주제:** 카페 주문 관리
- **DB:** SQLite 3.x (파일 기반, 서버 불필요)
- **테이블 5개:** `category`, `menu`, `customer`, `orders`, `order_detail`
- **1:N 관계 4개:** category→menu, customer→orders, orders→order_detail, menu→order_detail
- ERD: [erd.md](erd.md)

## 2. 제출물 구성
| 파일/폴더 | 설명 |
|-----------|------|
| [schema.sql](schema.sql) | 스키마 생성 (CREATE TABLE, PK/FK/제약조건) |
| [data.sql](data.sql) | 샘플 데이터 INSERT (테이블당 10행 이상) |
| [queries.sql](queries.sql) | 핵심 쿼리 17개 (기본/조인/집계/서브쿼리/수정·삭제/인덱스) |
| [erd.md](erd.md) | ERD (Mermaid + dbdiagram.io DSL) |
| [results/](results/) | 실행 결과 캡처(텍스트) |

`results/` 폴더:
- `query_results.txt` — 쿼리 17개 실행 결과

## 3. 실행 방법
```bash
# DB 생성 후 스키마 → 데이터 → 쿼리 순으로 실행
sqlite3 cafe.db ".read schema.sql"
sqlite3 cafe.db ".read data.sql"
sqlite3 cafe.db ".read queries.sql"

# 보기 좋게 결과 확인하려면 box 모드
sqlite3 -box -header cafe.db ".read queries.sql"
```
> `cafe.db` 파일은 위 명령으로 언제든 재생성됩니다(저장소에는 포함하지 않음).

## 4. 쿼리 구성 (총 17개, 요구 15개 충족)
| 범주 | 개수 | 쿼리 |
|------|------|------|
| 기본 조회 (WHERE/ORDER BY/LIMIT) | 4 | Q1~Q4 |
| 조인 (INNER×3, LEFT×1) | 4 | Q5~Q8 |
| 집계 (COUNT/SUM/AVG + GROUP BY) | 4 | Q9~Q12 |
| 서브쿼리 | 2 | Q13~Q14 |
| 수정/삭제 (UPDATE/DELETE) | 2 | Q15~Q16 |
| 인덱스 (CREATE INDEX) | 1 | Q17 |

## 5. 제약조건 충족 체크리스트
- [x] 테이블 4개 이상 → **5개**
- [x] 1:N 관계 2개 이상 → **4개**
- [x] 각 테이블 PK 보유
- [x] FK 2개 이상 → **4개** (`menu`, `orders`, `order_detail`×2)
- [x] NOT NULL 제약 (예: `menu.name`, `customer.name`, `orders.customer_id`)
- [x] UNIQUE 제약 (`category.name`, `customer.phone`)
- [x] FK 실제 동작 — `PRAGMA foreign_keys = ON` 으로 없는 값 참조 시 차단
- [x] 각 테이블 10행 이상 (category 10 / menu 15 / customer 12 / orders 14 / order_detail 30)
- [x] 뷰·프로시저·트리거 미사용

## 6. 과제 목표 — 핵심 개념 요약
- **DB가 엑셀과 다른 점:** 데이터를 역할별 테이블로 나누고 **관계(FK)** 와 **규칙(제약조건)** 으로 묶어, 중복 없이 무결성을 지키며 저장·조회한다. (예: 메뉴 정보를 주문마다 반복 입력하지 않고 `menu` 한 곳에 두고 `order_detail`이 `menu_id`로 참조)
- **PK / FK:** PK는 행을 유일하게 식별하는 키, FK는 다른 테이블의 PK를 가리켜 **1:N 관계**를 만든다. (한 명의 customer ↔ 여러 orders)
- **SELECT/INSERT/UPDATE/DELETE:** 각각 조회 / 입력 / 수정 / 삭제에 사용.
- **JOIN + GROUP BY:** 흩어진 테이블을 연결(JOIN)해 한 번에 뽑고, 기준 컬럼으로 묶어(GROUP BY) 합계·평균 같은 집계를 낸다.
- **인덱스:** 자주 검색·조인하는 컬럼(예: `orders.customer_id`)에 인덱스를 두면 풀 스캔 없이 빠르게 찾는다. Q17의 실행계획에서 `SEARCH ... USING INDEX` 로 확인됨.

## 7. DB 전용 문법 표기
표준 SQL 위주로 작성했으며, SQLite 전용 문법은 해당 위치에 주석으로 명시했다.
- `PRAGMA foreign_keys = ON;` — SQLite는 FK가 기본 OFF라 활성화 필요
- `AUTOINCREMENT`, `datetime('now','localtime')`, `strftime('%Y-%m', ...)` — SQLite 날짜/키 문법
