"""
AI API

- GET  /api/ai/status            AI 是否可用 + 模型名
- POST /api/ai/chat              对话式检索/分析交易 {question, history?}
- POST /api/ai/recognize         智能识别账单(上传 file 或 {text}) → 返回交易预览
- POST /api/ai/recognize/import  把识别结果导入到某成员 {rows, member_id, name}
"""
import csv
import io
import logging
import os
from datetime import datetime

from flask import Blueprint, jsonify, request

from config import AI_ENABLED, AI_MODEL, AI_BASE_URL
from utils.session import get_session_dir, get_current_uid
from services.data_loader import load_alipay_data
from services import ai as ai_svc
from services import members as member_svc

logger = logging.getLogger(__name__)
ai_bp = Blueprint('ai', __name__)


def _uid():
    return get_current_uid() or '__anon__'


def _cfg():
    """当前用户生效的 AI 配置(自定义优先,回落 env 默认)。"""
    return ai_svc.get_ai_config(_uid())


@ai_bp.route('/api/ai/status')
def ai_status():
    cfg = _cfg()
    enabled = bool(cfg.get('api_key'))
    return jsonify({'success': True, 'enabled': enabled,
                    'model': cfg['model'] if enabled else None,
                    'source': cfg['source']})


def _require_ai():
    if not _cfg().get('api_key'):
        return jsonify({'success': False, 'error': 'AI 未配置,请到「设置 → AI 模型配置」填入 API Key'}), 503
    return None


# ============ 每用户模型配置 ============
@ai_bp.route('/api/ai/config', methods=['GET'])
def get_config():
    cfg = ai_svc.get_ai_config(_uid())
    return jsonify({'success': True, 'config': {
        'base_url': cfg['base_url'],
        'model': cfg['model'],
        'api_key_masked': ai_svc.mask_key(cfg['api_key']),
        'has_key': bool(cfg['api_key']),
        'source': cfg['source'],   # custom=用户自定义 / default=系统默认
        'default_base_url': AI_BASE_URL,
        'default_model': AI_MODEL,
        'has_default': AI_ENABLED,
    }})


@ai_bp.route('/api/ai/config', methods=['POST'])
def save_config():
    data = request.get_json(silent=True) or {}
    base_url = (data.get('base_url') or '').strip()
    model = (data.get('model') or '').strip()
    api_key = data.get('api_key')   # None=不改 / ''=清除自定义回落默认 / 其他=新key
    if api_key is not None:
        api_key = api_key.strip()
    if api_key and (base_url and not base_url.startswith(('http://', 'https://'))):
        return jsonify({'success': False, 'error': 'Base URL 需以 http(s):// 开头'}), 400
    cfg = ai_svc.save_ai_config(_uid(), base_url=base_url or None, api_key=api_key, model=model or None)
    return jsonify({'success': True, 'source': cfg['source'],
                    'api_key_masked': ai_svc.mask_key(cfg['api_key'])})


@ai_bp.route('/api/ai/config/test', methods=['POST'])
def test_config():
    """测试连接:body 可带 base_url/api_key/model 直接试,缺省用已保存配置。"""
    data = request.get_json(silent=True) or {}
    cfg = ai_svc.get_ai_config(_uid())
    test = {
        'base_url': (data.get('base_url') or cfg['base_url']).strip().rstrip('/'),
        'api_key': (data.get('api_key') or '').strip() or cfg['api_key'],
        'model': (data.get('model') or cfg['model']).strip(),
    }
    if not test['api_key']:
        return jsonify({'success': False, 'error': '没有可用的 API Key'}), 400
    ok, msg = ai_svc.test_ai_config(test)
    return jsonify({'success': True, 'ok': ok, 'message': msg})


@ai_bp.route('/api/ai/chat', methods=['POST'])
def chat():
    err = _require_ai()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    question = (data.get('question') or '').strip()
    if not question:
        return jsonify({'success': False, 'error': '问题不能为空'}), 400
    try:
        df = load_alipay_data()
    except FileNotFoundError:
        return jsonify({'success': False, 'error': '当前账号还没有账单数据,请先上传'}), 400
    try:
        result = ai_svc.chat_over_transactions(df, question, data.get('history'), cfg=_cfg())
    except Exception as e:
        logger.exception("AI chat 失败")
        return jsonify({'success': False, 'error': f'AI 调用失败: {e}'}), 500
    return jsonify({'success': True, **result})


