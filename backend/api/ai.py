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
from services import ai_analyze as analyze_svc
from services import ai_chats as chat_svc
from services import members as member_svc

logger = logging.getLogger(__name__)
ai_bp = Blueprint('ai', __name__)


def _uid():
    return get_current_uid() or '__anon__'


def _cfg(purpose='chat'):
    """当前用户某功能生效的 AI 配置(功能分配优先 → 默认档案 → env 默认)。"""
    return ai_svc.get_ai_config(_uid(), purpose)


@ai_bp.route('/api/ai/status')
def ai_status():
    cfg = _cfg('chat')
    enabled = bool(cfg.get('api_key'))
    return jsonify({'success': True, 'enabled': enabled,
                    'model': cfg['model'] if enabled else None,
                    'source': cfg['source']})


def _require_ai(purpose='chat'):
    if not _cfg(purpose).get('api_key'):
        return jsonify({'success': False, 'error': 'AI 未配置,请到「设置 → AI 与模型」选择/配置模型'}), 503
    return None


# ============ 每用户模型配置(档案 + 功能分配) ============
@ai_bp.route('/api/ai/config', methods=['GET'])
def get_config():
    """返回全部档案(key 掩码)、功能分配、默认档案、自定义供应商模板。绝不下发明文 Key。"""
    return jsonify({'success': True, 'config': ai_svc.public_config(_uid())})


@ai_bp.route('/api/ai/profiles', methods=['POST'])
def upsert_profile():
    """新增/更新一套模型配置档案。带 id=更新;不带=新增。api_key 缺省=保留,''=清除。"""
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    base_url = (data.get('base_url') or '').strip()
    if not name:
        return jsonify({'success': False, 'error': '请填写配置名称'}), 400
    if base_url and not base_url.startswith(('http://', 'https://')):
        return jsonify({'success': False, 'error': 'Base URL 需以 http(s):// 开头'}), 400
    profile = {'id': data.get('id'), 'name': name, 'base_url': base_url,
               'model': (data.get('model') or '').strip()}
    if 'api_key' in data:           # 只有显式传了才动 key(支持 ''=清除)
        profile['api_key'] = data.get('api_key')
    try:
        pid, cfg = ai_svc.upsert_profile(_uid(), profile)
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    return jsonify({'success': True, 'profile_id': pid, 'config': cfg})


@ai_bp.route('/api/ai/profiles/<pid>', methods=['DELETE'])
def delete_profile(pid):
    return jsonify({'success': True, 'config': ai_svc.delete_profile(_uid(), pid)})


@ai_bp.route('/api/ai/config', methods=['PUT'])
def save_routing():
    """保存功能分配/默认档案/自定义供应商模板/自动分析开关(不改档案与 key)。"""
    data = request.get_json(silent=True) or {}
    custom_providers = data.get('custom_providers')
    if custom_providers is not None and not isinstance(custom_providers, list):
        return jsonify({'success': False, 'error': 'custom_providers 须为数组'}), 400
    cfg = ai_svc.save_routing(_uid(),
                              assignments=data.get('assignments'),
                              default_profile=data.get('default_profile'),
                              custom_providers=custom_providers,
                              auto_analyze=data.get('auto_analyze'))
    return jsonify({'success': True, 'config': cfg})


@ai_bp.route('/api/ai/config/test', methods=['POST'])
def test_config():
    """测试连接:可直接给 base_url/api_key/model;或给档案 id(缺的字段回落该档案已存值)。"""
    data = request.get_json(silent=True) or {}
    test_key = (data.get('api_key') or '').strip()
    test_base = (data.get('base_url') or '').strip().rstrip('/')
    test_model = (data.get('model') or '').strip()
    pid = (data.get('id') or data.get('profile_id') or '').strip()
    if pid:
        prof = next((p for p in ai_svc._normalized(_uid())['profiles'] if p['id'] == pid), None)
        if prof:
            test_key = test_key or prof['api_key']
            test_base = test_base or (prof['base_url'] or '').rstrip('/')
            test_model = test_model or prof['model']
    if not test_key:
        return jsonify({'success': False, 'error': '没有可用的 API Key(新档案请先填 Key 再测)'}), 400
    if not test_base:
        return jsonify({'success': False, 'error': '请填写 Base URL'}), 400
    ok, msg = ai_svc.test_ai_config({'base_url': test_base, 'api_key': test_key, 'model': test_model})
    return jsonify({'success': True, 'ok': ok, 'message': msg})


# ============ AI 智能分析(各分析维度的洞察报告) ============
@ai_bp.route('/api/ai/analyze', methods=['GET'])
def get_analysis_report():
    """取某维度已缓存的分析报告(不触发生成)。"""
    scope = (request.args.get('scope') or '').strip()
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    rec = analyze_svc.get_cached(_uid(), scope, year, month)
    return jsonify({'success': True, 'report': rec,
                    'auto': ai_svc.get_auto_analyze(_uid()),
                    'enabled': bool(_cfg('analysis').get('api_key'))})


