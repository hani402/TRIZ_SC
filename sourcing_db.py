"""
소싱 상품 등록 / 공구 제안 계산 기능 전용 DB 모듈.

- 기존 운영 기능(공구현황판, 매출집계 등)과 완전히 분리된 별도 SQLite 파일을 사용합니다.
- 이 파일이 삭제되어도 기존 기능은 전혀 영향받지 않습니다.
- Streamlit Cloud 재시작 시 로컬 파일이 사라지는 문제 때문에, app.py의 GitHub 동기화
  파이프라인(SYNCED_FILES)에 이 DB 파일도 등록되어 자동으로 저장/복원됩니다.
"""
import os
import sqlite3
from contextlib import contextmanager

SOURCING_DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
SOURCING_DB_PATH = os.path.join(SOURCING_DB_DIR, 'sourcing.db')

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor_name TEXT NOT NULL,
    brand_name TEXT NOT NULL,
    product_name TEXT NOT NULL,
    category TEXT,
    sourcing_manager TEXT NOT NULL,
    vendor_contact_name TEXT,
    vendor_contact_phone TEXT,
    vendor_contact_email TEXT,
    product_status TEXT NOT NULL DEFAULT '조건 협의 중',
    vendor_commission_rate REAL,
    vat_included INTEGER DEFAULT 1,
    base_shipping_fee REAL,
    jeju_shipping_fee REAL,
    remote_shipping_fee REAL,
    free_shipping_condition TEXT,
    shipping_lead_time TEXT,
    return_address TEXT,
    settlement_terms TEXT,
    inventory_notes TEXT,
    image_url TEXT,
    product_link TEXT,
    expiry_info TEXT,
    groupbuy_history TEXT,
    appeal_points TEXT,
    sample_policy_notes TEXT,
    notes TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    created_by TEXT,
    updated_by TEXT
);

CREATE TABLE IF NOT EXISTS product_options (
    option_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    option_name TEXT NOT NULL,
    composition TEXT,
    retail_price REAL NOT NULL,
    groupbuy_price REAL NOT NULL,
    supply_price REAL NOT NULL,
    vendor_commission_rate REAL,
    shipping_fee REAL,
    notes TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sales_proposals (
    proposal_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    sales_manager TEXT NOT NULL,
    seller_name TEXT,
    vendor_company_name TEXT,
    transaction_type TEXT,
    seller_commission_rate REAL NOT NULL DEFAULT 0,
    vendor_commission_rate REAL NOT NULL DEFAULT 0,
    pg_fee_rate REAL NOT NULL DEFAULT 0,
    start_date TEXT,
    end_date TEXT,
    event_details TEXT,
    notes TEXT,
    proposal_status TEXT NOT NULL DEFAULT '작성 중',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    created_by TEXT,
    updated_by TEXT
);

CREATE TABLE IF NOT EXISTS sales_proposal_options (
    proposal_option_id INTEGER PRIMARY KEY AUTOINCREMENT,
    proposal_id INTEGER NOT NULL REFERENCES sales_proposals(proposal_id),
    source_option_id INTEGER REFERENCES product_options(option_id),
    option_name_snapshot TEXT NOT NULL,
    composition_snapshot TEXT,
    retail_price_snapshot REAL NOT NULL,
    groupbuy_price_snapshot REAL NOT NULL,
    supply_price_snapshot REAL NOT NULL,
    discount_rate_snapshot REAL,
    seller_payment REAL,
    vendor_payment REAL,
    pg_fee REAL,
    additional_cost REAL DEFAULT 0,
    company_gp REAL,
    company_gp_rate REAL,
    expected_quantity INTEGER DEFAULT 0,
    expected_sales REAL,
    expected_total_gp REAL
);

CREATE INDEX IF NOT EXISTS idx_products_status ON products(product_status);
CREATE INDEX IF NOT EXISTS idx_products_active ON products(is_active);
CREATE INDEX IF NOT EXISTS idx_options_product ON product_options(product_id);
CREATE INDEX IF NOT EXISTS idx_proposals_product ON sales_proposals(product_id);
CREATE INDEX IF NOT EXISTS idx_proposal_options_proposal ON sales_proposal_options(proposal_id);
"""


def ensure_sourcing_db():
    """DB 파일/폴더/스키마가 없으면 생성. 이미 있으면 아무 것도 하지 않음(멱등)."""
    os.makedirs(SOURCING_DB_DIR, exist_ok=True)
    conn = sqlite3.connect(SOURCING_DB_PATH)
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()


@contextmanager
def get_conn():
    """짧게 열고 바로 닫는 커넥션 컨텍스트 매니저. 매 쿼리마다 새로 열어 커넥션 누수를 방지."""
    ensure_sourcing_db()
    conn = sqlite3.connect(SOURCING_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
