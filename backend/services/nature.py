"""
资金性质标注层 —— 三表模型的地基。

「收/支」回答的是"方向"(收入/支出/转入/转出/不计收支),
「资金性质」回答的是"这笔钱的经济本质":
    消费         真实对外消费(收支表的支出口径)
    工资收入     工资/薪酬/奖金/劳务(收支表的收入口径)
    投资收益     利息/分红/结息/收益
    其他收入     经营收款/理赔/赔付等外部流入
    退款         退款/冲正(抵减消费,不是收入)
    报销         报销返还(抵减消费,不是收入)
    信用卡还款   清偿负债,不是新支出
    投资申赎     理财/基金申购赎回(资产形态变化)
    内部流转     自己账户间搬运(银行↔平台/钱包/提现/充值/公积金)
    转账往来     与他人之间的转账/红包/资金周转
    其他         无法判定

规则优先级:用户自定义规则 > 退款标志 > 交易分类精确映射 > 关键词 > 方向兜底。
用户规则存 upload/<uid>/_nature_rules.json,改动会使数据缓存自动失效(纳入文件签名)。
"""
import json
import logging
import os
import re
import threading

from config import UPLOAD_FOLDER

logger = logging.getLogger(__name__)
_rules_lock = threading.Lock()

NATURE_COL = '资金性质'

NATURES = ['消费', '工资收入', '投资收益', '其他收入', '退款', '报销',
           '信用卡还款', '投资申赎', '内部流转', '转账往来', '其他']

# 真实收入 / 真实支出口径(收支表)
INCOME_NATURES = ('工资收入', '投资收益', '其他收入')
EXPENSE_NATURE = '消费'

MAX_RULES = 60
RULE_FIELDS = ('任意', '交易对方', '商品说明', '交易分类', '收/付款方式')


# ============ 用户自定义规则 ============
def _rules_file(uid):
    return os.path.join(UPLOAD_FOLDER, uid, '_nature_rules.json')


def load_rules(uid):
    try:
        p = _rules_file(uid)
        if os.path.exists(p):
            with open(p, encoding='utf-8') as f:
                rules = json.load(f) or []
                return rules if isinstance(rules, list) else []
    except Exception:
        logger.exception("读取口径规则失败")
    return []


def save_rules(uid, rules):
    """整体替换规则列表。规则: {field, contains, nature};按列表顺序首个命中生效。"""
    if not isinstance(rules, list):
        raise ValueError('规则须为数组')
    clean = []
    for r in rules[:MAX_RULES]:
        if not isinstance(r, dict):
            continue
        field = str(r.get('field', '任意')).strip() or '任意'
        contains = str(r.get('contains', '')).strip()[:40]
        nature = str(r.get('nature', '')).strip()
        if field not in RULE_FIELDS or not contains or nature not in NATURES:
            continue
        clean.append({'field': field, 'contains': contains, 'nature': nature})
    with _rules_lock:
        p = _rules_file(uid)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        tmp = p + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(clean, f, ensure_ascii=False, indent=2)
        os.replace(tmp, p)
        try:
            os.chmod(p, 0o600)
        except Exception:
            pass
    return clean


# ============ 内置规则表 ============
# 交易分类 → 性质(精确语义,最可靠:银行转换行的分类即编码了性质)
_CAT_EXACT = {
    '退款': '退款', '退款冲正': '退款', '转账-退款': '退款',
    '信用卡还款': '信用卡还款', '信用还款': '信用卡还款', '信用借还': '信用卡还款',
    '理财投资': '投资申赎', '投资理财': '投资申赎',
    '公积金': '内部流转', '账户存取': '内部流转',
    '零钱提现': '内部流转', '经营账户提现': '内部流转',
    '工资收入': '工资收入',
    '其他收入': '其他收入', '经营收款': '其他收入',
    '转账': '转账往来', '转账红包': '转账往来', '群收款': '转账往来',
    '二维码收款': '转账往来', '红包': '转账往来', '亲友代付': '转账往来',
    '对外转入': '转账往来', '对外转出': '转账往来', '对外转账': '转账往来',
    '资金往来': '转账往来',
    '平台代扣': '内部流转', '资金转移': '内部流转',
}
_CAT_PREFIX = [
    ('自转账', '内部流转'),          # 自转账 / 自转账(账户搬运) / 自转账(银行↔平台)
    ('转入零钱通', '内部流转'),
    ('零钱通转出', '内部流转'),
    ('微信红包', '转账往来'),        # 微信红包（单发/群红包）
]
_CAT_CONTAINS = [
    ('资金周转', '转账往来'),        # 信用卡资金周转/回流(大额周转,绝不能算消费)
    ('资金回流', '转账往来'),
]
_CAT_SUFFIX = [
    ('-退款', '退款'),               # 「美团-退款」等商户后缀型
]