@ai_bp.route('/api/ai/analyze', methods=['POST'])
def run_analysis_report():
    """生成(或取缓存)某维度的 AI 分析报告。{scope, year?, month?, force?}"""
    err = _require_ai('analysis')
    if err:
        return err
    data = request.get_json(silent=True) or {}
    scope = (data.get('scope') or '').strip()
    if scope not in analyze_svc.SCOPES:
        return jsonify({'success': False, 'error': '未知分析维度'}), 400
    try:
        df = load_alipay_data()
    except FileNotFoundError:
        return jsonify({'success': False, 'error': '当前账号还没有账单数据,请先上传'}), 400
    try:
        rec = analyze_svc.generate(_uid(), df, scope,
                                   year=data.get('year'), month=data.get('month'),
                                   force=bool(data.get('force')), cfg=_cfg('analysis'))
    except (ValueError, RuntimeError) as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.exception("AI 智能分析失败")
        return jsonify({'success': False, 'error': f'分析失败: {e}'}), 500
    return jsonify({'success': True, 'report': rec})


@ai_bp.route('/api/ai/chat', methods=['POST'])
def chat():
    err = _require_ai()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    question = (data.get('question') or '').strip()
    chat_id = (data.get('chat_id') or '').strip() or None
    if not question:
        return jsonify({'success': False, 'error': '问题不能为空'}), 400
    try:
        df = load_alipay_data()
    except FileNotFoundError:
        return jsonify({'success': False, 'error': '当前账号还没有账单数据,请先上传'}), 400
    uid = _uid()
    # 上下文:有 chat_id 用服务端存的历史(权威),否则用客户端传的
    history = chat_svc.history_for(uid, chat_id) if chat_id else data.get('history')
    try:
        result = ai_svc.chat_over_transactions(df, question, history, cfg=_cfg(), uid=uid)
    except Exception as e:
        logger.exception("AI chat 失败")
        return jsonify({'success': False, 'error': f'AI 调用失败: {e}'}), 500
    # 持久化本轮问答到会话历史
    try:
        chat_id = chat_svc.append_chat(uid, chat_id, question, result['answer'], result.get('tool_calls'))
    except Exception:
        logger.exception("保存对话历史失败(不影响回答)")
    return jsonify({'success': True, 'chat_id': chat_id, **result})


# ============ 对话历史 ============
@ai_bp.route('/api/ai/chats')
def list_chats():
    return jsonify({'success': True, 'chats': chat_svc.list_chats(_uid())})


@ai_bp.route('/api/ai/chats/<cid>')
def get_chat(cid):
    chat = chat_svc.get_chat(_uid(), cid)
    if not chat:
        return jsonify({'success': False, 'error': '会话不存在'}), 404
    return jsonify({'success': True, 'chat': chat})


@ai_bp.route('/api/ai/chats/<cid>', methods=['DELETE'])
def delete_chat(cid):
    ok = chat_svc.delete_chat(_uid(), cid)
    return jsonify({'success': ok} if ok else {'success': False, 'error': '会话不存在'})


@ai_bp.route('/api/ai/chats/<cid>', methods=['PUT'])
def rename_chat(cid):
    data = request.get_json(silent=True) or {}
    title = (data.get('title') or '').strip()
    if not title:
        return jsonify({'success': False, 'error': '标题不能为空'}), 400
    ok = chat_svc.rename_chat(_uid(), cid, title)
    return jsonify({'success': ok} if ok else {'success': False, 'error': '会话不存在'})


# ============ 导出文件下载(AI 生成) ============
import re as _re_dl
from flask import send_from_directory


@ai_bp.route('/api/ai/exports/<path:filename>')
def download_export(filename):
    """下载 AI 导出的文件(仅当前用户自己的 _exports 目录)。"""
    filename = os.path.basename(filename)   # 去掉任何路径成分
    if not _re_dl.match(r'^[\w一-龥()\-.]+\.(xlsx|csv)$', filename):
        return jsonify({'success': False, 'error': '非法文件名'}), 400
    exp_dir = os.path.join(get_session_dir(), '_exports')
    if not os.path.exists(os.path.join(exp_dir, filename)):
        return jsonify({'success': False, 'error': '文件不存在或已过期'}), 404
    return send_from_directory(exp_dir, filename, as_attachment=True)


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
    err = _require_ai('recognize')
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
        rows = ai_svc.recognize_bill(text, hint, cfg=_cfg('recognize'))
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.exception("AI 识别失败")
        return jsonify({'success': False, 'error': f'识别失败: {e}'}), 500
    return jsonify({'success': True, 'rows': rows, 'count': len(rows)})


_ALIPAY_HDR = "交易时间,交易分类,交易对方,对方账号,商品说明,收/支,金额,收/付款方式,交易状态,交易订单号,商家订单号,备注,"


@ai_bp.route('/api/ai/recognize/import', methods=['POST'])
def recognize_import():
    err = _require_ai('recognize')
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
