"""
소싱 상품 등록 / 관리 / 공구 제안 계산 화면.

- 이 파일의 함수들은 app.py에서 호출만 됩니다. app.py 쪽 변경은 최소화되어 있습니다.
- DB 접근은 전부 sourcing_repository를 통해서만 하고, 계산은 sourcing_calc만 사용합니다.
"""
import streamlit as st
import sourcing_repository as repo
from sourcing_calc import calc_discount_rate, calc_option_result, calc_proposal_summary

PRODUCT_STATUSES = ['조건 협의 중', '구성안 작성 중', '구성안 확정', '제안 가능', '일시 중지', '진행 불가']
PROPOSAL_STATUSES = ['작성 중', '제안 전달', '조건 협의', '진행 예정', '진행 확정', '진행 취소']


def _money(v):
    try: return f"₩{float(v):,.0f}"
    except (TypeError, ValueError): return '-'


def _pct(v):
    try: return f"{float(v)*100:.1f}%"
    except (TypeError, ValueError): return '-'


# ── 1. 소싱 상품 등록 ────────────────────────────────────────────────────
def render_product_register_page():
    st.markdown('<div class="section-title">🧪 소싱 상품 등록</div>', unsafe_allow_html=True)
    st.markdown('<div class="help">소싱 담당자가 신규 상품과 옵션 구성안을 등록합니다.</div>', unsafe_allow_html=True)

    st.session_state.setdefault('sourcing_option_rows', [{'option_name': '', 'composition': '', 'retail_price': 0, 'groupbuy_price': 0, 'supply_price': 0, 'vendor_commission_rate': 0.0, 'shipping_fee': 0, 'notes': ''}])

    c1, c2 = st.columns(2)
    with c1:
        vendor_name = st.text_input('업체명 *')
        brand_name = st.text_input('브랜드명 *')
        product_name = st.text_input('상품명 *')
        category = st.text_input('카테고리')
        sourcing_manager = st.text_input('소싱 담당자 *')
        product_status = st.selectbox('상품 상태', PRODUCT_STATUSES)
    with c2:
        vendor_contact_name = st.text_input('업체 담당자명')
        vendor_contact_phone = st.text_input('업체 연락처')
        vendor_contact_email = st.text_input('업체 이메일')
        image_url = st.text_input('이미지 URL')
        product_link = st.text_input('상품 링크')
        expiry_info = st.text_input('제조일 / 소비기한')

    with st.expander('📦 거래 및 배송 조건', expanded=False):
        d1, d2 = st.columns(2)
        with d1:
            vendor_commission_rate = st.number_input('업체 제안 가능 수수료율 (%)', min_value=0.0, max_value=100.0, value=0.0, step=0.5) / 100
            vat_included = st.checkbox('부가세 포함', value=True)
            base_shipping_fee = st.number_input('기본 배송비', min_value=0, value=0, step=500)
            jeju_shipping_fee = st.number_input('제주 배송비(추가)', min_value=0, value=0, step=500)
            remote_shipping_fee = st.number_input('도서산간 배송비(추가)', min_value=0, value=0, step=500)
            free_shipping_condition = st.text_input('무료배송 조건')
        with d2:
            shipping_lead_time = st.text_input('출고 리드타임')
            return_address = st.text_area('반품 및 교환 주소', height=70)
            settlement_terms = st.text_input('정산 조건')
            inventory_notes = st.text_area('재고 관련 특이사항', height=70)
            groupbuy_history = st.selectbox('공동구매 진행이력', ['', 'O', 'X'])

    with st.expander('📝 소구포인트 / 샘플정책 / 기타', expanded=False):
        appeal_points = st.text_area('소구포인트 및 기타 특이사항', height=90)
        sample_policy_notes = st.text_area('샘플 정책 / 셀러 허들 / 이벤트', height=90)
        notes = st.text_area('특이사항', height=70)

    st.markdown('<div class="section-title" style="font-size:1.1rem;">옵션 구성</div>', unsafe_allow_html=True)
    rows = st.session_state['sourcing_option_rows']
    for i, opt in enumerate(rows):
        with st.container():
            st.markdown(f'<div class="card">', unsafe_allow_html=True)
            oc1, oc2, oc3 = st.columns(3)
            with oc1:
                opt['option_name'] = st.text_input('옵션명 *', value=opt['option_name'], key=f'opt_name_{i}')
                opt['composition'] = st.text_input('상세 구성', value=opt['composition'], key=f'opt_comp_{i}')
            with oc2:
                opt['retail_price'] = st.number_input('정상가 *', min_value=0, value=int(opt['retail_price']), step=1000, key=f'opt_retail_{i}')
                opt['groupbuy_price'] = st.number_input('공구가 *', min_value=0, value=int(opt['groupbuy_price']), step=1000, key=f'opt_gb_{i}')
                opt['supply_price'] = st.number_input('공급가 *', min_value=0, value=int(opt['supply_price']), step=1000, key=f'opt_supply_{i}')
            with oc3:
                opt['vendor_commission_rate'] = st.number_input('업체 제공 가능 수수료율 (%)', min_value=0.0, max_value=100.0, value=float(opt['vendor_commission_rate'])*100, step=0.5, key=f'opt_vc_{i}') / 100
                opt['shipping_fee'] = st.number_input('배송비', min_value=0, value=int(opt['shipping_fee']), step=500, key=f'opt_ship_{i}')
                opt['notes'] = st.text_input('비고', value=opt['notes'], key=f'opt_notes_{i}')
            if opt['retail_price']:
                dr = calc_discount_rate(opt['retail_price'], opt['groupbuy_price'])
                st.caption(f'할인율(자동계산): {_pct(dr)}')
                if opt['groupbuy_price'] > opt['retail_price']:
                    st.error('공구가는 정상가보다 클 수 없습니다.')
            if len(rows) > 1:
                if st.button('이 옵션 삭제', key=f'opt_del_{i}'):
                    rows.pop(i)
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    if st.button('➕ 옵션 추가'):
        rows.append({'option_name': '', 'composition': '', 'retail_price': 0, 'groupbuy_price': 0, 'supply_price': 0, 'vendor_commission_rate': 0.0, 'shipping_fee': 0, 'notes': ''})
        st.rerun()

    # 중복 옵션명 경고
    names = [o['option_name'].strip() for o in rows if o['option_name'].strip()]
    if len(names) != len(set(names)):
        st.warning('⚠️ 동일한 옵션명이 여러 개 있습니다. 확인해주세요.')

    st.markdown('---')
    if st.button('💾 상품 등록', type='primary'):
        errors = []
        if not vendor_name: errors.append('업체명을 입력해주세요.')
        if not brand_name: errors.append('브랜드명을 입력해주세요.')
        if not product_name: errors.append('상품명을 입력해주세요.')
        if not sourcing_manager: errors.append('소싱 담당자를 입력해주세요.')
        valid_options = [o for o in rows if o['option_name'].strip()]
        if not valid_options: errors.append('옵션을 최소 1개 이상 입력해주세요.')
        for o in valid_options:
            if not o['retail_price'] or o['retail_price'] <= 0:
                errors.append(f'"{o["option_name"]}" 옵션: 정상가는 0보다 커야 합니다.')
            if o['groupbuy_price'] > o['retail_price']:
                errors.append(f'"{o["option_name"]}" 옵션: 공구가는 정상가보다 클 수 없습니다.')
            if o['supply_price'] < 0:
                errors.append(f'"{o["option_name"]}" 옵션: 공급가는 음수가 될 수 없습니다.')

        if repo.check_duplicate_product(vendor_name, brand_name, product_name):
            st.warning('⚠️ 동일한 업체·브랜드·상품명이 이미 등록되어 있습니다. 그래도 등록하시려면 아래 버튼을 다시 눌러주세요.')
            st.session_state['sourcing_dup_confirmed'] = True

        if errors:
            for e in errors: st.error(e)
        else:
            for o in valid_options:
                o['discount_rate'] = calc_discount_rate(o['retail_price'], o['groupbuy_price'])
            data = dict(
                vendor_name=vendor_name, brand_name=brand_name, product_name=product_name, category=category,
                sourcing_manager=sourcing_manager, vendor_contact_name=vendor_contact_name,
                vendor_contact_phone=vendor_contact_phone, vendor_contact_email=vendor_contact_email,
                product_status=product_status, vendor_commission_rate=vendor_commission_rate, vat_included=vat_included,
                base_shipping_fee=base_shipping_fee, jeju_shipping_fee=jeju_shipping_fee, remote_shipping_fee=remote_shipping_fee,
                free_shipping_condition=free_shipping_condition, shipping_lead_time=shipping_lead_time,
                return_address=return_address, settlement_terms=settlement_terms, inventory_notes=inventory_notes,
                image_url=image_url, product_link=product_link, expiry_info=expiry_info, groupbuy_history=groupbuy_history,
                appeal_points=appeal_points, sample_policy_notes=sample_policy_notes, notes=notes,
            )
            pid = repo.create_product(data, valid_options, user=sourcing_manager)
            st.success(f'상품이 등록되었습니다 (상품 ID: {pid})')
            st.session_state['sourcing_option_rows'] = [{'option_name': '', 'composition': '', 'retail_price': 0, 'groupbuy_price': 0, 'supply_price': 0, 'vendor_commission_rate': 0.0, 'shipping_fee': 0, 'notes': ''}]


