"""
持仓相关API
- 当前持仓 / 卖出 / 历史交易
- 总资金设置（仓位集中度预警用）
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Tuple
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from ..database import get_db
from ..models import Position, Setting
from ..models_platform import PortfolioSnapshot
from ..schemas import PositionCreate, PositionSell, PositionUpdate, PositionResponse
from ..services.alert_service import compute_drawdown_stats
from ..services.stock_service import StockService
from ..utils.market import detect_market

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])
stock_service = StockService()

# 风控规则（来自CLAUDE.md）
MAX_SINGLE_POSITION_PCT = 40.0   # 单只股票最大仓位40%
CASH_MIN_PCT = 15.0              # 现金保留下限15%
CASH_MAX_PCT = 25.0              # 现金保留上限25%


def _get_total_capital(db: Session) -> float:
    """读取总资金设置，未设置为0"""
    row = db.query(Setting).filter(Setting.key == "total_capital").first()
    try:
        return float(row.value) if row else 0.0
    except (TypeError, ValueError):
        return 0.0


def _realized_pnl(sell_price: float, buy_price: float, quantity: float) -> Tuple[float, float]:
    """已实现盈亏与百分比（卖出接口与单测共用同一实现）"""
    pnl = (sell_price - buy_price) * quantity
    pct = (sell_price - buy_price) / buy_price * 100 if buy_price else 0
    return round(pnl, 2), round(pct, 2)


def _fetch_quotes(positions: List[Position]) -> list:
    """并行拉取全部持仓实时行情（美股 yfinance .info 单次秒级，串行会随持仓数线性放大）"""
    with ThreadPoolExecutor(max_workers=8) as executor:
        return list(executor.map(
            lambda p: stock_service.get_realtime_quote(p.stock_code, detect_market(p.stock_code)),
            positions
        ))


@router.get("", response_model=List[PositionResponse])
def get_positions(db: Session = Depends(get_db)):
    """获取当前持仓列表（含实时盈亏 + 止损止盈触发状态）"""
    positions = db.query(Position).filter(Position.status == "holding").all()
    quotes = _fetch_quotes(positions)
    return [_enrich_holding(pos, quote) for pos, quote in zip(positions, quotes)]


def _enrich_holding(pos: Position, quote) -> PositionResponse:
    current_price = (quote or {}).get('price') or pos.buy_price
    profit_loss = (current_price - pos.buy_price) * pos.quantity
    profit_loss_pct = (current_price - pos.buy_price) / pos.buy_price * 100 if pos.buy_price else 0

    # 距止损/止盈的距离（百分比），供前端预警
    days_held = max((datetime.now() - pos.buy_date).days, 0)

    return PositionResponse(
        id=pos.id,
        stock_code=pos.stock_code,
        stock_name=pos.stock_name,
        market=pos.market,
        buy_price=pos.buy_price,
        quantity=pos.quantity,
        buy_date=pos.buy_date,
        stop_loss=pos.stop_loss,
        take_profit=pos.take_profit,
        status=pos.status,
        created_at=pos.created_at,
        current_price=round(current_price, 2),
        profit_loss=round(profit_loss, 2),
        profit_loss_pct=round(profit_loss_pct, 2),
        holding_days=days_held,
    )


@router.get("/history", response_model=List[PositionResponse])
async def get_position_history(db: Session = Depends(get_db)):
    """已卖出持仓（历史交易，含已实现盈亏与持有天数）"""
    positions = db.query(Position).filter(Position.status == "sold") \
        .order_by(Position.sell_date.desc()).all()

    result = []
    for pos in positions:
        realized_pnl = None
        realized_pct = None
        days = None
        if pos.sell_price is not None:
            realized_pnl = (pos.sell_price - pos.buy_price) * pos.quantity
            realized_pct = (pos.sell_price - pos.buy_price) / pos.buy_price * 100 if pos.buy_price else 0
        if pos.sell_date and pos.buy_date:
            days = max((pos.sell_date - pos.buy_date).days, 0)

        result.append(PositionResponse(
            id=pos.id,
            stock_code=pos.stock_code,
            stock_name=pos.stock_name,
            market=pos.market,
            buy_price=pos.buy_price,
            quantity=pos.quantity,
            buy_date=pos.buy_date,
            stop_loss=pos.stop_loss,
            take_profit=pos.take_profit,
            status=pos.status,
            sell_price=pos.sell_price,
            sell_date=pos.sell_date,
            created_at=pos.created_at,
            realized_pnl=round(realized_pnl, 2) if realized_pnl is not None else None,
            realized_pnl_pct=round(realized_pct, 2) if realized_pct is not None else None,
            holding_days=days,
        ))
    return result


@router.post("/{position_id}/sell")
async def sell_position(position_id: int, sell: PositionSell, db: Session = Depends(get_db)):
    """卖出持仓：记录卖出价/日期 → 已实现盈亏"""
    position = db.query(Position).filter(
        Position.id == position_id, Position.status == "holding"
    ).first()
    if not position:
        raise HTTPException(status_code=404, detail="持仓不存在或已卖出")

    position.status = "sold"
    position.sell_price = sell.sell_price
    position.sell_date = sell.sell_date
    db.commit()

    realized_pnl, realized_pct = _realized_pnl(sell.sell_price, position.buy_price, position.quantity)
    return {
        "message": "卖出成功",
        "realized_pnl": realized_pnl,
        "realized_pnl_pct": realized_pct,
        "holding_days": max((sell.sell_date - position.buy_date).days, 0),
    }


@router.post("", response_model=PositionResponse)
async def add_position(position: PositionCreate, db: Session = Depends(get_db)):
    """添加持仓"""
    if position.stop_loss is not None and position.stop_loss >= position.buy_price:
        raise HTTPException(status_code=400, detail="止损位应低于买入价")
    if position.take_profit is not None and position.take_profit <= position.buy_price:
        raise HTTPException(status_code=400, detail="止盈位应高于买入价")

    data = position.model_dump()
    # 市场判定后端单点：忽略客户端传值（此前前端用首字符正则复刻，BRK.B 类代码会误判）
    data['market'] = detect_market(position.stock_code)
    db_position = Position(**data)
    db.add(db_position)
    db.commit()
    db.refresh(db_position)

    return PositionResponse(
        id=db_position.id,
        stock_code=db_position.stock_code,
        stock_name=db_position.stock_name,
        market=db_position.market,
        buy_price=db_position.buy_price,
        quantity=db_position.quantity,
        buy_date=db_position.buy_date,
        stop_loss=db_position.stop_loss,
        take_profit=db_position.take_profit,
        status=db_position.status,
        created_at=db_position.created_at,
    )


@router.put("/{position_id}")
async def update_position(position_id: int, update: PositionUpdate,
                          db: Session = Depends(get_db)):
    """修改持仓：买入价/数量/买入日期/止损止盈（None=不修改；止损止盈显式传null=清除）"""
    position = db.query(Position).filter(Position.id == position_id).first()
    if not position:
        raise HTTPException(status_code=404, detail="未找到")

    if update.buy_price is not None:
        if update.buy_price <= 0:
            raise HTTPException(status_code=400, detail="买入价格必须大于0")
        position.buy_price = update.buy_price
    if update.quantity is not None:
        if update.quantity < 1:
            raise HTTPException(status_code=400, detail="数量必须大于0")
        position.quantity = update.quantity
    if update.buy_date is not None:
        position.buy_date = update.buy_date
    # 止损止盈：区分"未传"（保持不变）与"显式null"（清除）
    for field in ("stop_loss", "take_profit"):
        if field in update.model_fields_set:
            setattr(position, field, getattr(update, field))

    db.commit()
    return {"message": "更新成功"}


@router.delete("/{position_id}")
async def delete_position(position_id: int, db: Session = Depends(get_db)):
    """删除记录"""
    position = db.query(Position).filter(Position.id == position_id).first()
    if not position:
        raise HTTPException(status_code=404, detail="未找到")

    db.delete(position)
    db.commit()
    return {"message": "删除成功"}


# ============================================
# 设置：总资金（仓位集中度预警）
# ============================================
@router.get("/settings/total_capital")
async def get_total_capital(db: Session = Depends(get_db)):
    return {"total_capital": _get_total_capital(db)}


@router.put("/settings/total_capital")
async def set_total_capital(total_capital: float, db: Session = Depends(get_db)):
    if total_capital < 0:
        raise HTTPException(status_code=400, detail="总资金不能为负")
    row = db.query(Setting).filter(Setting.key == "total_capital").first()
    if row:
        row.value = str(total_capital)
    else:
        db.add(Setting(key="total_capital", value=str(total_capital)))
    db.commit()
    return {"message": "保存成功", "total_capital": total_capital}


@router.get("/summary")
def get_portfolio_summary(db: Session = Depends(get_db)):
    """持仓汇总 + 仓位集中度检查"""
    positions = db.query(Position).filter(Position.status == "holding").all()

    total_value = 0.0
    total_cost = 0.0
    per_stock_value = {}

    quotes = _fetch_quotes(positions)
    for pos, quote in zip(positions, quotes):
        current_price = (quote or {}).get('price') or pos.buy_price
        value = current_price * pos.quantity
        total_value += value
        total_cost += pos.buy_price * pos.quantity
        per_stock_value[pos.stock_code] = per_stock_value.get(pos.stock_code, 0) + value

    total_profit = total_value - total_cost
    total_profit_pct = (total_profit / total_cost * 100) if total_cost > 0 else 0

    total_capital = _get_total_capital(db)

    # ---- 仓位集中度预警 ----
    warnings = []
    base = total_capital if total_capital > 0 else total_value
    base_label = '总资金' if total_capital > 0 else '持仓总市值'
    for code, value in per_stock_value.items():
        weight = value / base * 100 if base > 0 else 0
        name = next((p.stock_name for p in positions if p.stock_code == code), code)
        if weight > MAX_SINGLE_POSITION_PCT:
            warnings.append({
                'level': 'error',
                'code': code,
                'name': name,
                'weight': round(weight, 1),
                'message': f"{name}({code})占{base_label} {weight:.1f}%，超过单票{MAX_SINGLE_POSITION_PCT}%上限，建议减仓"
            })

    cash_pct = (total_capital - total_value) / total_capital * 100 if total_capital > 0 else None
    if cash_pct is not None:
        if cash_pct < CASH_MIN_PCT:
            warnings.append({
                'level': 'warning',
                'code': '',
                'name': '',
                'weight': round(cash_pct, 1),
                'message': f"现金比例仅{cash_pct:.1f}%，低于{CASH_MIN_PCT:.0f}%下限，注意保留子弹"
            })
        elif cash_pct > CASH_MAX_PCT:
            warnings.append({
                'level': 'info',
                'code': '',
                'name': '',
                'weight': round(cash_pct, 1),
                'message': f"现金比例{cash_pct:.1f}%，高于{CASH_MAX_PCT:.0f}%上限，资金利用率偏低"
            })

    return {
        "total_positions": len(positions),
        "total_value": round(total_value, 2),
        "total_cost": round(total_cost, 2),
        "total_profit": round(total_profit, 2),
        "total_profit_pct": round(total_profit_pct, 2),
        "total_capital": total_capital,
        "cash_pct": round(cash_pct, 1) if cash_pct is not None else None,
        "warnings": warnings,
    }


@router.get("/equity-curve")
def get_equity_curve(db: Session = Depends(get_db)):
    """组合净值曲线（每日快照）+ 回撤统计；快照由后台价格监控任务在交易时段写入"""
    snaps = db.query(PortfolioSnapshot).order_by(PortfolioSnapshot.snap_date.asc()).all()
    curve = [{'date': s.snap_date, 'value': s.total_value} for s in snaps]
    stats = compute_drawdown_stats([s.total_value for s in snaps])
    return {'curve': curve, **stats}
