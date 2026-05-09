"""Token utilization metrics — LangChain callback that records Ollama LLM stats."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

logger = logging.getLogger(__name__)

METRICS_PATH = Path(__file__).parent.parent / "data" / "metrics.jsonl"


class TokenMetricsCallback(BaseCallbackHandler):
    """Append one JSON line to data/metrics.jsonl after every LLM call."""

    def __init__(self, agent_name: str, num_ctx: int, num_predict: int) -> None:
        super().__init__()
        self.agent_name = agent_name
        self.num_ctx = num_ctx
        self.num_predict = num_predict

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        try:
            for gen_list in response.generations:
                for gen in gen_list:
                    info: dict = getattr(gen, "generation_info", None) or {}
                    prompt_tokens = info.get("prompt_eval_count", 0)
                    gen_tokens    = info.get("eval_count", 0)
                    done_reason   = info.get("done_reason", "unknown")
                    eval_ns       = info.get("eval_duration", 0)
                    total_ns      = info.get("total_duration", 0)
                    tps = round(gen_tokens / (eval_ns / 1e9), 1) if eval_ns > 0 else 0.0

                    entry = {
                        "ts":           datetime.now().isoformat(timespec="seconds"),
                        "agent":        self.agent_name,
                        "prompt_tokens": prompt_tokens,
                        "num_ctx":       self.num_ctx,
                        "ctx_util":      round(prompt_tokens / self.num_ctx * 100, 1) if self.num_ctx else 0,
                        "gen_tokens":    gen_tokens,
                        "num_predict":   self.num_predict,
                        "predict_util":  round(gen_tokens / self.num_predict * 100, 1) if self.num_predict else 0,
                        "done_reason":   done_reason,
                        "tps":           tps,
                        "total_ms":      round(total_ns / 1e6),
                    }

                    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
                    with open(METRICS_PATH, "a", encoding="utf-8") as f:
                        f.write(json.dumps(entry) + "\n")
        except Exception:
            logger.debug("TokenMetricsCallback error", exc_info=True)
