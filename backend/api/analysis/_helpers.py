"""api/analysis 子模块共享辅助函数。"""
from services.analysis import analyze_members


def _member_analysis_with_colors(df):
    """成员维度 + 按 members.json 附加成员配色。"""
    rows = analyze_members(df)
    try:
        from utils.session import get_current_uid
        from services import members as member_svc
        cmap = {m['name']: m.get('color', '#8E8E93')
                for m in member_svc.list_members(get_current_uid() or '__anon__')}
    except Exception:
        cmap = {}
    for r in rows:
        r['color'] = cmap.get(r['member'], '#8E8E93')
    return rows
