"""Records actual attendance and hearing-service delivery."""

from dataclasses import asdict, dataclass

from src.hearing_support.service_access import (
    ATTENDANCE_STATUSES,
    EVIDENCE_STATUSES,
)

from .allocation import ServiceAllocation


DELIVERY_STATUSES = {
    "delivered",
    "not_delivered",
    "unknown",
}


@dataclass
class ServiceDelivery:
    """Records the outcome of one allocated service request."""

    demand_id: str
    agent_id: str
    service_id: str
    service_type: str
    clinician_id: str
    delivery_month: int
    attendance_status: str
    delivery_status: str
    evidence_status: str = "unknown"

    def validate(self):
        for name in (
            "demand_id",
            "agent_id",
            "service_id",
            "service_type",
            "clinician_id",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string.")

        if (
            isinstance(self.delivery_month, bool)
            or not isinstance(self.delivery_month, int)
            or self.delivery_month < 0
        ):
            raise ValueError(
                "delivery_month must be a non-negative integer."
            )

        if self.attendance_status not in ATTENDANCE_STATUSES:
            raise ValueError("Invalid attendance status.")

        if self.delivery_status not in DELIVERY_STATUSES:
            raise ValueError("Invalid delivery status.")

        if self.evidence_status not in EVIDENCE_STATUSES:
            raise ValueError("Invalid evidence status.")

        if (
            self.delivery_status == "delivered"
            and self.attendance_status != "attended"
        ):
            raise ValueError(
                "A delivered service requires attended status."
            )

        if (
            self.delivery_status == "not_delivered"
            and self.attendance_status == "attended"
        ):
            raise ValueError(
                "An attended appointment cannot be marked not_delivered."
            )

        return True

    def to_dict(self):
        self.validate()
        return asdict(self)


def create_service_delivery(
    allocation: ServiceAllocation,
    delivery_month: int,
    attendance_status: str,
    delivery_status: str,
    evidence_status: str = "unknown",
) -> ServiceDelivery:
    """Create a delivery record for an allocated service request."""

    if not isinstance(allocation, ServiceAllocation):
        raise TypeError("allocation must be a ServiceAllocation.")

    allocation.validate()

    if allocation.allocation_status != "allocated":
        raise ValueError(
            "Service delivery can only be recorded for allocated demand."
        )

    delivery = ServiceDelivery(
        demand_id=allocation.demand_id,
        agent_id=allocation.agent_id,
        service_id=allocation.service_id,
        service_type=allocation.service_type,
        clinician_id=allocation.clinician_id,
        delivery_month=delivery_month,
        attendance_status=attendance_status,
        delivery_status=delivery_status,
        evidence_status=evidence_status,
    )

    delivery.validate()
    return delivery
