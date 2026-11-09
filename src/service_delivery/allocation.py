"""Allocation of explicit service demand against planned capacity."""

from dataclasses import asdict, dataclass

from src.agents.agent import Agent
from src.service_capacity.planned_schedule import PlannedServiceSchedule

from .demand import ServiceDemand


@dataclass
class ServiceAllocation:
    """Records the allocation outcome for one service demand."""

    demand_id: str
    agent_id: str
    service_id: str
    service_type: str
    age_group: str
    clinician_id: str
    allocation_status: str
    reason: str

    def validate(self):
        for name in (
            "demand_id",
            "agent_id",
            "service_id",
            "service_type",
            "age_group",
            "clinician_id",
            "reason",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string.")

        if self.allocation_status not in {"allocated", "unallocated"}:
            raise ValueError("Invalid allocation status.")

        return True

    def to_dict(self):
        self.validate()
        return asdict(self)


def allocate_service_demand(
    demands: list[ServiceDemand],
    agents: list[Agent],
    planned_schedule: PlannedServiceSchedule,
) -> list[ServiceAllocation]:
    """Allocate matching requests without exceeding planned appointments.

    Requests are processed in their supplied order. Every valid demand
    receives an allocation outcome, including requests that cannot be
    allocated.
    """

    if not isinstance(demands, list):
        raise TypeError("demands must be a list.")

    if not isinstance(agents, list):
        raise TypeError("agents must be a list.")

    if not isinstance(planned_schedule, PlannedServiceSchedule):
        raise TypeError(
            "planned_schedule must be a PlannedServiceSchedule."
        )

    planned_schedule.validate()

    agent_lookup = {}

    for agent in agents:
        if not isinstance(agent, Agent):
            raise TypeError("Every population member must be an Agent.")

        agent.validate()

        if agent.agent_id in agent_lookup:
            raise ValueError(f"Duplicate agent ID: {agent.agent_id}")

        agent_lookup[agent.agent_id] = agent

    demand_ids = set()

    for demand in demands:
        if not isinstance(demand, ServiceDemand):
            raise TypeError("Every demand must be a ServiceDemand.")

        demand.validate()

        if demand.demand_id in demand_ids:
            raise ValueError(f"Duplicate demand ID: {demand.demand_id}")

        demand_ids.add(demand.demand_id)

        if demand.agent_id not in agent_lookup:
            raise ValueError(
                f"No Agent found for demand: {demand.demand_id}"
            )

    allocations = []
    allocated_count = 0
    capacity = planned_schedule.planned_appointments_per_month

    for demand in demands:
        agent = agent_lookup[demand.agent_id]
        age_group = agent.profile.age_group

        status = "unallocated"

        if demand.service_type != planned_schedule.service_type:
            reason = "service_type_not_in_schedule"

        elif age_group != planned_schedule.age_group:
            reason = "age_group_not_in_schedule"

        elif allocated_count >= capacity:
            reason = "planned_appointment_capacity_exhausted"

        else:
            status = "allocated"
            reason = "matching_request_allocated"
            allocated_count += 1

        allocations.append(
            ServiceAllocation(
                demand_id=demand.demand_id,
                agent_id=demand.agent_id,
                service_id=planned_schedule.service_id,
                service_type=demand.service_type,
                age_group=age_group,
                clinician_id=planned_schedule.clinician_id,
                allocation_status=status,
                reason=reason,
            )
        )

    return allocations
