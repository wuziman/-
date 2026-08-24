"""
小红书博主帖子抓取（非官方接口，依赖用户提供的登录Cookie，随时可能因反爬升级失效）

原理：博主主页 https://www.xiaohongshu.com/user/profile/{id} 是服务端渲染页面，
HTML里内嵌 window.__INITIAL_STATE__ JSON，带浏览器UA+Cookie 直接GET即可解析出笔记列表。
Cookie从平台设置页粘贴（浏览器F12复制），约30天过期。

仅抓取博主公开笔记的标题/简介作为AI选股输入源，不下载图片、不做互动。
"""

import json
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urlparse

import requests
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import Setting
from ..models_platform import XhsPost

logger = logging.getLogger(__name__)

KEY_XHS_COOKIE = 'xhs_cookie'
KEY_XHS_BLOGGERS = 'xhs_bloggers'   # JSON: [{"name":"显示名","url":"https://www.xiaohongshu.com/user/profile/xxx"}]

_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
       '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')


# ============================================
# 配置读写（Setting表）
# ============================================
def get_xhs_config(db: Session) -> Dict:
    cookie_row = db.query(Setting).filter(Setting.key == KEY_XHS_COOKIE).first()
    bloggers_row = db.query(Setting).filter(Setting.key == KEY_XHS_BLOGGERS).first()
    try:
        bloggers = json.loads(bloggers_row.value) if bloggers_row and bloggers_row.value else []
    except (ValueError, TypeError):
        bloggers = []
    return {
        'cookie_set': bool(cookie_row and cookie_row.value),
        'bloggers': bloggers,
    }


def _is_xhs_url(url: str) -> bool:
    """博主URL域名白名单：只允许小红书域。
    抓取时会携带用户登录Cookie请求该URL——不设白名单的话，
    任何能写配置的路径都能把Cookie发往任意主机"""
    try:
        parts = urlparse(url)
    except ValueError:
        return False
    return (parts.scheme == 'https'
            and (parts.netloc == 'xiaohongshu.com'
                 or parts.netloc.endswith('.xiaohongshu.com')))


def set_xhs_config(db: Session, cookie: Optional[str] = None,
                   bloggers: Optional[List[Dict]] = None):
    def _upsert(key: str, value: str):
        row = db.query(Setting).filter(Setting.key == key).first()
        if row:
            row.value = value
        else:
            db.add(Setting(key=key, value=value))

    if cookie is not None:
        _upsert(KEY_XHS_COOKIE, cookie.strip())
    if bloggers is not None:
        clean = []
        for b in bloggers:
            if not (isinstance(b, dict) and b.get('url', '').strip()):
                continue
            url = b.get('url', '').strip()
            if '://' not in url:
                url = 'https://' + url   # 用户粘贴时常省略scheme
            if not _is_xhs_url(url):
                raise ValueError(
                    f'博主URL必须为 https://*.xiaohongshu.com 域名（携带登录Cookie抓取，'
                    f'不接受其他站点）: {url}')
            clean.append({'name': b.get('name', '').strip(), 'url': url})
        _upsert(KEY_XHS_BLOGGERS, json.dumps(clean, ensure_ascii=False))
    db.commit()


# ============================================
# 页面解析
# ============================================
def _extract_initial_state(html: str) -> Optional[Dict]:
    """从页面HTML提取window.__INITIAL_STATE__并转成可json.loads的对象"""
    m = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*</script>', html, re.S)
    if not m:
        return None
    raw = m.group(1)
    # JS对象字面量里的undefined不是合法JSON
    raw = re.sub(r'\bundefined\b', 'null', raw)
    try:
        return json.loads(raw)
    except ValueError as e:
        logger.warning(f"INITIAL_STATE解析失败: {e}")
        return None


