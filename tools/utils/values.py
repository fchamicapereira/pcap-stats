from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Values:
    requested_bps: float = 0
    pktgen_bps: float = 0
    pktgen_pps: float = 0
    dut_ingress_bps: float = 0
    dut_ingress_pps: float = 0
    dut_egress_bps: float = 0
    dut_egress_pps: float = 0
    label: Optional[str] = None