# ── 2. 소싱 상품 관리 ────────────────────────────────────────────────────
def render_product_manage_page():
    st.markdown('<div class="section-title">🧪 소싱 상품 관리</div>', unsafe_allow_html=True)

    f1, f2, f3 = st.columns(3)
    with f1: vendor_q = st.text_input('업체명 검색', key='pm_vendor')
    with f2: brand_q = st.text_input('브랜드명 검색', key='pm_brand')
    with f3: product_q = st.text_input('상품명 검색', key='pm_product')
    f4, f5, f6 = st.columns(3)
    with f4: managers = ['전체'] + repo.list_distinct_managers(); manager_sel = st.selectbox('소싱 담당자', managers, key='pm_manager')
    with f5: status_sel = st.selectbox('상품 상태', ['전체'] + PRODUCT_STATUSES, key='pm_status')
    with f6: include_inactive = st.checkbox('사용 중지 상품도 표시', value=False, key='pm_inactive')

    st.session_state.setdefault('pm_page', 1)
    rows, total = repo.search_products(vendor_q, brand_q, product_q, manager_sel, status_sel,
                                        include_inactive, st.session_state['pm_page'], 20)

    st.markdown(f'<div class="help">총 {total}건</div>', unsafe_allow_html=True)
    if not rows:
        st.info('조건에 맞는 상품이 없습니다.')
    else:
        for r in rows:
            with st.container():
                st.markdown('<div class="card">', unsafe_allow_html=True)
                cA, cB, cC = st.columns([3, 2, 2])
                with cA:
                    st.markdown(f'**{r["vendor_name"]} · {r["brand_name"]} · {r["product_name"]}**')
                    st.caption(f'소싱담당: {r["sourcing_manager"]} · 옵션 {r["option_count"]}개 · 상태: {r["product_status"]}')
                with cB:
                    st.caption(f'수수료율: {_pct(r["vendor_commission_rate"])}')
                    st.caption(f'수정일: {r["updated_at"][:10]}')
                with cC:
                    bcol1, bcol2, bcol3, bcol4 = st.columns(4)
                    with bcol1:
                        if st.button('상세', key=f'view_{r["product_id"]}'):
                            st.session_state['pm_detail_id'] = r['product_id']
                            st.session_state.pop('pm_edit_id', None)
                            st.rerun()
                    with bcol2:
                        if st.button('수정', key=f'edit_{r["product_id"]}'):
                            st.session_state['pm_edit_id'] = r['product_id']
                            st.session_state.pop('pm_detail_id', None)
                            st.rerun()
                    with bcol3:
                        if st.button('복제', key=f'dup_{r["product_id"]}'):
                            new_id = repo.duplicate_product(r['product_id'], user=r['sourcing_manager'])
                            st.success(f'복제 완료 (신규 ID: {new_id})')
                            st.rerun()
                    with bcol4:
                        if st.button('사용중지', key=f'deact_{r["product_id"]}'):
                            repo.set_product_active(r['product_id'], False, user=r['sourcing_manager'])
                            st.success('사용 중지로 변경되었습니다.')
                            st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    pcol1, pcol2, pcol3 = st.columns([1, 2, 1])
    with pcol1:
        if st.button('◀ 이전', disabled=st.session_state['pm_page'] <= 1):
            st.session_state['pm_page'] -= 1; st.rerun()
    with pcol2:
        st.markdown(f'<div style="text-align:center;">{st.session_state["pm_page"]} 페이지 (페이지당 20건)</div>', unsafe_allow_html=True)
    with pcol3:
        if st.button('다음 ▶', disabled=st.session_state['pm_page'] * 20 >= total):
            st.session_state['pm_page'] += 1; st.rerun()

    if st.session_state.get('pm_detail_id'):
        detail = repo.get_product(st.session_state['pm_detail_id'])
        if detail:
            p = detail['product']
            st.markdown('---')
            st.markdown(f'<div class="section-title" style="font-size:1.1rem;">상세: {p["product_name"]}</div>', unsafe_allow_html=True)

            def _field(label, value):
                v = value if (value not in (None, '', 0) or value == 0) else '-'
                if label.endswith('여부'):
                    v = '포함' if value else '미포함'
                return f'<div class="field-item"><b>{label}</b><span>{v}</span></div>'

            basic_fields = [
                ('업체명', p['vendor_name']), ('브랜드명', p['brand_name']), ('카테고리', p['category']),
                ('소싱 담당자', p['sourcing_manager']), ('상품 상태', p['product_status']),
                ('업체 담당자명', p['vendor_contact_name']), ('업체 연락처', p['vendor_contact_phone']), ('업체 이메일', p['vendor_contact_email']),
                ('이미지 URL', p['image_url']), ('상품 링크', p['product_link']),
                ('제조일/소비기한', p['expiry_info']), ('공동구매 진행이력', p['groupbuy_history']),
            ]
            st.markdown(f'<div class="field-grid">{"".join(_field(l,v) for l,v in basic_fields)}</div>', unsafe_allow_html=True)

            with st.expander('📦 거래 및 배송 조건'):
                trade_fields = [
                    ('업체 제안 가능 수수료율', _pct(p['vendor_commission_rate'])), ('부가세 포함 여부', p['vat_included']),
                    ('기본 배송비', _money(p['base_shipping_fee'])), ('제주 배송비', _money(p['jeju_shipping_fee'])),
                    ('도서산간 배송비', _money(p['remote_shipping_fee'])), ('무료배송 조건', p['free_shipping_condition']),
                    ('출고 리드타임', p['shipping_lead_time']), ('정산 조건', p['settlement_terms']),
                    ('반품/교환 주소', p['return_address']), ('재고 특이사항', p['inventory_notes']),
                ]
                st.markdown(f'<div class="field-grid">{"".join(_field(l,v) for l,v in trade_fields)}</div>', unsafe_allow_html=True)

            with st.expander('📝 소구포인트 / 샘플정책 / 특이사항'):
                note_fields = [
                    ('소구포인트 및 기타 특이사항', p['appeal_points']),
                    ('샘플 정책 / 셀러 허들 / 이벤트', p['sample_policy_notes']),
                    ('특이사항', p['notes']),
                ]
                st.markdown(f'<div class="field-grid">{"".join(f"<div class=\'field-item full\'><b>{l}</b><span>{v or chr(45)}</span></div>" for l,v in note_fields)}</div>', unsafe_allow_html=True)

            st.caption(f'등록일 {p["created_at"][:16].replace("T"," ")} · 수정일 {p["updated_at"][:16].replace("T"," ")}')

            st.markdown('<div class="section-title" style="font-size:1rem;">옵션 목록</div>', unsafe_allow_html=True)
            if detail['options']:
                opt_rows = ''.join(
                    f'<tr><td>{o["option_name"]}</td><td>{o.get("composition") or "-"}</td>'
                    f'<td class="center">{_money(o["retail_price"])}</td><td class="center">{_money(o["groupbuy_price"])}</td>'
                    f'<td class="center">{_money(o["supply_price"])}</td>'
                    f'<td class="center">{_pct(calc_discount_rate(o["retail_price"], o["groupbuy_price"]))}</td></tr>'
                    for o in detail['options']
                )
                st.markdown(
                    '<div class="card" style="padding:0;overflow-x:auto;"><table class="deal-table">'
                    '<thead><tr><th>옵션명</th><th>구성</th><th>정상가</th><th>공구가</th><th>공급가</th><th>할인율</th></tr></thead>'
                    f'<tbody>{opt_rows}</tbody></table></div>', unsafe_allow_html=True)
            else:
                st.info('등록된 옵션이 없습니다.')

            if st.button('상세 닫기'):
                del st.session_state['pm_detail_id']
                st.rerun()

    if st.session_state.get('pm_edit_id'):
        _render_product_edit_form(st.session_state['pm_edit_id'])