def _walk_find_notes(obj, found: List[Dict], depth: int = 0):
    """在任意嵌套结构里收集形如笔记摘要的dict（有id且有标题字段）"""
    if depth > 6 or len(found) >= 40:
        return
    if isinstance(obj, dict):
        nid = obj.get('id') or obj.get('noteId')
        title = obj.get('displayTitle') or obj.get('title') or ''
        if nid and isinstance(nid, str) and title:
            found.append({
                'note_id': nid,
                'title': str(title)[:300],
                'desc': str(obj.get('desc') or '')[:500],
                'time': str(obj.get('time') or obj.get('publishTime') or ''),
                'url': f"https://www.xiaohongshu.com/explore/{nid}",
            })
            return  # 命中即不再下钻该节点
        for v in obj.values():
            _walk_find_notes(v, found, depth + 1)
    elif isinstance(obj, list):
        for v in obj:
            _walk_find_notes(v, found, depth + 1)


def fetch_profile_notes(blogger_name: str, profile_url: str, cookie: str) -> List[Dict]:
    """抓取单个博主主页的笔记列表（标题+简介）"""
    headers = {
        'User-Agent': _UA,
        'Accept': 'text/html,application/xhtml+xml',
        'Referer': 'https://www.xiaohongshu.com/',
    }
    if cookie:
        headers['Cookie'] = cookie

    resp = requests.get(profile_url, headers=headers, timeout=15)
    if resp.status_code != 200:
        raise RuntimeError(f'HTTP {resp.status_code}（Cookie可能过期或被风控）')
    state = _extract_initial_state(resp.text)
    if state is None:
        raise RuntimeError('页面未包含INITIAL_STATE（大概率被重定向到登录墙）')

    notes: List[Dict] = []
    _walk_find_notes(state, notes)
    for n in notes:
        n['blogger_name'] = blogger_name
    # 按note_id去重保序
    seen, unique = set(), []
    for n in notes:
        if n['note_id'] not in seen:
            seen.add(n['note_id'])
            unique.append(n)
    return unique


# ============================================
# 缓存与摘要
# ============================================
def refresh_all() -> Dict:
    """抓取全部配置博主的最新笔记并入库（按note_id去重）。返回各博主结果"""
    db = SessionLocal()
    try:
        cfg = get_xhs_config(db)
        cookie_row = db.query(Setting).filter(Setting.key == KEY_XHS_COOKIE).first()
        cookie = (cookie_row.value if cookie_row else '') or ''
    finally:
        db.close()

    results = {'bloggers': [], 'new_posts': 0}
    if not cfg['cookie_set']:
        return {**results, 'error': '未配置小红书Cookie，请在设置中粘贴'}
    if not cfg['bloggers']:
        return {**results, 'error': '未配置博主链接'}

    for b in cfg['bloggers']:
        entry = {'name': b['name'], 'count': 0, 'error': None}
        try:
            notes = fetch_profile_notes(b['name'], b['url'], cookie)
            db = SessionLocal()
            try:
                new_cnt = 0
                for n in notes:
                    exists = db.query(XhsPost.id).filter(
                        XhsPost.note_id == n['note_id']).first()
                    if exists:
                        continue
                    db.add(XhsPost(
                        note_id=n['note_id'], blogger_name=n['blogger_name'],
                        title=n['title'], content=n.get('desc', ''),
                        url=n['url'], posted_time=n.get('time') or None,
                        fetched_at=datetime.now()))
                    new_cnt += 1
                db.commit()
            finally:
                db.close()
            entry['count'] = len(notes)
            results['new_posts'] += new_cnt
        except Exception as e:
            logger.warning(f"小红书抓取失败[{b['name']}]: {e}")
            entry['error'] = str(e)
        results['bloggers'].append(entry)
    return results


def digest_recent(limit: int = 20) -> str:
    """最近缓存的帖子拼成喂给AI的文本摘要"""
    db = SessionLocal()
    try:
        rows = (db.query(XhsPost)
                .order_by(XhsPost.fetched_at.desc(), XhsPost.id.desc())
                .limit(limit).all())
    finally:
        db.close()
    if not rows:
        return '（暂无小红书博主内容）'
    lines = []
    for r in rows:
        text = f"- [{r.blogger_name}] {r.title}"
        if r.content:
            text += f"：{r.content[:150]}"
        lines.append(text)
    return '\n'.join(lines)
