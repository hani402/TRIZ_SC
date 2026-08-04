"""
소싱 상품 / 공구 제안 데이터 접근 계층.

- 화면 코드(sourcing_pages.py)는 이 파일의 함수만 호출하고, SQL을 직접 쓰지 않습니다.
- 목록 조회는 전부 페이지네이션 + 필요한 컬럼만 가져오도록 작성했습니다 (전체 로딩 금지 원칙).
- '저장' 시점에만 실제로 DB에 씁니다.
"""
from datetime import datetime
from sourcing_db import get_conn


def _now():
    return datetime.now().isoformat(timespec='seconds')


# ── 상품(products) ──────────────────────────────────────────────────────
def check_duplicate_product(vendor_name, brand_name, product_name, exclude_id=None):
    with get_conn() as conn:
        q = "SELECT product_id FROM products WHERE vendor_name=? AND brand_name=? AND product_name=? AND is_active=1"
        params = [vendor_name, brand_name, product_name]
        if exclude_id:
            q += " AND product_id != ?"
            params.append(exclude_id)
        row = conn.execute(q, params).fetchone()
        return row is not None


def create_product(data, options, user):
    """data: 상품 기본정보 dict. options: 옵션 dict 리스트(최소 1개)."""
    now = _now()
    with get_conn() as conn:
        cur = conn.execute("""
            INSERT INTO products (
                vendor_name, brand_name, product_name, category, sourcing_manager,
                vendor_contact_name, vendor_contact_phone, vendor_contact_email,
                product_status, vendor_commission_rate, vat_included,
                base_shipping_fee, jeju_shipping_fee, remote_shipping_fee, free_shipping_condition,
                shipping_lead_time, return_address, settlement_terms, inventory_notes,
                image_url, product_link, expiry_info, groupbuy_history, appeal_points,
                sample_policy_notes, notes, is_active, created_at, updated_at, created_by, updated_by
            ) VALUES (?,?,?,?,?, ?,?,?, ?,?,?, ?,?,?,?, ?,?,?,?, ?,?,?,?,?, ?,?,1,?,?,?,?)
        """, (
            data['vendor_name'], data['brand_name'], data['product_name'], data.get('category'), data['sourcing_manager'],
            data.get('vendor_contact_name'), data.get('vendor_contact_phone'), data.get('vendor_contact_email'),
            data.get('product_status', '조건 협의 중'), data.get('vendor_commission_rate'), int(data.get('vat_included', True)),
            data.get('base_shipping_fee'), data.get('jeju_shipping_fee'), data.get('remote_shipping_fee'), data.get('free_shipping_condition'),
            data.get('shipping_lead_time'), data.get('return_address'), data.get('settlement_terms'), data.get('inventory_notes'),
            data.get('image_url'), data.get('product_link'), data.get('expiry_info'), data.get('groupbuy_history'), data.get('appeal_points'),
            data.get('sample_policy_notes'), data.get('notes'), now, now, user, user,
        ))
        product_id = cur.lastrowid
        for opt in options:
            _insert_option(conn, product_id, opt, now)
        return product_id


def _insert_option(conn, product_id, opt, now):
    conn.execute("""
        INSERT INTO product_options (
            product_id, option_name, composition, retail_price, groupbuy_price, supply_price,
            vendor_commission_rate, shipping_fee, notes, is_active, created_at, updated_at
        ) VALUES (?,?,?,?,?,?, ?,?,?,1,?,?)
    """, (
        product_id, opt['option_name'], opt.get('composition'), opt['retail_price'], opt['groupbuy_price'], opt['supply_price'],
        opt.get('vendor_commission_rate'), opt.get('shipping_fee'), opt.get('notes'), now, now,
    ))


def update_product(product_id, data, user):
    now = _now()
    with get_conn() as conn:
        conn.execute("""
            UPDATE products SET
                vendor_name=?, brand_name=?, product_name=?, category=?, sourcing_manager=?,
                vendor_contact_name=?, vendor_contact_phone=?, vendor_contact_email=?,
                product_status=?, vendor_commission_rate=?, vat_included=?,
                base_shipping_fee=?, jeju_shipping_fee=?, remote_shipping_fee=?, free_shipping_condition=?,
                shipping_lead_time=?, return_address=?, settlement_terms=?, inventory_notes=?,
                image_url=?, product_link=?, expiry_info=?, groupbuy_history=?, appeal_points=?,
                sample_policy_notes=?, notes=?, updated_at=?, updated_by=?
            WHERE product_id=?
        """, (
            data['vendor_name'], data['brand_name'], data['product_name'], data.get('category'), data['sourcing_manager'],
            data.get('vendor_contact_name'), data.get('vendor_contact_phone'), data.get('vendor_contact_email'),
            data.get('product_status'), data.get('vendor_commission_rate'), int(data.get('vat_included', True)),
            data.get('base_shipping_fee'), data.get('jeju_shipping_fee'), data.get('remote_shipping_fee'), data.get('free_shipping_condition'),
            data.get('shipping_lead_time'), data.get('return_address'), data.get('settlement_terms'), data.get('inventory_notes'),
            data.get('image_url'), data.get('product_link'), data.get('expiry_info'), data.get('groupbuy_history'), data.get('appeal_points'),
            data.get('sample_policy_notes'), data.get('notes'), now, user, product_id,
        ))


