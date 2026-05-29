"""
轻量可观测性指标（进程内聚合）。
用于竞赛演示：HTTP 延迟/错误率、LLM 调用成功率、与监控 API 汇总。
使用 threading.Lock，可在异步中间件与同步 LLM 调用中安全更新。
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Any, Deque, Dict, List, Optional

_lock = threading.Lock()

_http_total: int = 0
_http_4xx: int = 0
_http_5xx: int = 0
_latency_ms: Deque[float] = deque(maxlen=500)
_path_stats: Dict[str, Dict[str, float]] = {}

_llm_calls: int = 0
_llm_failures: int = 0
_llm_latency_ms: Deque[float] = deque(maxlen=200)
_graph_node_stats: Dict[str, Dict[str, float]] = {}
_trace_index: Dict[str, List[Dict[str, Any]]] = {}


def record_http_request(path: str, status_code: int, latency_ms: float) -> None:
    """记录一次 HTTP 请求（由 FastAPI 中间件调用）。"""
    global _http_total, _http_4xx, _http_5xx
    with _lock:
        _http_total += 1
        if 400 <= status_code < 500:
            _http_4xx += 1
        elif status_code >= 500:
            _http_5xx += 1
        _latency_ms.append(latency_ms)
        bucket = _path_stats.setdefault(path, {"count": 0, "errors": 0, "sum_ms": 0.0})
        bucket["count"] += 1
        bucket["sum_ms"] += latency_ms
        if status_code >= 400:
            bucket["errors"] += 1


def record_llm_call(latency_ms: float, failed: bool) -> None:
    """记录一次 LLM 调用（failed=True 表示抛异常或明确失败）。"""
    global _llm_calls, _llm_failures
    with _lock:
        _llm_calls += 1
        if failed:
            _llm_failures += 1
        _llm_latency_ms.append(latency_ms)


def record_graph_node_execution(
    trace_id: str,
    node_name: str,
    elapsed_ms: float,
    status: str,
    learner_id: str,
    knowledge_id: str,
) -> None:
    """记录一次 graph 节点执行（含 trace 维度索引）。"""
    if not trace_id:
        return
    with _lock:
        bucket = _graph_node_stats.setdefault(
            node_name,
            {"count": 0, "errors": 0, "sum_ms": 0.0, "max_ms": 0.0},
        )
        bucket["count"] += 1
        bucket["sum_ms"] += elapsed_ms
        bucket["max_ms"] = max(bucket["max_ms"], elapsed_ms)
        if status != "ok":
            bucket["errors"] += 1

        rows = _trace_index.setdefault(trace_id, [])
        rows.append(
            {
                "node_name": node_name,
                "elapsed_ms": round(float(elapsed_ms), 2),
                "status": status,
                "learner_id": learner_id,
                "knowledge_id": knowledge_id,
            }
        )
        if len(rows) > 30:
            _trace_index[trace_id] = rows[-30:]
        if len(_trace_index) > 1000:
            oldest = next(iter(_trace_index))
            _trace_index.pop(oldest, None)


def get_trace_detail(trace_id: str) -> Dict[str, Any]:
    """按 trace_id 查询节点链路明细。"""
    with _lock:
        nodes = list(_trace_index.get(trace_id, []))
    return {"trace_id": trace_id, "nodes": nodes, "found": len(nodes) > 0}


def _percentile(sorted_samples: List[float], p: float) -> Optional[float]:
    if not sorted_samples:
        return None
    if len(sorted_samples) == 1:
        return float(sorted_samples[0])
    k = (len(sorted_samples) - 1) * p / 100.0
    lo = int(k)
    hi = min(lo + 1, len(sorted_samples) - 1)
    w = k - lo
    return float(sorted_samples[lo] * (1 - w) + sorted_samples[hi] * w)


def get_http_metrics_snapshot() -> Dict[str, Any]:
    """返回 HTTP 指标快照（拷贝，可供 JSON 序列化）。"""
    with _lock:
        http_total = _http_total
        http_4xx = _http_4xx
        http_5xx = _http_5xx
        llm_calls = _llm_calls
        llm_failures = _llm_failures
        lat = list(_latency_ms)
        llm_lat = list(_llm_latency_ms)
        paths = {
            p: {
                "count": int(v["count"]),
                "errors": int(v["errors"]),
                "avg_latency_ms": round(v["sum_ms"] / max(1, v["count"]), 2),
            }
            for p, v in _path_stats.items()
        }
        node_stats = {
            node: {
                "count": int(v["count"]),
                "errors": int(v["errors"]),
                "avg_elapsed_ms": round(v["sum_ms"] / max(1, v["count"]), 2),
                "max_elapsed_ms": round(v["max_ms"], 2),
            }
            for node, v in _graph_node_stats.items()
        }
    lat_sorted = sorted(lat)
    llm_sorted = sorted(llm_lat)
    total_err = http_4xx + http_5xx
    return {
        "http": {
            "total_requests": http_total,
            "errors_4xx": http_4xx,
            "errors_5xx": http_5xx,
            "error_rate": round(total_err / max(1, http_total), 4),
            "avg_latency_ms": round(sum(lat) / max(1, len(lat)), 2),
            "p50_latency_ms": _percentile(lat_sorted, 50),
            "p95_latency_ms": _percentile(lat_sorted, 95),
            "recent_sample_count": len(lat),
        },
        "by_path": paths,
        "llm": {
            "total_calls": llm_calls,
            "failures": llm_failures,
            "success_rate": round(1.0 - (llm_failures / max(1, llm_calls)), 4),
            "avg_latency_ms": round(sum(llm_lat) / max(1, len(llm_lat)), 2),
            "p95_latency_ms": _percentile(llm_sorted, 95),
        },
        "graph": {
            "node_stats": node_stats,
            "trace_count": len(_trace_index),
        },
    }


def reset_metrics() -> None:
    """测试或演示前清零（可选）。"""
    global _http_total, _http_4xx, _http_5xx, _llm_calls, _llm_failures
    with _lock:
        _http_total = 0
        _http_4xx = 0
        _http_5xx = 0
        _latency_ms.clear()
        _path_stats.clear()
        _llm_calls = 0
        _llm_failures = 0
        _llm_latency_ms.clear()
        _graph_node_stats.clear()
        _trace_index.clear()
