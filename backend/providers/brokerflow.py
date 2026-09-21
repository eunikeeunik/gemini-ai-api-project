"""
EquityLens AI - Broker Flow Provider (Bandarmologi / Foreign Flow)
Per blueprint: No reliable free source for IDX broker summary / foreign flow.
Provides NullBrokerFlow returning available: false with reason.
"""
from typing import Dict, Any

class BrokerFlowProvider:
    def get_flow(self, code: str) -> Dict[str, Any]:
        raise NotImplementedError

class NullBrokerFlow(BrokerFlowProvider):
    def get_flow(self, code: str) -> Dict[str, Any]:
        return {
            "symbol": f"IDX:{code.upper()}",
            "available": False,
            "reason": "Butuh sumber data berbayar (mis. Invezgo/Sectors) untuk broker summary & foreign flow IDX",
            "provider": "NullBrokerFlow"
        }

broker_flow_provider = NullBrokerFlow()

def get_broker_flow(code: str) -> Dict[str, Any]:
    return broker_flow_provider.get_flow(code)