def replace_product_options(product_id, options, now=None):
    """옵션 전체를 비활성화(is_active=0) 후 새로 입력된 옵션들을 삽입.
    (물리 삭제 대신 비활성화하여, 이미 제안에서 스냅샷으로 참조된 과거 옵션 데이터는 안전하게 보존됨)"""
    now = now or _now()
    with get_conn() as conn:
        conn.execute("UPDATE product_options SET is_active=0, updated_at=? WHERE product_id=?", (now, product_id))
        for opt in options:
            _insert_option(conn, product_id, opt, now)


def set_product_active(product_id, is_active, user):
    with get_conn() as conn:
        conn.execute("UPDATE products SET is_active=?, updated_at=?, updated_by=? WHERE product_id=?",
                     (int(is_active), _now(), user, product_id))


def duplicate_product(product_id, user):
    with get_conn() as conn:
        p = conn.execute("SELECT * FROM products WHERE product_id=?", (product_id,)).fetchone()
        if not p: return None
        opts = conn.execute("SELECT * FROM product_options WHERE product_id=? AND is_active=1", (product_id,)).fetchall()
    data = dict(p)
    data['product_name'] = data['product_name'] + ' (복제)'
    options = [dict(o) for o in opts]
    return create_product(data, options, user)


def search_products(vendor_name='', brand_name='', product_name='', sourcing_manager='', status='',
                     include_inactive=False, page=1, page_size=20):
    """목록 조회: 필요한 컬럼만, 페이지네이션 적용. 옵션 개수는 서브쿼리로 카운트만."""
    where = []
    params = []
    if not include_inactive:
        where.append("p.is_active=1")
    if vendor_name:
        where.append("p.vendor_name LIKE ?"); params.append(f'%{vendor_name}%')
    if brand_name:
        where.append("p.brand_name LIKE ?"); params.append(f'%{brand_name}%')
    if product_name:
        where.append("p.product_name LIKE ?"); params.append(f'%{product_name}%')
    if sourcing_manager and sourcing_manager != '전체':
        where.append("p.sourcing_manager = ?"); params.append(sourcing_manager)
    if status and status != '전체':
        where.append("p.product_status = ?"); params.append(status)
    where_sql = ('WHERE ' + ' AND '.join(where)) if where else ''

    with get_conn() as conn:
        total = conn.execute(f"SELECT COUNT(*) AS c FROM products p {where_sql}", params).fetchone()['c']
        offset = (page - 1) * page_size
        rows = conn.execute(f"""
            SELECT p.product_id, p.vendor_name, p.brand_name, p.product_name, p.sourcing_manager,
                   p.product_status, p.vendor_commission_rate, p.created_at, p.updated_at,
                   (SELECT COUNT(*) FROM product_options o WHERE o.product_id=p.product_id AND o.is_active=1) AS option_count
            FROM products p {where_sql}
            ORDER BY p.updated_at DESC
            LIMIT ? OFFSET ?
        """, params + [page_size, offset]).fetchall()
        return [dict(r) for r in rows], total


def get_product(product_id):
    with get_conn() as conn:
        p = conn.execute("SELECT * FROM products WHERE product_id=?", (product_id,)).fetchone()
        if not p: return None
        opts = conn.execute("SELECT * FROM product_options WHERE product_id=? AND is_active=1 ORDER BY option_id",
                             (product_id,)).fetchall()
        return {'product': dict(p), 'options': [dict(o) for o in opts]}


def list_distinct_managers():
    with get_conn() as conn:
        rows = conn.execute("SELECT DISTINCT sourcing_manager FROM products WHERE sourcing_manager IS NOT NULL ORDER BY 1").fetchall()
        return [r['sourcing_manager'] for r in rows]


def list_products_for_proposal(brand_name):
    """영업 제안 화면에서 브랜드 선택 시, '제안 가능'/'구성안 확정' 상태의 상품만 가볍게 조회."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT product_id, product_name, vendor_name FROM products
            WHERE brand_name=? AND is_active=1 AND product_status IN ('제안 가능','구성안 확정')
            ORDER BY product_name
        """, (brand_name,)).fetchall()
        return [dict(r) for r in rows]


