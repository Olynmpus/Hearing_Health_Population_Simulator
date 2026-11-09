import pytest

from src.service_delivery.demand import ServiceDemand
from src.service_delivery.allocation import ServiceAllocation
from src.service_delivery.delivery import ServiceDelivery
from src.service_delivery.assessment import assess_service_delivery


def make_demand(demand_id):
    return ServiceDemand(
        demand_id=demand_id,
        agent_id=f"PERSON-{demand_id}",
        service_type="audiology_assessment",
        request_month=1,
        request_source="individual_request",
        evidence_status="simulation_assumption",
    )


def make_allocation(demand_id, status="allocated"):
    return ServiceAllocation(
        demand_id=demand_id,
        agent_id=f"PERSON-{demand_id}",
        service_id="SERVICE-001",
        service_type="audiology_assessment",
        age_group="working_age_adult",
        clinician_id="CLINICIAN-001",
        allocation_status=status,
        reason="test",
    )


def make_delivery(demand_id, attendance, delivery):
    return ServiceDelivery(
        demand_id=demand_id,
        agent_id=f"PERSON-{demand_id}",
        service_id="SERVICE-001",
        service_type="audiology_assessment",
        clinician_id="CLINICIAN-001",
        delivery_month=2,
        attendance_status=attendance,
        delivery_status=delivery,
        evidence_status="simulation_assumption",
    )


def test_assesses_allocation_and_delivery_counts():
    demands = [make_demand(str(i)) for i in range(1, 5)]
    allocations = [
        make_allocation("1"),
        make_allocation("2"),
        make_allocation("3", "unallocated"),
        make_allocation("4"),
    ]
    deliveries = [
        make_delivery("1", "attended", "delivered"),
        make_delivery("2", "did_not_attend", "not_delivered"),
    ]

    result = assess_service_delivery(demands, allocations, deliveries)

    assert result.requested_count == 4
    assert result.allocated_count == 3
    assert result.unallocated_count == 1
    assert result.pending_delivery_count == 1
    assert result.attended_count == 1
    assert result.did_not_attend_count == 1
    assert result.delivered_count == 1
    assert result.not_delivered_count == 1


def test_empty_records_return_zero_counts():
    result = assess_service_delivery([], [], [])

    assert result.requested_count == 0
    assert result.allocated_count == 0
    assert result.unallocated_count == 0
    assert result.pending_delivery_count == 0
    assert result.delivered_count == 0


def test_unknown_delivery_status_is_not_treated_as_failure():
    demands = [make_demand("1")]
    allocations = [make_allocation("1")]
    deliveries = [make_delivery("1", "unknown", "unknown")]

    result = assess_service_delivery(demands, allocations, deliveries)

    assert result.attendance_recorded_count == 1
    assert result.attended_count == 0
    assert result.did_not_attend_count == 0
    assert result.delivery_recorded_count == 1
    assert result.delivered_count == 0
    assert result.not_delivered_count == 0
    assert result.pending_delivery_count == 0


def test_rejects_delivery_without_matching_allocation():
    delivery = make_delivery("999", "attended", "delivered")

    with pytest.raises(ValueError, match="unknown demand"):
        assess_service_delivery([], [], [delivery])


def test_rejects_duplicate_demand_ids():
    demands = [make_demand("1"), make_demand("1")]

    with pytest.raises(ValueError, match="Duplicate demand"):
        assess_service_delivery(demands, [], [])


def test_rejects_duplicate_allocations():
    demands = [make_demand("1")]
    allocations = [
        make_allocation("1"),
        make_allocation("1"),
    ]

    with pytest.raises(ValueError, match="Duplicate allocation"):
        assess_service_delivery(demands, allocations, [])


def test_rejects_duplicate_delivery_records():
    demands = [make_demand("1")]
    allocations = [make_allocation("1")]
    deliveries = [
        make_delivery("1", "attended", "delivered"),
        make_delivery("1", "attended", "delivered"),
    ]

    with pytest.raises(ValueError, match="Duplicate delivery"):
        assess_service_delivery(demands, allocations, deliveries)


def test_rejects_missing_allocation_outcome():
    demands = [make_demand("1")]

    with pytest.raises(ValueError, match="Every demand must have an allocation"):
        assess_service_delivery(demands, [], [])


def test_rejects_invalid_allocation_record():
    demands = [make_demand("1")]
    allocation = make_allocation("1")
    allocation.allocation_status = "invalid"

    with pytest.raises(ValueError):
        assess_service_delivery(demands, [allocation], [])


def test_rejects_invalid_delivery_record():
    demands = [make_demand("1")]
    allocations = [make_allocation("1")]
    delivery = make_delivery("1", "attended", "delivered")
    delivery.delivery_status = "invalid"

    with pytest.raises(ValueError):
        assess_service_delivery(demands, allocations, [delivery])


def test_rejects_non_list_inputs():
    with pytest.raises(TypeError):
        assess_service_delivery(None, [], [])

    with pytest.raises(TypeError):
        assess_service_delivery([], None, [])

    with pytest.raises(TypeError):
        assess_service_delivery([], [], None)


def test_serialises_assessment():
    result = assess_service_delivery(
        [make_demand("1")],
        [make_allocation("1")],
        [make_delivery("1", "attended", "delivered")],
    )

    data = result.to_dict()

    assert data["requested_count"] == 1
    assert data["allocated_count"] == 1
    assert data["delivered_count"] == 1
