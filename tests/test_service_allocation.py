import pytest

from src.agents.agent import Agent, AgentProfile
from src.service_capacity.planned_schedule import PlannedServiceSchedule
from src.service_delivery.demand import ServiceDemand
from src.service_delivery.allocation import allocate_service_demand


def make_agent(agent_id, age_group="working_age_adult"):
    return Agent(
        agent_id=agent_id,
        profile=AgentProfile(
            age_group=age_group,
            hearing_profile="moderate",
            geography="regional",
        ),
    )


def make_demand(
    demand_id,
    agent_id,
    service_type="audiology_assessment",
):
    return ServiceDemand(
        demand_id=demand_id,
        agent_id=agent_id,
        service_type=service_type,
        request_month=1,
        request_source="individual_request",
        evidence_status="simulation_assumption",
    )


def make_schedule(appointments=2):
    return PlannedServiceSchedule(
        service_id="SERVICE-001",
        service_type="audiology_assessment",
        age_group="working_age_adult",
        clinician_id="CLINICIAN-001",
        planned_trips_per_month=1,
        planned_appointments_per_month=appointments,
        planned_clinical_hours_per_month=float(appointments),
        maximum_deliverable_appointments_per_month=12,
        schedule_status="valid",
    )


def test_allocates_matching_requests():
    agents = [make_agent("PERSON-001"), make_agent("PERSON-002")]
    demands = [
        make_demand("DEMAND-001", "PERSON-001"),
        make_demand("DEMAND-002", "PERSON-002"),
    ]

    result = allocate_service_demand(demands, agents, make_schedule())

    assert len(result) == 2
    assert all(item.allocation_status == "allocated" for item in result)


def test_allocation_never_exceeds_planned_appointments():
    agents = [
        make_agent("PERSON-001"),
        make_agent("PERSON-002"),
        make_agent("PERSON-003"),
    ]
    demands = [
        make_demand("DEMAND-001", "PERSON-001"),
        make_demand("DEMAND-002", "PERSON-002"),
        make_demand("DEMAND-003", "PERSON-003"),
    ]

    result = allocate_service_demand(demands, agents, make_schedule(2))

    allocated = [
        item for item in result
        if item.allocation_status == "allocated"
    ]
    unallocated = [
        item for item in result
        if item.allocation_status == "unallocated"
    ]

    assert len(allocated) == 2
    assert len(unallocated) == 1
    assert unallocated[0].reason == "planned_appointment_capacity_exhausted"


def test_zero_planned_appointments_means_no_allocations():
    agents = [make_agent("PERSON-001")]
    demands = [make_demand("DEMAND-001", "PERSON-001")]

    result = allocate_service_demand(demands, agents, make_schedule(0))

    assert result[0].allocation_status == "unallocated"


def test_rejects_request_for_different_service():
    agents = [make_agent("PERSON-001")]
    demands = [
        make_demand(
            "DEMAND-001",
            "PERSON-001",
            "communication_support",
        )
    ]

    result = allocate_service_demand(demands, agents, make_schedule())

    assert result[0].allocation_status == "unallocated"
    assert result[0].reason == "service_type_not_in_schedule"


def test_rejects_request_outside_scheduled_age_group():
    agents = [
        make_agent("PERSON-001", age_group="older_adult")
    ]
    demands = [make_demand("DEMAND-001", "PERSON-001")]

    result = allocate_service_demand(demands, agents, make_schedule())

    assert result[0].allocation_status == "unallocated"
    assert result[0].reason == "age_group_not_in_schedule"


def test_unallocated_requests_remain_in_results():
    agents = [make_agent("PERSON-001")]
    demands = [make_demand("DEMAND-001", "PERSON-001")]

    result = allocate_service_demand(demands, agents, make_schedule(0))

    assert len(result) == 1
    assert result[0].demand_id == "DEMAND-001"


def test_same_person_can_have_multiple_independent_requests():
    agents = [make_agent("PERSON-001")]
    demands = [
        make_demand("DEMAND-001", "PERSON-001"),
        make_demand(
            "DEMAND-002",
            "PERSON-001",
            "communication_support",
        ),
    ]

    result = allocate_service_demand(demands, agents, make_schedule(1))

    assert len(result) == 2
    assert result[0].allocation_status == "allocated"
    assert result[1].allocation_status == "unallocated"


def test_rejects_duplicate_demand_ids():
    agents = [make_agent("PERSON-001")]
    demands = [
        make_demand("DEMAND-001", "PERSON-001"),
        make_demand("DEMAND-001", "PERSON-001"),
    ]

    with pytest.raises(ValueError, match="Duplicate demand ID"):
        allocate_service_demand(demands, agents, make_schedule())


def test_rejects_missing_agent():
    demands = [make_demand("DEMAND-001", "PERSON-999")]

    with pytest.raises(ValueError, match="No Agent found"):
        allocate_service_demand(demands, [], make_schedule())


def test_allocation_can_be_serialised():
    agents = [make_agent("PERSON-001")]
    demands = [make_demand("DEMAND-001", "PERSON-001")]

    result = allocate_service_demand(demands, agents, make_schedule())
    data = result[0].to_dict()

    assert data["demand_id"] == "DEMAND-001"
    assert data["allocation_status"] == "allocated"
