"""
config/config.json 单点读取器。

此前 analysis_service/_load_api_keys、report_service/_load_webhook、
llm_client/load_ai_provider_config 各自实现路径推导与容错，行为各异。
统一约定：
- 路径：<repo根>/config/config.json（repo根 = 本文件 parents[4]，与密钥位置 memory 记录一致）
- 任何读取异常返回空配置，不抛出；环境变量优先于文件由各调用方自行叠加
"""
import json
from pathlib import Path
from typing import Dict

_CONFIG_PATH = Path(__file__).resolve().parents[4] / 'config' / 'config.json'


def load_config() -> Dict:
    """读取整个 config.json；文件缺失/损坏时返回 {}"""
    try:
        with open(_CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}
