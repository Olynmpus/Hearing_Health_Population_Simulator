import pytest

from src.service_delivery.allocation import ServiceAllocation
from src.service_delivery.delivery import (
    ServiceDelivery,
    create_service_delivery,
)


def make_allocation(status="allocated"):
    return ServiceAllocation(
        demand_id="DEMAND-001",
        agent_id="PERSON-001",
        service_id="SERVICE-001",
        service_type="audiology_assessment",
        age_group="working_age_adult",
        clinician_id="CLINICIAN-001",
        allocation_status=status,
        reason="matching_request_allocated",
    )


def test_creates_successful_service_delivery():
    result = create_service_delivery(
        allocation=make_allocation(),
        delivery_month=2,
        attendance_status="attended",
        delivery_status="delivered",
        evidence_status="user_reported",
    )

    assert result.validate() is True
    assert result.demand_id == "DEMAND-001"
    assert result.delivery_status == "delivered"


def test_records_attendance_without_confirming_delivery():
    result = create_service_delivery(
        allocation=make_allocation(),
        delivery_month=2,
        attendance_status="attended",
        delivery_status="unknown",
    )

    assert result.attendance_status == "attended"
    assert result.delivery_status == "unknown"


def test_records_non_attendance():
    result = create_service_delivery(
        allocation=make_allocation(),
        delivery_month=2,
        attendance_status="did_not_attend",
        delivery_status="not_delivered",
    )

    assert result.delivery_status == "not_delivered"


def test_rejects_delivery_for_unallocated_request():
    with pytest.raises(ValueError, match="only be recorded for allocated"):
        create_service_delivery(
            allocation=make_allocation("unallocated"),
            delivery_month=2,
            attendance_status="attended",
            delivery_status="delivered",
        )


@pytest.mark.parametrize("month", [-1, 1.5, True, "2"])
def test_rejects_invalid_delivery_month(month):
    with pytest.raises(ValueError):
        create_service_delivery(
            allocation=make_allocation(),
            delivery_month=month,
            attendance_status="attended",
            delivery_status="delivered",
        )


def test_rejects_delivered_service_without_attendance():
    with pytest.raises(ValueError, match="requires attended"):
        create_service_delivery(
            allocation=make_allocation(),
            delivery_month=2,
            attendance_status="did_not_attend",
            delivery_status="delivered",
        )


def test_rejects_attended_service_marked_not_delivered():
    with pytest.raises(ValueError, match="cannot be marked not_delivered"):
        create_service_delivery(
            allocation=make_allocation(),
            delivery_month=2,
            attendance_status="attended",
            delivery_status="not_delivered",
        )


def test_rejects_invalid_attendance_status():
    with pytest.raises(ValueError, match="Invalid attendance"):
        create_service_delivery(
            allocation=make_allocation(),
            delivery_month=2,
            attendance_status="invalid",
            delivery_status="unknown",
        )


def test_rejects_invalid_delivery_status():
    with pytest.raises(ValueError, match="Invalid delivery"):
        create_service_delivery(
            allocation=make_allocation(),
            delivery_month=2,
            attendance_status="attended",
            delivery_status="invalid",
        )


def test_rejects_invalid_evidence_status():
    with pytest.raises(ValueError, match="Invalid evidence"):
        create_service_delivery(
            allocation=make_allocation(),
            delivery_month=2,
            attendance_status="attended",
            delivery_status="delivered",
            evidence_status="invalid",
        )


def test_delivery_can_be_serialised():
    result = create_service_delivery(
        allocation=make_allocation(),
        delivery_month=2,
        attendance_status="attended",
        delivery_status="delivered",
    )

    data = result.to_dict()

    assert data["demand_id"] == "DEMAND-001"
    assert data["agent_id"] == "PERSON-001"
    assert data["delivery_month"] == 2


def test_rejects_non_allocation_input():
    with pytest.raises(TypeError):
        create_service_delivery(
            allocation="not an allocation",
            delivery_month=2,
            attendance_status="attended",
            delivery_status="delivered",
        )
