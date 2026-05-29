-- =====================================================================
--  카페 주문(Cafe Order) 데이터베이스 - 핵심 쿼리 모음 (총 17개)
--  실행: sqlite3 cafe.db ".read queries.sql"   (schema/data 실행 이후)
--
--  [구성]
--   기본 조회 : Q1~Q4   (WHERE / ORDER BY / LIMIT)
--   조 인      : Q5~Q8   (INNER JOIN x3, LEFT JOIN x1)
--   집 계      : Q9~Q12  (COUNT / SUM / AVG + GROUP BY)
--   서브쿼리   : Q13~Q14
--   수정/삭제  : Q15~Q16 (UPDATE / DELETE)
--   인덱스     : Q17     (CREATE INDEX)
--
--  * 날짜 비교의 '현재 기준일'은 데이터와 맞추기 위해 2026-05-30 으로 고정.
-- =====================================================================

PRAGMA foreign_keys = ON;

-- =========================== 기본 조회 ===============================

-- Q1) [조회] 판매 중인(is_available=1) 메뉴를 가격 높은 순으로 정렬
SELECT menu_id, name, price
FROM menu
WHERE is_available = 1
ORDER BY price DESC;

-- Q2) [조회] 4500원 이상인 메뉴만 가격 오름차순 조회
SELECT name, price
FROM menu
WHERE price >= 4500
ORDER BY price ASC;

-- Q3) [조회] 가장 최근에 가입한 고객 TOP 5 (LIMIT)
SELECT name, membership, joined_at
FROM customer
ORDER BY joined_at DESC
LIMIT 5;

-- Q4) [조회] GOLD 등급 고객 목록 (이름순)
SELECT customer_id, name, phone, membership
FROM customer
WHERE membership = 'GOLD'
ORDER BY name;

-- =============================== 조인 ================================

-- Q5) [INNER JOIN] 주문 + 고객: 누가 언제 어떤 상태로 주문했는지
SELECT o.order_id, c.name AS customer, o.ordered_at, o.status
FROM orders o
INNER JOIN customer c ON c.customer_id = o.customer_id
ORDER BY o.ordered_at;

-- Q6) [INNER JOIN x3] 주문 영수증 상세: 주문-상세-메뉴 연결, 라인별 금액
SELECT o.order_id,
       c.name        AS customer,
       m.name        AS menu,
       d.quantity,
       d.unit_price,
       d.quantity * d.unit_price AS line_total
FROM order_detail d
INNER JOIN orders   o ON o.order_id   = d.order_id
INNER JOIN customer c ON c.customer_id = o.customer_id
INNER JOIN menu     m ON m.menu_id    = d.menu_id
ORDER BY o.order_id, d.order_detail_id;

-- Q7) [INNER JOIN] 카테고리별 메뉴 목록 (카테고리명 + 메뉴명 + 가격)
SELECT cat.name AS category, m.name AS menu, m.price
FROM menu m
INNER JOIN category cat ON cat.category_id = m.category_id
ORDER BY cat.name, m.price DESC;

-- Q8) [LEFT JOIN] 전체 고객의 주문 횟수 (주문 0건 고객도 0으로 표시)
SELECT c.name,
       COUNT(o.order_id) AS order_count
FROM customer c
LEFT JOIN orders o ON o.customer_id = c.customer_id
GROUP BY c.customer_id, c.name
ORDER BY order_count DESC, c.name;

-- =============================== 집계 ================================

-- Q9) [COUNT + GROUP BY] 카테고리별 메뉴 개수 (메뉴 많은 순)
SELECT cat.name AS category, COUNT(m.menu_id) AS menu_count
FROM category cat
LEFT JOIN menu m ON m.category_id = cat.category_id
GROUP BY cat.category_id, cat.name
ORDER BY menu_count DESC, cat.name;

-- Q10) [SUM + GROUP BY] 고객별 결제 총액 (취소 주문 제외)
SELECT c.name,
       SUM(d.quantity * d.unit_price) AS total_spent
FROM customer c
INNER JOIN orders       o ON o.customer_id = c.customer_id
INNER JOIN order_detail d ON d.order_id    = o.order_id
WHERE o.status <> 'CANCELLED'
GROUP BY c.customer_id, c.name
ORDER BY total_spent DESC;

-- Q11) [AVG + GROUP BY] 카테고리별 평균 메뉴 가격
SELECT cat.name AS category,
       ROUND(AVG(m.price), 0) AS avg_price
FROM menu m
INNER JOIN category cat ON cat.category_id = m.category_id
GROUP BY cat.category_id, cat.name
ORDER BY avg_price DESC;

-- Q12) [집계 + 랭킹] 가장 많이 팔린 메뉴 TOP 5 (취소 주문 제외)
SELECT m.name,
       SUM(d.quantity) AS sold_qty
FROM order_detail d
INNER JOIN orders o ON o.order_id = d.order_id
INNER JOIN menu   m ON m.menu_id  = d.menu_id
WHERE o.status <> 'CANCELLED'
GROUP BY m.menu_id, m.name
ORDER BY sold_qty DESC
LIMIT 5;

-- ============================ 서브쿼리 ===============================

-- Q13) [서브쿼리] 전체 메뉴 평균 가격보다 비싼 메뉴
SELECT name, price
FROM menu
WHERE price > (SELECT AVG(price) FROM menu)
ORDER BY price DESC;

-- Q14) [서브쿼리] 주문 기록이 한 번도 없는 고객 찾기 (NOT IN)
SELECT customer_id, name, membership
FROM customer
WHERE customer_id NOT IN (SELECT DISTINCT customer_id FROM orders)
ORDER BY customer_id;

-- ========================== 수정 / 삭제 =============================

-- Q15) [UPDATE] '캐모마일' 메뉴를 다시 판매 가능 상태로 변경
UPDATE menu
SET is_available = 1
WHERE name = '캐모마일';
-- 확인
SELECT name, is_available FROM menu WHERE name = '캐모마일';

-- Q16) [DELETE] 취소(CANCELLED)된 주문의 상세 품목 삭제
--   FK 때문에 자식(order_detail) -> 부모(orders) 순으로 지운다.
DELETE FROM order_detail
WHERE order_id IN (SELECT order_id FROM orders WHERE status = 'CANCELLED');
-- 확인: 취소 주문에 남은 상세가 0건이어야 함
SELECT COUNT(*) AS remaining_cancelled_details
FROM order_detail d
JOIN orders o ON o.order_id = d.order_id
WHERE o.status = 'CANCELLED';

-- ============================= 인덱스 ===============================

-- Q17) [CREATE INDEX] orders.customer_id 인덱스
--   이유: "고객별 주문 조회/집계(Q8,Q10)"에서 customer_id 로 자주 조인·필터링하므로,
--         이 컬럼에 인덱스를 두면 풀 스캔 없이 빠르게 해당 고객의 주문을 찾을 수 있다.
CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders(customer_id);
-- 확인: 인덱스가 사용되는지 실행계획 조회
EXPLAIN QUERY PLAN
SELECT * FROM orders WHERE customer_id = 1;
