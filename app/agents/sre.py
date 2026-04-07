from typing import Dict, List, Any
import datetime

class SREAgent:
    """
    The Guardian of AgentNet.
    Monitors inter-agent communication, latency, and operational health.
    """
    
    def __init__(self):
        self.handover_logs: List[Dict[str, Any]] = []
        self.metrics: Dict[str, List[float]] = {}
        self.health_status = "HEALTHY"

    def log_handover(self, from_agent: str, to_agent: str, context: Dict[str, Any]):
        """
        Logs a successful handover between two agents.
        """
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "event": "HANDOVER",
            "from": from_agent,
            "to": to_agent,
            "data_transferred": list(context.keys())
        }
        self.handover_logs.append(log_entry)
        print(f"[SRE] Handover: {from_agent} -> {to_agent}")

    def log_latency(self, agent_name: str, duration_ms: float):
        """
        Tracks the performance of a specific agent.
        """
        if agent_name not in self.metrics:
            self.metrics[agent_name] = []
        
        self.metrics[agent_name].append(duration_ms)
        
        # Alert if an agent is lagging
        if duration_ms > 1000:
            print(f"[SRE ALERT] Agent '{agent_name}' is lagging: {duration_ms:.2f}ms")
            self.health_status = "DEGRADED"

    def get_node_health(self) -> Dict[str, Any]:
        """
        Simulates / Tracks the health of hardware nodes.
        """
        nodes = {
            "Gate Alpha": {"status": "ONLINE", "uptime": "99.9%", "latency": "12ms", "load": 24},
            "Gate Beta": {"status": "ONLINE", "uptime": "98.5%", "latency": "45ms", "load": 12},
            "Level 1": {"status": "ONLINE", "uptime": "99.9%", "latency": "8ms", "load": 45},
            "Level 2": {"status": "DEGRADED", "uptime": "92.1%", "latency": "156ms", "load": 89}
        }
        return nodes

    def get_system_report(self) -> Dict[str, Any]:
        """
        Generates a summary of the Network's health.
        """
        report = {
            "status": self.health_status,
            "active_agents": ["Vision", "Optimization", "Allocation", "SRE"],
            "total_handovers": len(self.handover_logs),
            "averages_ms": {
                name: round(sum(vals)/len(vals), 2) 
                for name, vals in self.metrics.items() if vals
            },
            "node_health": self.get_node_health()
        }
        return report

    async def check_health(self) -> bool:
        return self.health_status != "CRITICAL"
