"""Optional MLflow tracing integration via ``mlflow.gemini.autolog()``.

Guarded import — the server runs fine without ``mlflow-tracing`` installed.
When enabled, every ``genai.models.AsyncModels.generate_content`` call is
automatically traced (all 23 tools go through ``GeminiClient.generate``).

Configuration is read from :class:`~video_research_mcp.config.ServerConfig`
(which loads ``~/.config/video-research-mcp/.env``), so new users can add
``MLFLOW_TRACKING_URI`` to their ``.env`` file just like ``WEAVIATE_URL``.

Env vars (all have defaults, none required):
    GEMINI_TRACING_ENABLED: "true" (default) or "false" to opt out.
    MLFLOW_TRACKING_URI: Where to store traces (default ``./mlruns``).
    MLFLOW_EXPERIMENT_NAME: Experiment name (default ``video-research-mcp``).
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

try:
    import mlflow
    import mlflow.gemini

    _HAS_MLFLOW = True
except ImportError:
    _HAS_MLFLOW = False


def is_enabled() -> bool:
    """Return True when mlflow-tracing is installed and not explicitly disabled."""
    if not _HAS_MLFLOW:
        return False
    from .config import get_config

    return get_config().tracing_enabled


def setup() -> None:
    """Configure MLflow tracking and enable Gemini autologging.

    No-op when ``is_enabled()`` returns False. Failures are logged and
    swallowed — tracing must never prevent the server from starting.
    """
    if not is_enabled():
        return

    from .config import get_config

    cfg = get_config()
    tracking_uri = cfg.mlflow_tracking_uri
    experiment = cfg.mlflow_experiment_name

    try:
        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(experiment)
        mlflow.gemini.autolog()
        logger.info("MLflow tracing enabled (uri=%s, experiment=%s)", tracking_uri, experiment)
    except Exception:
        logger.warning("MLflow tracing setup failed — continuing without tracing", exc_info=True)


def shutdown() -> None:
    """Flush pending async traces.

    No-op when ``is_enabled()`` returns False.
    """
    if not is_enabled():
        return

    try:
        mlflow.flush_trace_async_logging()
        logger.info("MLflow traces flushed")
    except Exception:
        logger.warning("MLflow trace flush failed", exc_info=True)