def _render_product_edit_form(product_id):
    detail = repo.get_product(product_id)
    if not detail:
        st.warning('상품을 찾을 수 없습니다.')
        return
    p = detail['product']
    st.markdown('---')
    st.markdown(f'<div class="section-title" style="font-size:1.1rem;">✏️ 수정: {p["product_name"]}</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        vendor_name = st.text_input('업체명 *', value=p['vendor_name'], key='ed_vendor')
        brand_name = st.text_input('브랜드명 *', value=p['brand_name'], key='ed_brand')
        product_name = st.text_input('상품명 *', value=p['product_name'], key='ed_pname')
        category = st.text_input('카테고리', value=p['category'] or '', key='ed_cat')
        sourcing_manager = st.text_input('소싱 담당자 *', value=p['sourcing_manager'], key='ed_mgr')
        product_status = st.selectbox('상품 상태', PRODUCT_STATUSES, index=PRODUCT_STATUSES.index(p['product_status']) if p['product_status'] in PRODUCT_STATUSES else 0, key='ed_status')
    with c2:
        vendor_contact_name = st.text_input('업체 담당자명', value=p['vendor_contact_name'] or '', key='ed_cname')
        vendor_contact_phone = st.text_input('업체 연락처', value=p['vendor_contact_phone'] or '', key='ed_cphone')
        vendor_contact_email = st.text_input('업체 이메일', value=p['vendor_contact_email'] or '', key='ed_cemail')
        image_url = st.text_input('이미지 URL', value=p['image_url'] or '', key='ed_img')
        product_link = st.text_input('상품 링크', value=p['product_link'] or '', key='ed_link')
        expiry_info = st.text_input('제조일 / 소비기한', value=p['expiry_info'] or '', key='ed_expiry')

    with st.expander('📦 거래 및 배송 조건', expanded=False):
        d1, d2 = st.columns(2)
        with d1:
            vendor_commission_rate = st.number_input('업체 제안 가능 수수료율 (%)', min_value=0.0, max_value=100.0, value=float(p['vendor_commission_rate'] or 0)*100, step=0.5, key='ed_vc') / 100
            vat_included = st.checkbox('부가세 포함', value=bool(p['vat_included']), key='ed_vat')
            base_shipping_fee = st.number_input('기본 배송비', min_value=0, value=int(p['base_shipping_fee'] or 0), step=500, key='ed_base_ship')
            jeju_shipping_fee = st.number_input('제주 배송비(추가)', min_value=0, value=int(p['jeju_shipping_fee'] or 0), step=500, key='ed_jeju')
            remote_shipping_fee = st.number_input('도서산간 배송비(추가)', min_value=0, value=int(p['remote_shipping_fee'] or 0), step=500, key='ed_remote')
            free_shipping_condition = st.text_input('무료배송 조건', value=p['free_shipping_condition'] or '', key='ed_freeship')
        with d2:
            shipping_lead_time = st.text_input('출고 리드타임', value=p['shipping_lead_time'] or '', key='ed_lead')
            return_address = st.text_area('반품 및 교환 주소', value=p['return_address'] or '', height=70, key='ed_return')
            settlement_terms = st.text_input('정산 조건', value=p['settlement_terms'] or '', key='ed_settle')
            inventory_notes = st.text_area('재고 관련 특이사항', value=p['inventory_notes'] or '', height=70, key='ed_inv')
            gh_options = ['', 'O', 'X']
            groupbuy_history = st.selectbox('공동구매 진행이력', gh_options, index=gh_options.index(p['groupbuy_history']) if p['groupbuy_history'] in gh_options else 0, key='ed_gh')

    with st.expander('📝 소구포인트 / 샘플정책 / 기타', expanded=False):
        appeal_points = st.text_area('소구포인트 및 기타 특이사항', value=p['appeal_points'] or '', height=90, key='ed_appeal')
        sample_policy_notes = st.text_area('샘플 정책 / 셀러 허들 / 이벤트', value=p['sample_policy_notes'] or '', height=90, key='ed_sample')
        notes = st.text_area('특이사항', value=p['notes'] or '', height=70, key='ed_notes')

    st.markdown('<div class="section-title" style="font-size:1.1rem;">옵션 구성</div>', unsafe_allow_html=True)
    edit_key = f'sourcing_edit_options_{product_id}'
    if edit_key not in st.session_state:
        st.session_state[edit_key] = [
            {'option_name': o['option_name'], 'composition': o['composition'] or '', 'retail_price': o['retail_price'],
             'groupbuy_price': o['groupbuy_price'], 'supply_price': o['supply_price'],
             'vendor_commission_rate': o['vendor_commission_rate'] or 0.0, 'shipping_fee': o['shipping_fee'] or 0, 'notes': o['notes'] or ''}
            for o in detail['options']
        ] or [{'option_name': '', 'composition': '', 'retail_price': 0, 'groupbuy_price': 0, 'supply_price': 0, 'vendor_commission_rate': 0.0, 'shipping_fee': 0, 'notes': ''}]
    rows = st.session_state[edit_key]

    for i, opt in enumerate(rows):
        st.markdown('<div class="card">', unsafe_allow_html=True)
        oc1, oc2, oc3 = st.columns(3)
        with oc1:
            opt['option_name'] = st.text_input('옵션명 *', value=opt['option_name'], key=f'ed_opt_name_{product_id}_{i}')
            opt['composition'] = st.text_input('상세 구성', value=opt['composition'], key=f'ed_opt_comp_{product_id}_{i}')
        with oc2:
            opt['retail_price'] = st.number_input('정상가 *', min_value=0, value=int(opt['retail_price']), step=1000, key=f'ed_opt_retail_{product_id}_{i}')
            opt['groupbuy_price'] = st.number_input('공구가 *', min_value=0, value=int(opt['groupbuy_price']), step=1000, key=f'ed_opt_gb_{product_id}_{i}')
            opt['supply_price'] = st.number_input('공급가 *', min_value=0, value=int(opt['supply_price']), step=1000, key=f'ed_opt_supply_{product_id}_{i}')
        with oc3:
            opt['vendor_commission_rate'] = st.number_input('업체 제공 가능 수수료율 (%)', min_value=0.0, max_value=100.0, value=float(opt['vendor_commission_rate'])*100, step=0.5, key=f'ed_opt_vc_{product_id}_{i}') / 100
            opt['shipping_fee'] = st.number_input('배송비', min_value=0, value=int(opt['shipping_fee']), step=500, key=f'ed_opt_ship_{product_id}_{i}')
            opt['notes'] = st.text_input('비고', value=opt['notes'], key=f'ed_opt_notes_{product_id}_{i}')
        if opt['retail_price']:
            dr = calc_discount_rate(opt['retail_price'], opt['groupbuy_price'])
            st.caption(f'할인율(자동계산): {_pct(dr)}')
            if opt['groupbuy_price'] > opt['retail_price']:
                st.error('공구가는 정상가보다 클 수 없습니다.')
        if len(rows) > 1:
            if st.button('이 옵션 삭제', key=f'ed_opt_del_{product_id}_{i}'):
                rows.pop(i)
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    if st.button('➕ 옵션 추가', key=f'ed_opt_add_{product_id}'):
        rows.append({'option_name': '', 'composition': '', 'retail_price': 0, 'groupbuy_price': 0, 'supply_price': 0, 'vendor_commission_rate': 0.0, 'shipping_fee': 0, 'notes': ''})
        st.rerun()

    st.markdown('---')
    ec1, ec2 = st.columns(2)
    with ec1:
        if st.button('💾 수정 저장', type='primary', key=f'ed_save_{product_id}'):
            errors = []
            if not vendor_name: errors.append('업체명을 입력해주세요.')
            if not brand_name: errors.append('브랜드명을 입력해주세요.')
            if not product_name: errors.append('상품명을 입력해주세요.')
            if not sourcing_manager: errors.append('소싱 담당자를 입력해주세요.')
            valid_options = [o for o in rows if o['option_name'].strip()]
            if not valid_options: errors.append('옵션을 최소 1개 이상 입력해주세요.')
            for o in valid_options:
                if not o['retail_price'] or o['retail_price'] <= 0:
                    errors.append(f'"{o["option_name"]}" 옵션: 정상가는 0보다 커야 합니다.')
                if o['groupbuy_price'] > o['retail_price']:
                    errors.append(f'"{o["option_name"]}" 옵션: 공구가는 정상가보다 클 수 없습니다.')
                if o['supply_price'] < 0:
                    errors.append(f'"{o["option_name"]}" 옵션: 공급가는 음수가 될 수 없습니다.')
            dup = repo.check_duplicate_product(vendor_name, brand_name, product_name, exclude_id=product_id)
            if dup:
                st.warning('⚠️ 동일한 업체·브랜드·상품명을 가진 다른 상품이 이미 있습니다.')

            if errors:
                for e in errors: st.error(e)
            else:
                data = dict(
                    vendor_name=vendor_name, brand_name=brand_name, product_name=product_name, category=category,
                    sourcing_manager=sourcing_manager, vendor_contact_name=vendor_contact_name,
                    vendor_contact_phone=vendor_contact_phone, vendor_contact_email=vendor_contact_email,
                    product_status=product_status, vendor_commission_rate=vendor_commission_rate, vat_included=vat_included,
                    base_shipping_fee=base_shipping_fee, jeju_shipping_fee=jeju_shipping_fee, remote_shipping_fee=remote_shipping_fee,
                    free_shipping_condition=free_shipping_condition, shipping_lead_time=shipping_lead_time,
                    return_address=return_address, settlement_terms=settlement_terms, inventory_notes=inventory_notes,
                    image_url=image_url, product_link=product_link, expiry_info=expiry_info, groupbuy_history=groupbuy_history,
                    appeal_points=appeal_points, sample_policy_notes=sample_policy_notes, notes=notes,
                )
                repo.update_product(product_id, data, user=sourcing_manager)
                repo.replace_product_options(product_id, valid_options)
                st.success('수정되었습니다.')
                del st.session_state[edit_key]
                del st.session_state['pm_edit_id']
                st.rerun()
    with ec2:
        if st.button('취소', key=f'ed_cancel_{product_id}'):
            del st.session_state[edit_key]
            del st.session_state['pm_edit_id']
            st.rerun()


# ── 3. 공구 제안 계산 ────────────────────────────────────────────────────
def render_proposal_calc_page():
    st.markdown('<div class="section-title">🧪 공구 제안 계산</div>', unsafe_allow_html=True)
    st.markdown('<div class="help">브랜드→상품 선택 후, 셀러/벤더 수수료만 입력하면 지급액과 GP가 자동 계산됩니다.</div>', unsafe_allow_html=True)

    brands = repo.list_distinct_brands_for_proposal()
    if not brands:
        any_rows, any_total = repo.search_products(page=1, page_size=5)
        if any_total == 0:
            st.info('아직 등록된 상품이 없습니다. "소싱 상품 등록"에서 먼저 상품을 등록해주세요.')
        else:
            st.warning('제안 가능한 상품이 없습니다. 아래 상품들이 등록되어 있지만, 상태가 "제안 가능" 또는 "구성안 확정"이 아니에요.')
            for r in any_rows:
                st.markdown(f'- **{r["product_name"]}** ({r["vendor_name"]}) — 현재 상태: `{r["product_status"]}`')
            st.caption('"소싱 상품 관리"에서 해당 상품의 "수정" 버튼을 눌러 상태를 바꿔주세요.')
        return

    c1, c2 = st.columns(2)
    with c1: brand_sel = st.selectbox('브랜드', brands)
    products = repo.list_products_for_proposal(brand_sel)
    with c2:
        product_sel = st.selectbox('상품', products, format_func=lambda p: f'{p["product_name"]} ({p["vendor_name"]})') if products else None

    if not product_sel:
        st.info('이 브랜드에 제안 가능한 상품이 없습니다.')
        return

    options = repo.get_active_options(product_sel['product_id'])
    if not options:
        st.warning('이 상품에 등록된 옵션이 없습니다.')
        return

    product_full = repo.get_product(product_sel['product_id'])['product']
    st.markdown('<div class="section-title" style="font-size:1.05rem;">📌 업체 제공 가능 수수료율 (참고)</div>', unsafe_allow_html=True)
    ref_html = f'<div class="field-grid"><div class="field-item"><b>상품 전체 기준</b><span>{_pct(product_full["vendor_commission_rate"])}</span></div>'
    for o in options:
        ref_rate = o['vendor_commission_rate'] if o['vendor_commission_rate'] is not None else product_full['vendor_commission_rate']
        ref_html += f'<div class="field-item"><b>{o["option_name"]}</b><span>{_pct(ref_rate)}</span></div>'
    ref_html += '</div>'
    st.markdown(ref_html, unsafe_allow_html=True)
    st.caption('※ 소싱 등록 시 업체가 제공 가능하다고 밝힌 수수료율입니다. 아래 "벤더 수수료율"을 입력할 때 참고하세요 (이 값을 넘으면 업체와 재협의가 필요할 수 있어요).')

    h1, h2, h3 = st.columns(3)
    with h1:
        sales_manager = st.text_input('영업 담당자 *')
        seller_name = st.text_input('셀러명')
        vendor_company_name = st.text_input('벤더사명')
    with h2:
        transaction_type = st.selectbox('거래 유형', ['셀러 판매', '벤더 직접', '기타'])
        seller_commission_rate = st.number_input('셀러 수수료율 (%)', min_value=0.0, max_value=100.0, value=0.0, step=0.5) / 100
        vendor_commission_rate = st.number_input('벤더 수수료율 (%)', min_value=0.0, max_value=100.0, value=0.0, step=0.5) / 100
    with h3:
        pg_fee_rate = st.number_input('PG 수수료율 (%)', min_value=0.0, max_value=100.0, value=0.0, step=0.1) / 100
        start_date = st.date_input('공구 시작일')
        end_date = st.date_input('공구 종료일')

    event_details = st.text_area('이벤트 내용', height=70)
    notes = st.text_area('특이사항', height=70)

    if product_full['vendor_commission_rate'] and vendor_commission_rate > product_full['vendor_commission_rate']:
        st.warning(f'⚠️ 입력하신 벤더 수수료율({_pct(vendor_commission_rate)})이 업체가 제공 가능하다고 밝힌 수수료율({_pct(product_full["vendor_commission_rate"])})보다 높습니다. 업체와 재협의가 필요할 수 있어요.')

    st.markdown('<div class="section-title" style="font-size:1.1rem;">옵션별 계산 결과</div>', unsafe_allow_html=True)
    option_inputs = {}
    calc_results = []
    for o in options:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f'**{o["option_name"]}** ({o.get("composition") or "-"})')
        oc1, oc2, oc3 = st.columns(3)
        with oc1:
            st.caption(f'정상가 {_money(o["retail_price"])} · 공구가 {_money(o["groupbuy_price"])}')
            dr = calc_discount_rate(o['retail_price'], o['groupbuy_price'])
            st.caption(f'할인율 {_pct(dr)} · 공급가 {_money(o["supply_price"])}')
        with oc2:
            qty = st.number_input('예상 판매 수량', min_value=0, value=0, step=10, key=f'qty_{o["option_id"]}')
        with oc3:
            add_cost = st.number_input('추가 비용', min_value=0, value=0, step=1000, key=f'cost_{o["option_id"]}')

        result = calc_option_result(o['groupbuy_price'], o['supply_price'], seller_commission_rate,
                                     vendor_commission_rate, pg_fee_rate, add_cost, qty)
        rc1, rc2, rc3, rc4 = st.columns(4)
        rc1.metric('셀러 지급액', _money(result['seller_payment']))
        rc2.metric('벤더 지급액', _money(result['vendor_payment']))
        rc3.metric('회사 GP', _money(result['company_gp']))
        rc4.metric('GP율', _pct(result['company_gp_rate']))
        st.markdown('</div>', unsafe_allow_html=True)

        option_inputs[o['option_id']] = {'qty': qty, 'add_cost': add_cost}
        calc_results.append({**result, 'option': o, 'expected_quantity': qty, 'discount_rate': dr})

    summary = calc_proposal_summary(calc_results)
    st.markdown('<div class="dark-card"><div style="display:flex;gap:30px;">'
                f'<div><span>예상 총 매출</span><br><b style="font-size:20px;">{_money(summary["total_expected_sales"])}</b></div>'
                f'<div><span>예상 총 GP</span><br><b style="font-size:20px;">{_money(summary["total_expected_gp"])}</b></div>'
                f'<div><span>평균 GP율</span><br><b style="font-size:20px;">{_pct(summary["blended_gp_rate"])}</b></div>'
                '</div></div>', unsafe_allow_html=True)

    if st.button('💾 제안 임시 저장', type='primary'):
        if not sales_manager:
            st.error('영업 담당자를 입력해주세요.')
        else:
            header = dict(sales_manager=sales_manager, seller_name=seller_name, vendor_company_name=vendor_company_name,
                          transaction_type=transaction_type, seller_commission_rate=seller_commission_rate,
                          vendor_commission_rate=vendor_commission_rate, pg_fee_rate=pg_fee_rate,
                          start_date=str(start_date), end_date=str(end_date), event_details=event_details, notes=notes)
            snapshots = []
            for r in calc_results:
                o = r['option']
                snapshots.append({
                    'source_option_id': o['option_id'], 'option_name': o['option_name'], 'composition': o.get('composition'),
                    'retail_price': o['retail_price'], 'groupbuy_price': o['groupbuy_price'], 'supply_price': o['supply_price'],
                    'discount_rate': r['discount_rate'], 'seller_payment': r['seller_payment'], 'vendor_payment': r['vendor_payment'],
                    'pg_fee': r['pg_fee'], 'additional_cost': option_inputs[o['option_id']]['add_cost'],
                    'company_gp': r['company_gp'], 'company_gp_rate': r['company_gp_rate'],
                    'expected_quantity': r['expected_quantity'], 'expected_sales': r['expected_sales'], 'expected_total_gp': r['expected_total_gp'],
                })
            pid = repo.create_proposal(product_sel['product_id'], header, snapshots, user=sales_manager)
            st.success(f'제안이 저장되었습니다 (제안 ID: {pid})')


