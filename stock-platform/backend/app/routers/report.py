"""
每日报告API
- GET  /api/report/preview   生成日报预览（不推送）
- POST /api/report/send      生成并推送企业微信（dry_run=true仅生成）
- GET  /api/report/schedule  查询定时日报配置
- PUT  /api/report/schedule  更新定时日报配置
- POST /api/report/run-now   立即生成并推送一次（无视开关）
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Watchlist
from ..services.report_service import ReportService
from ..services import scheduler_service

router = APIRouter(prefix="/api/report", tags=["report"])
report_service = ReportService()


class ReportSendRequest(BaseModel):
    dry_run: bool = True  # True=仅生成不推送


def _build_report(db: Session):
    watchlist = db.query(Watchlist).order_by(Watchlist.created_at.desc()).all()
    if not watchlist:
        raise HTTPException(status_code=400, detail="自选股列表为空，请先在分析页添加自选股")

    items = [{'stock_code': w.stock_code, 'stock_name': w.stock_name} for w in watchlist]
    return report_service.generate_daily_report(items)


@router.get("/preview")
def preview_daily_report(db: Session = Depends(get_db)):
    """生成日报预览（不推送）"""
    return _build_report(db)


@router.post("/send")
def send_daily_report(req: ReportSendRequest, db: Session = Depends(get_db)):
    """生成并推送日报到企业微信"""
    report_data = _build_report(db)

    if req.dry_run:
        return {**report_data, 'sent': False, 'message': 'dry_run模式：仅生成未推送'}

    result = report_service.send_to_wechat(report_data['report'])
    return {
        **report_data,
        'sent': result.get('sent', False),
        'send_error': result.get('error'),
        'message': '推送成功' if result.get('sent') else f"推送失败: {result.get('error')}"
    }


# ============================================
# 定时自动日报
# ============================================
class ScheduleUpdateRequest(BaseModel):
    enabled: bool
    hour: int = Field(default=17, ge=0, le=23)
    minute: int = Field(default=30, ge=0, le=59)


@router.get("/schedule")
async def get_schedule(db: Session = Depends(get_db)):
    """查询定时日报配置"""
    return scheduler_service.get_schedule_config(db)


@router.put("/schedule")
async def update_schedule(req: ScheduleUpdateRequest, db: Session = Depends(get_db)):
    """更新定时日报配置（写入Setting）"""
    scheduler_service._set_setting(
        db, scheduler_service.KEY_ENABLED, 'true' if req.enabled else 'false')
    scheduler_service._set_setting(
        db, scheduler_service.KEY_HOUR, str(req.hour))
    scheduler_service._set_setting(
        db, scheduler_service.KEY_MINUTE, str(req.minute))
    cfg = scheduler_service.get_schedule_config(db)
    return {'message': '保存成功', **cfg}


@router.post("/run-now")
def run_report_now():
    """立即生成日报并推送企业微信（无视开关；同步def由FastAPI放入线程池，避免阻塞事件循环）"""
    return scheduler_service.run_now()