def list_distinct_brands_for_proposal():
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT DISTINCT brand_name FROM products
            WHERE is_active=1 AND product_status IN ('제안 가능','구성안 확정')
            ORDER BY brand_name
        """).fetchall()
        return [r['brand_name'] for r in rows]


def get_active_options(product_id):
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM product_options WHERE product_id=? AND is_active=1 ORDER BY option_id",
                             (product_id,)).fetchall()
        return [dict(r) for r in rows]


# ── 영업 제안(sales_proposals) ──────────────────────────────────────────
def create_proposal(product_id, header, option_snapshots, user):
    """header: 제안 헤더 정보. option_snapshots: 옵션별 스냅샷+계산결과 dict 리스트."""
    now = _now()
    with get_conn() as conn:
        cur = conn.execute("""
            INSERT INTO sales_proposals (
                product_id, sales_manager, seller_name, vendor_company_name, transaction_type,
                seller_commission_rate, vendor_commission_rate, pg_fee_rate,
                start_date, end_date, event_details, notes, proposal_status,
                created_at, updated_at, created_by, updated_by
            ) VALUES (?,?,?,?,?, ?,?,?, ?,?,?,?,?, ?,?,?,?)
        """, (
            product_id, header['sales_manager'], header.get('seller_name'), header.get('vendor_company_name'), header.get('transaction_type'),
            header.get('seller_commission_rate', 0), header.get('vendor_commission_rate', 0), header.get('pg_fee_rate', 0),
            header.get('start_date'), header.get('end_date'), header.get('event_details'), header.get('notes'),
            header.get('proposal_status', '작성 중'), now, now, user, user,
        ))
        proposal_id = cur.lastrowid
        for snap in option_snapshots:
            conn.execute("""
                INSERT INTO sales_proposal_options (
                    proposal_id, source_option_id, option_name_snapshot, composition_snapshot,
                    retail_price_snapshot, groupbuy_price_snapshot, supply_price_snapshot, discount_rate_snapshot,
                    seller_payment, vendor_payment, pg_fee, additional_cost,
                    company_gp, company_gp_rate, expected_quantity, expected_sales, expected_total_gp
                ) VALUES (?,?,?,?, ?,?,?,?, ?,?,?,?, ?,?,?,?,?)
            """, (
                proposal_id, snap.get('source_option_id'), snap['option_name'], snap.get('composition'),
                snap['retail_price'], snap['groupbuy_price'], snap['supply_price'], snap.get('discount_rate'),
                snap['seller_payment'], snap['vendor_payment'], snap['pg_fee'], snap.get('additional_cost', 0),
                snap['company_gp'], snap['company_gp_rate'], snap.get('expected_quantity', 0),
                snap['expected_sales'], snap['expected_total_gp'],
            ))
        return proposal_id


def update_proposal_status(proposal_id, status, user):
    with get_conn() as conn:
        conn.execute("UPDATE sales_proposals SET proposal_status=?, updated_at=?, updated_by=? WHERE proposal_id=?",
                     (status, _now(), user, proposal_id))


def search_proposals(sales_manager='', status='', product_name='', page=1, page_size=20):
    where = []
    params = []
    if sales_manager and sales_manager != '전체':
        where.append("sp.sales_manager=?"); params.append(sales_manager)
    if status and status != '전체':
        where.append("sp.proposal_status=?"); params.append(status)
    if product_name:
        where.append("p.product_name LIKE ?"); params.append(f'%{product_name}%')
    where_sql = ('WHERE ' + ' AND '.join(where)) if where else ''
    with get_conn() as conn:
        total = conn.execute(f"""
            SELECT COUNT(*) AS c FROM sales_proposals sp JOIN products p ON p.product_id=sp.product_id {where_sql}
        """, params).fetchone()['c']
        offset = (page - 1) * page_size
        rows = conn.execute(f"""
            SELECT sp.proposal_id, sp.sales_manager, sp.seller_name, sp.vendor_company_name,
                   sp.proposal_status, sp.start_date, sp.end_date, sp.updated_at,
                   p.product_name, p.vendor_name
            FROM sales_proposals sp JOIN products p ON p.product_id=sp.product_id
            {where_sql}
            ORDER BY sp.updated_at DESC
            LIMIT ? OFFSET ?
        """, params + [page_size, offset]).fetchall()
        return [dict(r) for r in rows], total


def get_proposal(proposal_id):
    with get_conn() as conn:
        h = conn.execute("""
            SELECT sp.*, p.product_name, p.vendor_name, p.brand_name
            FROM sales_proposals sp JOIN products p ON p.product_id=sp.product_id
            WHERE sp.proposal_id=?
        """, (proposal_id,)).fetchone()
        if not h: return None
        opts = conn.execute("SELECT * FROM sales_proposal_options WHERE proposal_id=?", (proposal_id,)).fetchall()
        return {'header': dict(h), 'options': [dict(o) for o in opts]}
