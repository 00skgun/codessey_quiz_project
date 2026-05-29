-- =====================================================================
--  카페 주문(Cafe Order) 데이터베이스 - 스키마 생성 스크립트
--  DB: SQLite 3.x
--  실행: sqlite3 cafe.db ".read schema.sql"
--
--  [설계 개요]
--   테이블 5개: category, menu, customer, orders, order_detail
--   1:N 관계 4개
--     - category 1 : N menu          (한 카테고리에 여러 메뉴)
--     - customer 1 : N orders         (한 고객이 여러 번 주문)
--     - orders   1 : N order_detail   (한 주문에 여러 품목)
--     - menu     1 : N order_detail   (한 메뉴가 여러 주문에 담김)
--   * orders <-> menu 는 order_detail 을 통한 N:M 을 1:N 두 개로 분해한 구조
-- =====================================================================

-- SQLite 는 기본적으로 FK 제약을 끄고 시작하므로 반드시 켜준다. (SQLite 전용)
PRAGMA foreign_keys = ON;

-- 재실행 가능하도록 자식 -> 부모 순서로 DROP
DROP TABLE IF EXISTS order_detail;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS menu;
DROP TABLE IF EXISTS customer;
DROP TABLE IF EXISTS category;

-- ---------------------------------------------------------------------
-- 1) category : 메뉴 분류 (커피/티/디저트 ...)
-- ---------------------------------------------------------------------
CREATE TABLE category (
    category_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL UNIQUE,          -- NOT NULL + UNIQUE 제약
    description   TEXT
);

-- ---------------------------------------------------------------------
-- 2) menu : 판매 메뉴 (category 에 소속) -> category 1:N menu
-- ---------------------------------------------------------------------
CREATE TABLE menu (
    menu_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id   INTEGER NOT NULL,                 -- FK (부모: category)
    name          TEXT    NOT NULL,
    price         INTEGER NOT NULL CHECK (price >= 0),
    is_available  INTEGER NOT NULL DEFAULT 1 CHECK (is_available IN (0, 1)),
    created_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (category_id) REFERENCES category(category_id)
);

-- ---------------------------------------------------------------------
-- 3) customer : 고객
-- ---------------------------------------------------------------------
CREATE TABLE customer (
    customer_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL,
    phone         TEXT    UNIQUE,                    -- 연락처는 중복 불가
    email         TEXT,
    membership    TEXT    NOT NULL DEFAULT 'BRONZE'  -- 등급
                  CHECK (membership IN ('BRONZE', 'SILVER', 'GOLD')),
    joined_at     TEXT    NOT NULL DEFAULT (date('now', 'localtime'))
);

-- ---------------------------------------------------------------------
-- 4) orders : 주문 (customer 에 소속) -> customer 1:N orders
--    'order' 는 SQL 예약어이므로 테이블명을 orders 로 사용한다.
-- ---------------------------------------------------------------------
CREATE TABLE orders (
    order_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id   INTEGER NOT NULL,                 -- FK (부모: customer)
    ordered_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    status        TEXT    NOT NULL DEFAULT 'PAID'
                  CHECK (status IN ('PENDING', 'PAID', 'COMPLETED', 'CANCELLED')),
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
);

-- ---------------------------------------------------------------------
-- 5) order_detail : 주문 상세 품목
--    -> orders 1:N order_detail , menu 1:N order_detail
--    주문 시점의 가격(unit_price)을 함께 저장해 메뉴 가격이 바뀌어도
--    과거 주문 금액이 보존되도록 한다.
-- ---------------------------------------------------------------------
CREATE TABLE order_detail (
    order_detail_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id        INTEGER NOT NULL,               -- FK (부모: orders)
    menu_id         INTEGER NOT NULL,               -- FK (부모: menu)
    quantity        INTEGER NOT NULL CHECK (quantity > 0),
    unit_price      INTEGER NOT NULL CHECK (unit_price >= 0),
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (menu_id)  REFERENCES menu(menu_id)
);
