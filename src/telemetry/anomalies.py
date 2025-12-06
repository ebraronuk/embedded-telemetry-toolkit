"""Detects anomalies in telemetry streams (placeholder)."""
from .schemas import TelemetryBatch


class AnomalyDetector:
    """Finds anomalies within telemetry batches."""

    def detect(self, batch: TelemetryBatch) -> list:
        """Return an empty list of anomalies placeholder."""
        _ = batch  # placeholder use
        return []
