"""detect_file_source 来源探测的表征测试(重点覆盖收窄 except 后的容错回退)。"""
import os

from utils.file_utils import detect_file_source


def _write(tmp_path, name, data, binary=False):
    p = os.path.join(str(tmp_path), name)
    mode = 'wb' if binary else 'w'
    kw = {} if binary else {'encoding': 'utf-8-sig'}
    with open(p, mode, **kw) as f:
        f.write(data)
    return p


def test_detect_wechat_marker(tmp_path):
    p = _write(tmp_path, 'a.csv', '微信支付账单明细\n交易时间,交易类型\n')
    assert detect_file_source(p) == 'wechat'


def test_detect_bank_csv_marker(tmp_path):
    p = _write(tmp_path, 'b.csv', '# 银行对账单转换\n交易时间,金额\n')
    assert detect_file_source(p) == 'bank-csv'


def test_detect_plain_csv_falls_back_to_alipay(tmp_path):
    p = _write(tmp_path, 'c.csv', '交易时间,金额\n2024-01-01,10\n')
    assert detect_file_source(p) == 'alipay'


def test_detect_undecodable_csv_falls_back_without_crash(tmp_path):
    # 非法字节触发 UnicodeDecodeError,应被收窄后的 except 捕获并回退 alipay
    p = _write(tmp_path, 'd.csv', b'\xff\xfe\x00\x01garbage', binary=True)
    assert detect_file_source(p) == 'alipay'
