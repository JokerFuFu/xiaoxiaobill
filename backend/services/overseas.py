"""
境外消费识别 —— 从真实消费里单独拎出"花在境外/外币"的交易。

为什么单独做:境外消费混在普通消费里看不出规模,但它是旅行/海淘/海外 SaaS 的独立画像。
数据里没有现成"境外"分类,只能从标记反推。真实信号(实测自账单):
- 银行信用卡消费在商品说明里带外币金额,如 `MANUS AISGP(39.00美元)`、`NOTION LABS,INC.USA(205.17美元)`,
  并常把国家代码(USA/SGP/JPN…)拼在商户名后。
- 弱信号:海外京东/免税/Duty Free/跨境 等关键词。

口径:只在"真实消费"(资金性质=消费)里找,绝不把转账/还款/投资算进去。
金额一律用人民币入账额(银行已折算);能解析出外币原值的另存 foreign_amount 供展示。
"""
import logging
import re

import pandas as pd

logger = logging.getLogger(__name__)

# 币种中文名 → 代码
_CUR_NAME = {
    '美元': 'USD', '日元': 'JPY', '欧元': 'EUR', '港币': 'HKD', '港元': 'HKD',
    '英镑': 'GBP', '韩元': 'KRW', '新台币': 'TWD', '泰铢': 'THB', '澳元': 'AUD',
    '加元': 'CAD', '新加坡元': 'SGD', '瑞士法郎': 'CHF', '林吉特': 'MYR',
}
# "39.00美元" / "1,234.5 日元"
_AMT_CUR_RE = re.compile(
    r'([\d,]+\.?\d*)\s*(美元|日元|欧元|港币|港元|英镑|韩元|新台币|泰铢|澳元|加元|新加坡元|瑞士法郎|林吉特)')
# 独立币种代码(词边界)
_CODE_RE = re.compile(r'(?<![A-Za-z])(USD|JPY|EUR|HKD|GBP|KRW|SGD|AUD|CAD|THB|MYR|TWD|CHF)(?![A-Za-z])')
# 国家/地区三位代码(信用卡境外消费把它拼在商户名后,仅银行来源时才信,避免误伤中文商户里的字母)
_COUNTRY = {
    'USA': '美国', 'SGP': '新加坡', 'JPN': '日本', 'HKG': '中国香港', 'GBR': '英国',
    'KOR': '韩国', 'THA': '泰国', 'MYS': '马来西亚', 'TWN': '中国台湾', 'AUS': '澳大利亚',
    'CAN': '加拿大', 'FRA': '法国', 'DEU': '德国', 'ITA': '意大利', 'ESP': '西班牙',
    'CHE': '瑞士', 'NLD': '荷兰', 'MAC': '中国澳门', 'IDN': '印尼', 'VNM': '越南',
}
# 国家代码常紧贴在商户名后(如 ...USA / ...SGP),不要求前置词边界
_COUNTRY_RE = re.compile(r'(' + '|'.join(_COUNTRY) + r')(?![A-Za-z])')
# 仅保留高确定性的"实体免税店",不要 境外/跨境/海外 这些会误伤商品营销词的软关键词
_KW_RE = re.compile(r'免税店|Duty\s*Free', re.I)
# 清洗商户名:去掉尾部 (39.00美元) 外币括注、紧贴的国家代码、电话号
_SUFFIX_AMT_RE = re.compile(r'\s*[（(][^)）]*(?:美元|日元|欧元|港[币元]|英镑|韩元|新台币|泰铢|澳元|加元|新加坡元|法郎|林吉特)[^)）]*[)）]\s*$')
_SUFFIX_COUNTRY_RE = re.compile(r'(?<=[A-Za-z.])(' + '|'.join(_COUNTRY) + r')\s*$')
_PHONE_RE = re.compile(r'\s*\d{3}[-\s]?\d{3,4}[-\s]?\d{3,4}\s*')


def _clean_merchant(name):
    name = (name or '').strip()
    name = _SUFFIX_AMT_RE.sub('', name)
    name = _PHONE_RE.sub(' ', name).strip()
    name = _SUFFIX_COUNTRY_RE.sub('', name).strip(' .')
    return name or '(未知商户)'


def _row_text(r):
    return ' '.join(str(r.get(c, '') or '') for c in ('交易分类', '交易对方', '商品说明'))