# 关键词规则。两条铁律:
# 1. 刻意不匹配「收/付款方式」——"余额宝"出现在方式里是"用余额宝付款的消费",不是投资!
# 2. 投资类关键词只匹配 交易分类+商品说明(不含交易对方)——商户名是误杀主源
#    ("中华思源工程扶贫基金会"的捐款、"XX理财餐饮公司"的午餐 都不是投资);
#    且「基金」排除「基金会」。字段以 \n 拼接,正则跨度用 [^\n]* 防跨字段误拼。
_KW_REPAY = re.compile(r'信用卡还款|信用卡自动还款|信用卡[^\n]{0,8}还款|还款[^\n]{0,8}信用卡|月付[^\n]{0,4}还款')
_KW_INVEST = re.compile(r'基金(?!会)|理财|申购|赎回|定期存款|结构性存款|国债|证券|黄金积存|定活互转|通知存款|'
                        r'朝朝宝|余利宝|余额宝[^\n]*转入|余额宝[^\n]*转出|转入余额宝|余额宝-')
_KW_WITHDRAW = re.compile(r'零钱提现|余额提现|提现到')
_KW_INCOME = [
    (re.compile(r'工资|薪资|薪酬|代发|奖金|年终奖|劳务费'), '工资收入'),
    (re.compile(r'利息|结息|分红|派息|收益到账'), '投资收益'),
    (re.compile(r'报销'), '报销'),
    (re.compile(r'医保|理赔|保险金|赔付|赔偿'), '其他收入'),
    (re.compile(r'退款|退货|冲正'), '退款'),
]


def _join_cols(df, cols):
    """以 \\n 拼接若干列为单个文本 Series(\\n 防正则跨字段拼接)。"""
    import pandas as pd
    parts = [df[c].astype(str).fillna('') for c in cols if c in df.columns]
    if not parts:
        return pd.Series([''] * len(df), index=df.index)
    s = parts[0]
    for p in parts[1:]:
        s = s + '\n' + p
    return s


def _text_series(df):
    return _join_cols(df, ('交易分类', '交易对方', '商品说明'))


def apply_nature(df, uid=None):
    """为 df 标注「资金性质」列。纯增列,不改任何既有列;幂等。"""
    import pandas as pd
    if df is None or len(df) == 0:
        if df is not None:
            df[NATURE_COL] = pd.Series(dtype=object)
        return df

    n = len(df)
    result = pd.Series([None] * n, index=df.index, dtype=object)
    cat = df['交易分类'].astype(str).fillna('') if '交易分类' in df.columns else pd.Series([''] * n, index=df.index)
    text = _text_series(df)
    zhi = df['收/支'].astype(str) if '收/支' in df.columns else pd.Series([''] * n, index=df.index)

    def assign(mask, nature):
        m = mask & result.isna()
        if m.any():
            result[m] = nature

    # 1. 用户自定义规则(最高优先级,按列表顺序)
    if uid:
        for r in load_rules(uid):
            field, kw, nature = r['field'], r['contains'], r['nature']
            if field == '任意':
                fs = text
                if '收/付款方式' in df.columns:
                    fs = fs + '\n' + df['收/付款方式'].astype(str).fillna('')
            elif field in df.columns:
                fs = df[field].astype(str).fillna('')
            else:
                continue
            assign(fs.str.contains(re.escape(kw), na=False), nature)

    # 2. 退款标志
    if '是否退款' in df.columns:
        assign(df['是否退款'].fillna(False).astype(bool), '退款')

    # 2.5 利息/结息/分红优先于分类映射 —— 银行转换分类会把结息混进「工资收入」,
    #     必须在分类映射之前按关键词纠正,否则投资收益被工资吞掉
    assign((zhi == '收入') & text.str.contains(r'利息|结息|分红|派息|收益到账', na=False), '投资收益')

    # 3. 交易分类映射
    mapped = cat.map(_CAT_EXACT)
    m = mapped.notna() & result.isna()
    result[m] = mapped[m]
    for prefix, nature in _CAT_PREFIX:
        assign(cat.str.startswith(prefix, na=False), nature)
    for sub, nature in _CAT_CONTAINS:
        assign(cat.str.contains(sub, na=False, regex=False), nature)
    for suffix, nature in _CAT_SUFFIX:
        assign(cat.str.endswith(suffix, na=False), nature)

    # 4. 关键词。还款/提现匹配 分类+对方+说明;投资只匹配 分类+说明(防商户名误杀)
    cat_desc = _join_cols(df, ('交易分类', '商品说明'))
    assign(text.str.contains(_KW_REPAY, na=False), '信用卡还款')
    assign(cat_desc.str.contains(_KW_INVEST, na=False), '投资申赎')
    assign(text.str.contains(_KW_WITHDRAW, na=False), '内部流转')
    is_income = zhi == '收入'
    for pat, nature in _KW_INCOME:
        assign(is_income & text.str.contains(pat, na=False), nature)

    # 5. 方向兜底
    assign(zhi == '不计收支', '内部流转')
    assign(zhi == '支出', '消费')
    assign(zhi == '收入', '其他收入')
    assign(zhi.isin(['转入', '转出']), '转账往来')

    # 6. 终极兜底
    result[result.isna()] = '其他'
    df[NATURE_COL] = result
    return df
