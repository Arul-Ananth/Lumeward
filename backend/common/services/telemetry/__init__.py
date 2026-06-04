from backend.common.services.telemetry.event_bus import EventBus, EventPriority, TelemetryEvent

__all__ = [
    "EventBus",
    "EventPriority",
    "TelemetryEvent",
    "TelemetryDispatcher",
    "DocumentIngestionWorker",
    "SessionSummaryWorker",
    "UserProfileRollupWorker",
]


def __getattr__(name: str):
    if name in {
        "TelemetryDispatcher",
        "DocumentIngestionWorker",
        "SessionSummaryWorker",
        "UserProfileRollupWorker",
    }:
        from backend.common.services.telemetry import workers

        return getattr(workers, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
