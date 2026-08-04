"""
공구 제안 계산 로직 (순수 함수 모음).

DB나 화면(Streamlit)에 전혀 의존하지 않습니다 — 입력값을 받아 계산 결과만 반환합니다.
그래서 화면 코드를 건드리지 않고도 이 파일만 따로 테스트할 수 있습니다.
"""


def calc_discount_rate(retail_price, groupbuy_price):
    """할인율 = (정상가 - 공구가) / 정상가"""
    if not retail_price:
        return 0.0
    return (retail_price - groupbuy_price) / retail_price


def calc_option_result(groupbuy_price, supply_price, seller_commission_rate,
                        vendor_commission_rate, pg_fee_rate, additional_cost=0,
                        expected_quantity=0):
    """옵션 1개에 대한 지급액/GP/예상 매출 등을 전부 계산해서 dict로 반환.

    seller_payment = 공구가 × 셀러 수수료율
    vendor_payment = 공구가 × 벤더 수수료율
    pg_fee         = 공구가 × PG 수수료율
    company_gp     = 공구가 - 공급가 - 셀러지급액 - 벤더지급액 - PG수수료 - 추가비용
    company_gp_rate= company_gp / 공구가
    expected_sales   = 공구가 × 예상판매수량
    expected_total_gp= company_gp × 예상판매수량
    """
    groupbuy_price = groupbuy_price or 0
    supply_price = supply_price or 0
    seller_commission_rate = seller_commission_rate or 0
    vendor_commission_rate = vendor_commission_rate or 0
    pg_fee_rate = pg_fee_rate or 0
    additional_cost = additional_cost or 0
    expected_quantity = expected_quantity or 0

    seller_payment = groupbuy_price * seller_commission_rate
    vendor_payment = groupbuy_price * vendor_commission_rate
    pg_fee = groupbuy_price * pg_fee_rate

    company_gp = groupbuy_price - supply_price - seller_payment - vendor_payment - pg_fee - additional_cost
    company_gp_rate = (company_gp / groupbuy_price) if groupbuy_price else 0.0

    expected_sales = groupbuy_price * expected_quantity
    expected_total_gp = company_gp * expected_quantity

    return {
        'seller_payment': seller_payment,
        'vendor_payment': vendor_payment,
        'pg_fee': pg_fee,
        'company_gp': company_gp,
        'company_gp_rate': company_gp_rate,
        'expected_sales': expected_sales,
        'expected_total_gp': expected_total_gp,
    }


def calc_proposal_summary(option_results):
    """제안에 포함된 여러 옵션의 계산 결과 리스트를 받아 합계를 반환."""
    total_expected_sales = sum(r['expected_sales'] for r in option_results)
    total_expected_gp = sum(r['expected_total_gp'] for r in option_results)
    blended_gp_rate = (total_expected_gp / total_expected_sales) if total_expected_sales else 0.0
    return {
        'total_expected_sales': total_expected_sales,
        'total_expected_gp': total_expected_gp,
        'blended_gp_rate': blended_gp_rate,
    }