# ── 4. 저장된 제안 ───────────────────────────────────────────────────────
def render_saved_proposals_page():
    st.markdown('<div class="section-title">🧪 저장된 제안</div>', unsafe_allow_html=True)

    f1, f2, f3 = st.columns(3)
    with f1: manager_q = st.text_input('영업 담당자', key='sp_manager')
    with f2: status_q = st.selectbox('제안 상태', ['전체'] + PROPOSAL_STATUSES, key='sp_status')
    with f3: product_q = st.text_input('상품명 검색', key='sp_product')

    st.session_state.setdefault('sp_page', 1)
    rows, total = repo.search_proposals(manager_q, status_q, product_q, st.session_state['sp_page'], 20)
    st.markdown(f'<div class="help">총 {total}건</div>', unsafe_allow_html=True)

    for r in rows:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        cA, cB = st.columns([3, 1])
        with cA:
            st.markdown(f'**{r["product_name"]}** ({r["vendor_name"]}) · 담당: {r["sales_manager"]}')
            st.caption(f'셀러: {r["seller_name"] or "-"} · 일정: {r["start_date"] or "-"} ~ {r["end_date"] or "-"}')
        with cB:
            st.markdown(f'<span class="chip active">{r["proposal_status"]}</span>', unsafe_allow_html=True)
            if st.button('열기', key=f'open_{r["proposal_id"]}'):
                st.session_state['sp_detail_id'] = r['proposal_id']
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    pcol1, pcol2, pcol3 = st.columns([1, 2, 1])
    with pcol1:
        if st.button('◀ 이전 ', disabled=st.session_state['sp_page'] <= 1):
            st.session_state['sp_page'] -= 1; st.rerun()
    with pcol3:
        if st.button('다음 ▶ ', disabled=st.session_state['sp_page'] * 20 >= total):
            st.session_state['sp_page'] += 1; st.rerun()

    if st.session_state.get('sp_detail_id'):
        detail = repo.get_proposal(st.session_state['sp_detail_id'])
        if detail:
            st.markdown('---')
            h = detail['header']
            st.markdown(f'<div class="section-title" style="font-size:1.1rem;">{h["product_name"]} 제안 상세</div>', unsafe_allow_html=True)
            new_status = st.selectbox('상태 변경', PROPOSAL_STATUSES, index=PROPOSAL_STATUSES.index(h['proposal_status']))
            if st.button('상태 저장'):
                repo.update_proposal_status(h['proposal_id'], new_status, user=h['sales_manager'])
                st.success('상태가 변경되었습니다.')
                st.rerun()
            for o in detail['options']:
                st.markdown(f'- **{o["option_name_snapshot"]}**: 공구가 {_money(o["groupbuy_price_snapshot"])} / GP {_money(o["company_gp"])} ({_pct(o["company_gp_rate"])}) / 예상수량 {o["expected_quantity"]}건')
            if st.button('상세 닫기 '):
                del st.session_state['sp_detail_id']
                st.rerun()
