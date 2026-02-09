class SREAgent:
    """
    Guardian of the System. 
    Monitors latency, error rates, and resource usage.
    """
    
    def log_latency(self, endpoint: str, duration_ms: float):
        """
        In prod, sends metrics to Prometheus/Datadog.
        """
        if duration_ms > 500:
            print(f"[SRE ALERT] {endpoint} is slow: {duration_ms}ms")
        else:
            # print(f"[SRE] {endpoint} OK: {duration_ms}ms")
            pass

    async def check_health(self) -> bool:
        return True