def _extract_text(file_storage):
    """从上传文件抽取文本(csv/txt/xlsx/pdf)。"""
    name = (file_storage.filename or '').lower()
    raw = file_storage.read()
    if name.endswith(('.txt', '.csv')):
        for enc in ('utf-8-sig', 'gbk', 'utf-8'):
            try:
                return raw.decode(enc)
            except Exception:
                continue
        return raw.decode('utf-8', 'replace')
    if name.endswith('.xlsx'):
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(raw), read_only=True)
        lines = []
        for ws in wb.worksheets:
            for row in ws.iter_rows(values_only=True):
                cells = [str(c) for c in row if c is not None]
                if cells:
                    lines.append('\t'.join(cells))
        return '\n'.join(lines)
    if name.endswith('.pdf'):
        import pdfplumber
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            return '\n'.join((pg.extract_text() or '') for pg in pdf.pages)
    raise ValueError('暂不支持该文件类型的识别(支持 csv/txt/xlsx/pdf 文本)')


@ai_bp.route('/api/ai/recognize', methods=['POST'])
def recognize():
    err = _require_ai()
    if err:
        return err
    hint = request.form.get('hint', '') if request.form else ''
    try:
        if 'file' in request.files and request.files['file'].filename:
            text = _extract_text(request.files['file'])
            hint = hint or request.files['file'].filename
        else:
            data = request.get_json(silent=True) or {}
            text = data.get('text', '')
            hint = hint or data.get('hint', '')
        if not (text or '').strip():
            return jsonify({'success': False, 'error': '没有可识别的内容'}), 400
        rows = ai_svc.recognize_bill(text, hint, cfg=_cfg())
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.exception("AI 识别失败")
        return jsonify({'success': False, 'error': f'识别失败: {e}'}), 500
    return jsonify({'success': True, 'rows': rows, 'count': len(rows)})


_ALIPAY_HDR = "交易时间,交易分类,交易对方,对方账号,商品说明,收/支,金额,收/付款方式,交易状态,交易订单号,商家订单号,备注,"


@ai_bp.route('/api/ai/recognize/import', methods=['POST'])
def recognize_import():
    err = _require_ai()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    rows = data.get('rows') or []
    if not rows:
        return jsonify({'success': False, 'error': '没有要导入的记录'}), 400
    uid = _uid()
    member_id = data.get('member_id') or member_svc.default_member_id(uid)
    name = (data.get('name') or 'AI识别账单').strip()

    def _amt(v):
        try:
            return abs(float(str(v).replace(',', '').replace('¥', '').replace('￥', '').strip() or 0))
        except Exception:
            return None

    VALID = ['收入', '支出', '转入', '转出', '不计收支']
    session_dir = get_session_dir()
    safe = ''.join(c for c in name if c.isalnum() or c in ('_', '-')) or 'ai_bill'
    filename = f"ai_{safe}_{datetime.now().strftime('%H%M%S')}.csv"
    path = os.path.join(session_dir, filename)
    written = 0
    try:
        with open(path, 'w', encoding='utf-8-sig', newline='') as f:
            f.write("------------------------------------------------------------------------------------\n导出信息：\n姓名：-\n")
            f.write(f"账户：{name}  [AI识别·银行对账单转换样式]\n共{len(rows)}笔记录\n")
            f.write("------------------------银行对账单转换  支付宝样式------------------------\n")
            w = csv.writer(f)
            f.write(_ALIPAY_HDR + "\n")
            for r in rows:
                if not isinstance(r, dict):
                    continue
                amt = _amt(r.get('金额', 0))
                t = str(r.get('交易时间', '')).strip()
                if amt is None or amt <= 0 or not t:
                    continue   # 跳过金额非法/为空时间的脏行
                zhi = str(r.get('收/支', '支出')).strip()
                if zhi not in VALID:
                    zhi = '支出'
                w.writerow([t, r.get('交易分类', ''), r.get('交易对方', ''), '',
                            r.get('商品说明', ''), zhi, f"{amt:.2f}",
                            r.get('收/付款方式', ''), '交易成功', '', '', ''])
                written += 1
    except Exception as e:
        if os.path.exists(path):
            os.remove(path)   # 出错删半成品,避免脏文件被加载
        logger.exception("AI 识别导入写文件失败")
        return jsonify({'success': False, 'error': f'导入失败: {e}'}), 400

    if written == 0:
        if os.path.exists(path):
            os.remove(path)
        return jsonify({'success': False, 'error': '没有有效记录可导入(金额或时间不合法)'}), 400

    member_svc.set_file_member(uid, filename, member_id)
    logger.info(f"AI 识别导入 {written} 笔 → {filename} (member={member_id})")
    return jsonify({'success': True, 'filename': filename, 'count': written})
