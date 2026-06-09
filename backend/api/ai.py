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

from config import AI_ENABLED, AI_MODEL
from utils.session import get_session_dir, get_current_uid
from services.data_loader import load_alipay_data
from services import ai as ai_svc
from services import members as member_svc

logger = logging.getLogger(__name__)
ai_bp = Blueprint('ai', __name__)


@ai_bp.route('/api/ai/status')
def ai_status():
    return jsonify({'success': True, 'enabled': AI_ENABLED, 'model': AI_MODEL if AI_ENABLED else None})


def _require_ai():
    if not AI_ENABLED:
        return jsonify({'success': False, 'error': 'AI 未配置(缺少 ANTHROPIC_API_KEY)'}), 503
    return None


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
        result = ai_svc.chat_over_transactions(df, question, data.get('history'))
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
        rows = ai_svc.recognize_bill(text, hint)
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
    uid = get_current_uid() or 'user_local'
    member_id = data.get('member_id') or member_svc.default_member_id(uid)
    name = (data.get('name') or 'AI识别账单').strip()

    session_dir = get_session_dir()
    safe = ''.join(c for c in name if c.isalnum() or c in ('_', '-')) or 'ai_bill'
    filename = f"ai_{safe}_{datetime.now().strftime('%H%M%S')}.csv"
    path = os.path.join(session_dir, filename)
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        f.write("------------------------------------------------------------------------------------\n导出信息：\n姓名：-\n")
        f.write(f"账户：{name}  [AI识别·银行对账单转换样式]\n共{len(rows)}笔记录\n")
        f.write("------------------------银行对账单转换  支付宝样式------------------------\n")
        w = csv.writer(f)
        f.write(_ALIPAY_HDR + "\n")
        for r in rows:
            w.writerow([r.get('交易时间', ''), r.get('交易分类', ''), r.get('交易对方', ''), '',
                        r.get('商品说明', ''), r.get('收/支', '支出'), f"{float(r.get('金额', 0)):.2f}",
                        r.get('收/付款方式', ''), '交易成功', '', '', ''])
    member_svc.set_file_member(uid, filename, member_id)
    logger.info(f"AI 识别导入 {len(rows)} 笔 → {filename} (member={member_id})")
    return jsonify({'success': True, 'filename': filename, 'count': len(rows)})