def _real_consumption(df):
    from services.nature import NATURE_COL, EXPENSE_NATURE
    if df is None or len(df) == 0:
        return df
    if NATURE_COL in df.columns:
        d = df[df[NATURE_COL] == EXPENSE_NATURE].copy()
    else:
        d = df[df['收/支'] == '支出'].copy()
    if '是否退款' in d.columns:
        d = d[~d['是否退款'].fillna(False)]
    return d


def _detect_one(text, is_bank):
    """返回 (是否境外, 币种代码|None, 外币金额|None, 地区|None)。"""
    m = _AMT_CUR_RE.search(text)
    if m:
        amt = None
        try:
            amt = float(m.group(1).replace(',', ''))
        except ValueError:
            pass
        return True, _CUR_NAME.get(m.group(2)), amt, None
    mc = _CODE_RE.search(text)
    if mc:
        return True, mc.group(1), None, None
    if is_bank:
        mco = _COUNTRY_RE.search(text)
        if mco:
            return True, None, None, _COUNTRY[mco.group(1)]
    if _KW_RE.search(text):
        return True, None, None, None
    return False, None, None, None


def detect(df, year=None):
    """识别境外消费,返回汇总 + 明细。year=None 表示全部年份。"""
    con = _real_consumption(df)
    empty = {'count': 0, 'total_cny': 0.0, 'years': [], 'year': year,
             'by_currency': [], 'by_region': [], 'by_merchant': [], 'monthly': [], 'list': []}
    if con is None or len(con) == 0:
        return empty

    con = con.copy()
    years_all = sorted(con['交易时间'].dt.year.dropna().unique().astype(int).tolist())
    if year:
        con = con[con['交易时间'].dt.year == int(year)]
    if len(con) == 0:
        empty['years'] = years_all
        return empty

    recs = []
    for _, r in con.iterrows():
        is_bank = str(r.get('来源', '')) == '银行'
        hit, cur, famt, region = _detect_one(_row_text(r), is_bank)
        if not hit:
            continue
        raw_mer = str(r.get('交易对方', '') or '') or str(r.get('商品说明', ''))
        recs.append({
            'date': r['交易时间'].strftime('%Y-%m-%d'),
            'month': r['交易时间'].strftime('%Y-%m'),
            'merchant': _clean_merchant(raw_mer)[:40],
            'desc': str(r.get('商品说明', '') or '')[:60],
            'cny': round(float(r['金额']), 2),
            'currency': cur, 'foreign_amount': famt, 'region': region,
            'source': str(r.get('来源', '')),
        })
    if not recs:
        empty['years'] = years_all
        return empty

    rdf = pd.DataFrame(recs)
    total = round(float(rdf['cny'].sum()), 2)

    by_cur = []
    for cur, g in rdf[rdf['currency'].notna()].groupby('currency'):
        fa = g['foreign_amount'].dropna()
        by_cur.append({'currency': cur, 'count': int(len(g)), 'cny': round(float(g['cny'].sum()), 2),
                       'foreign_total': round(float(fa.sum()), 2) if len(fa) else None})
    by_cur.sort(key=lambda x: -x['cny'])

    by_region = [{'region': reg, 'count': int(len(g)), 'cny': round(float(g['cny'].sum()), 2)}
                 for reg, g in rdf[rdf['region'].notna()].groupby('region')]
    by_region.sort(key=lambda x: -x['cny'])

    by_merchant = []
    for mer, g in rdf.groupby('merchant'):
        by_merchant.append({'merchant': mer, 'count': int(len(g)), 'cny': round(float(g['cny'].sum()), 2)})
    by_merchant.sort(key=lambda x: -x['cny'])

    monthly = [{'month': m, 'cny': round(float(g['cny'].sum()), 2), 'count': int(len(g))}
               for m, g in rdf.groupby('month')]
    monthly.sort(key=lambda x: x['month'])

    # 明细直接用干净的 recs(None 保持 None);不走 DataFrame.to_dict 以免 None→NaN 产出非法 JSON
    lst = sorted(recs, key=lambda x: x['date'], reverse=True)[:200]
    return {
        'count': int(len(rdf)), 'total_cny': total, 'years': years_all, 'year': year,
        'by_currency': by_cur, 'by_region': by_region, 'by_merchant': by_merchant[:30],
        'monthly': monthly, 'list': lst,
    }
