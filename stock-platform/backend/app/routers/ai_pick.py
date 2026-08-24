"""
AI选股相关API
- GET  /api/ai-pick/status       配置状态（不回传key本身）
- POST /api/ai-pick/run          运行一次AI选股（耗时约1-3分钟）
- GET  /api/ai-pick/history      历史选股结果
- GET  /api/ai-pick/xhs-config   小红书配置读取
- PUT  /api/ai-pick/xhs-config   小红书配置保存（Cookie/博主列表）
- POST /api/ai-pick/xhs-refresh  手动抓取博主最新帖子
- GET  /api/ai-pick/xhs-summaries 已存博主总结
- POST /api/ai-pick/xhs-summaries 生成各博主近期帖子AI总结
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models_platform import AIPick, XhsPost
from ..services import xhs_service
from ..services.ai_pick_service import generate_xhs_summaries, get_xhs_summaries, run_ai_pick
from ..services.llm_client import is_ai_configured, load_ai_provider_config

router = APIRouter(prefix="/api/ai-pick", tags=["ai-pick"])


@router.get("/status")
def get_status(db: Session = Depends(get_db)):
    """配置状态总览（key等敏感信息只返回是否已设置）"""
    cfg = load_ai_provider_config()
    xhs_cfg = xhs_service.get_xhs_config(db)
    last_run = (db.query(AIPick).order_by(AIPick.id.desc()).first())
    post_count = db.query(XhsPost).count()
    return {
        'ai_configured': is_ai_configured(),
        'ai_model': cfg['model'] if is_ai_configured() else '',
        'xhs_cookie_set': xhs_cfg['cookie_set'],
        'bloggers': xhs_cfg['bloggers'],
        'cached_posts': post_count,
        'last_run_date': last_run.run_date if last_run else None,
    }


@router.post("/run")
def run_selection():
    """运行一次完整AI选股（拉数据+LLM分析，约1-3分钟；同步def走线程池）"""
    try:
        return run_ai_pick()
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI选股失败: {e}")


@router.get("/history")
def get_history(limit: int = 30, db: Session = Depends(get_db)):
    """历史选股记录（新→旧）"""
    rows = (db.query(AIPick)
            .order_by(AIPick.created_at.desc(), AIPick.rank.asc())
            .limit(limit).all())
    return [{
        'id': r.id,
        'run_date': r.run_date,
        'created_at': r.created_at.isoformat() if r.created_at else None,
        'rank': r.rank,
        'stock_code': r.stock_code,
        'stock_name': r.stock_name,
        'confidence': r.confidence,
        'thesis': r.thesis,
        'bottlenecks': r.bottlenecks,
        'risks': r.risks,
        'catalysts': r.catalysts,
        'market_commentary': r.market_commentary,
        'price_at_pick': r.price_at_pick,
    } for r in rows]


class XhsConfigRequest(BaseModel):
    cookie: str = None       # None=不改，空串=清除
    bloggers: list = None    # [{"name":"显示名","url":"https://www.xiaohongshu.com/user/profile/xxx"}]


@router.get("/xhs-config")
def get_xhs_config(db: Session = Depends(get_db)):
    return xhs_service.get_xhs_config(db)


@router.put("/xhs-config")
def put_xhs_config(req: XhsConfigRequest, db: Session = Depends(get_db)):
    try:
        xhs_service.set_xhs_config(db, cookie=req.cookie, bloggers=req.bloggers)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {'message': '保存成功', **xhs_service.get_xhs_config(db)}


@router.post("/xhs-refresh")
def refresh_xhs():
    """抓取全部博主最新帖子入库（需已配Cookie）"""
    result = xhs_service.refresh_all()
    if result.get('error'):
        raise HTTPException(status_code=400, detail=result['error'])
    return result


class XhsPostsRequest(BaseModel):
    limit: int = 20


@router.post("/xhs-posts")
def list_xhs_posts(req: XhsPostsRequest, db: Session = Depends(get_db)):
    """查看缓存的帖子列表"""
    rows = (db.query(XhsPost)
            .order_by(XhsPost.fetched_at.desc(), XhsPost.id.desc())
            .limit(req.limit).all())
    return [{
        'note_id': r.note_id, 'blogger_name': r.blogger_name,
        'title': r.title, 'url': r.url,
        'fetched_at': r.fetched_at.isoformat() if r.fetched_at else None,
    } for r in rows]


@router.get("/xhs-summaries")
def read_xhs_summaries(db: Session = Depends(get_db)):
    """已存博主总结（新→旧）"""
    return get_xhs_summaries(db)


@router.post("/xhs-summaries")
def refresh_xhs_summaries():
    """为每个配置博主生成近期帖子AI总结（每博主一次LLM调用，约几秒/人）"""
    try:
        return generate_xhs_summaries()
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"博主总结生成失败: {e}")
