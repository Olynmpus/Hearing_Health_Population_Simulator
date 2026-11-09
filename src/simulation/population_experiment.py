"""Initial population experiment setup."""

import json
import random
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from src.config_loader import load_experiment_config
from src.country_config import load_country_profile
from src.population.generator import generate_population
from src.population.integration import create_hearing_support_records
from src.hearing_support.need import HearingSupportNeed
from src.service_delivery.demand import ServiceDemand
from src.service_delivery.allocation import allocate_service_demand

from src.service_capacity.assessment import assess_mobile_service_capacity
from src.service_capacity.age_suitability import AgeServiceSuitability
from src.service_capacity.deployment import MobileServiceDeployment
from src.service_capacity.geographic_access import GeographicRoute
from src.service_capacity.planned_schedule import create_planned_service_schedule
from src.service_capacity.workforce import WorkforceMember
from src.service_delivery.delivery import create_service_delivery
from src.interventions.loader import load_intervention
from src.service_capacity.planned_schedule import PlannedServiceSchedule
from src.agents.relationships import SocialRelationship

def create_household_relationships(agents):
    """Create reciprocal family relationships within synthetic households."""

    households = {}

    for agent in agents:
        if agent.household_id is not None:
            households.setdefault(agent.household_id, []).append(agent)

    relationships = []

    for household_members in households.values():
        for agent in household_members:
            for other_agent in household_members:
                if agent.agent_id == other_agent.agent_id:
                    continue

                relationship = SocialRelationship(
                    agent_id=agent.agent_id,
                    contact_id=other_agent.agent_id,
                    relationship_type="family",
                )
                relationship.validate()
                relationships.append(relationship)

    return relationships

def generate_remote_round_trip_travel_hours(random_seed):
    """Generate a reproducible illustrative remote travel time."""

    rng = random.Random(
        random_seed + 3 if random_seed is not None else None
    )

    return rng.randint(201, 1199) / 100

@dataclass
class PopulationExperiment:
    """Initialised synthetic population experiment."""

    experiment_id: str
    experiment_name: str
    country_profile_id: str
    country_name: str
    population_size: int
    duration_months: int
    random_seed: int | None
    distribution_profile_id: str
    evidence_status: str
    agents: list
    support_records: list
    relationships: list
    relationship_evidence_status: str | None = None
    intervention: object | None = None
    remote_travel_hours: float | None = None
    remote_travel_hours: float | None = None

    def summary(self):
        """Return population counts and profile distributions."""

        def distribution(values):
            values = list(values)
            counts = Counter(values)
            total = len(values)
            return {
                category: {
                    "count": count,
                    "percentage": round(count / total * 100, 1),
                }
                for category, count in sorted(counts.items())
            }

        demands = [
            demand
            for record in self.support_records
            for demand in record.service_demands
        ]

        allocations = [
            allocation
            for record in self.support_records
            for allocation in record.service_allocations
        ]

        deliveries = [
            delivery
            for record in self.support_records
            for delivery in record.service_deliveries
        ]

        allocation_counts = Counter(
            allocation.allocation_status for allocation in allocations
        )

        attendance_counts = Counter(
            delivery.attendance_status for delivery in deliveries
        )

        delivery_counts = Counter(
            delivery.delivery_status for delivery in deliveries
        )

        allocations_by_clinician = Counter(
            allocation.clinician_id
            for allocation in allocations
            if allocation.allocation_status == "allocated"
        )

        deliveries_by_clinician = Counter(
            delivery.clinician_id for delivery in deliveries
        )

        return {
            "experiment_id": self.experiment_id,
            "experiment_name": self.experiment_name,
            "country_profile_id": self.country_profile_id,
            "country_name": self.country_name,
            "population_size": self.population_size,
            "duration_months": self.duration_months,
            "random_seed": self.random_seed,
            "distribution_profile_id": self.distribution_profile_id,
            "evidence_status": self.evidence_status,
            "intervention": (
                {
                    "intervention_id": self.intervention.intervention_id,
                    "name": self.intervention.name,
                    "evidence_status": self.intervention.evidence_status,
                    "remote_round_trip_travel_hours": self.remote_travel_hours,
                    "remote_round_trip_travel_hours": self.remote_travel_hours,
                }
                if self.intervention is not None
                else None
            ),
            "agent_count": len(self.agents),
            "support_record_count": len(self.support_records),
            "service_delivery": {
                "total_demands": len(demands),
                "allocated": allocation_counts["allocated"],
                "unallocated": allocation_counts["unallocated"],
                "attendance": dict(attendance_counts),
                "delivery_outcomes": dict(delivery_counts),
                "allocations_by_clinician": dict(allocations_by_clinician),
                "deliveries_by_clinician": dict(deliveries_by_clinician),
            },
            "population_distributions": {
                "age_group": distribution(
                    agent.profile.age_group for agent in self.agents
                ),
                "hearing_profile": distribution(
                    agent.profile.hearing_profile for agent in self.agents
                ),
                "geography": distribution(
                    agent.profile.geography for agent in self.agents
                ),
                "functional_status": distribution(
                    agent.profile.auditory_functional_status
                    for agent in self.agents
                ),
            },
        }

def initialise_hearing_support_needs(support_records):
    """Create an initial month-zero need assessment for each individual.

    Functional difficulty is preserved from the agent profile.
    Perceived need and help-seeking intention remain unknown.
    """

    for record in support_records:
        need = HearingSupportNeed(
            agent_id=record.agent_id,
            assessment_month=0,
            functional_difficulty_status=(
                record.agent.profile.auditory_functional_status
            ),
            perceived_need="unknown",
            help_seeking_intention="unknown",
            help_seeking_action="unknown",
            evidence_status="simulation_assumption",
        )

        record.add_hearing_support_need(need)

    return support_records

def generate_service_demands(
    experiment_config,
    support_records,
    intervention=None,
):
    """Generate illustrative annual service requests."""

    settings = experiment_config["demand"]
    duration_months = experiment_config["simulation"]["duration_months"]
    seed = experiment_config["simulation"].get("random_seed")

    probability = settings["annual_request_probability"]
    rng = random.Random(seed + 1 if seed is not None else None)
    remote_rng = random.Random(seed + 3 if seed is not None else None)

    demand_number = 1
    outreach_months = [0, 3, 6, 9]

    for record in support_records:
        profile = record.agent.profile

        if profile.age_group != settings["target_age_group"]:
            continue

        geography = profile.geography

        if geography == settings["target_geography"]:
            request_months = list(range(duration_months))

        elif (
            intervention is not None
            and "remote_very_remote" in intervention.target_geographies
            and geography == "remote_very_remote"
        ):
            request_months = [
                month for month in outreach_months
                if month < duration_months
            ]

        else:
            continue

        demand_rng = (
            remote_rng
            if geography == "remote_very_remote"
            else rng
        )

        if not request_months or demand_rng.random() >= probability:
            continue

        request_month = demand_rng.choice(request_months)

        demand = ServiceDemand(
            demand_id=f"DEMAND-{demand_number:06d}",
            agent_id=record.agent_id,
            service_type=settings["service_type"],
            request_month=request_month,
            request_source=settings["request_source"],
            evidence_status=settings["evidence_status"],
        )

        record.add_service_demand(demand)
        demand_number += 1

    return support_records

def create_experiment_service_schedule():
    """Create the illustrative regional audiology service schedule."""

    workforce = WorkforceMember(
        clinician_id="CLINICIAN-001",
        role="audiologist",
        qualifications=["Audiology qualification"],
        service_types=["audiology_assessment"],
        supported_age_groups=["working_age_adult"],
        available_clinical_hours_per_month=20,
        appointment_duration_minutes=60,
        evidence_status="simulation_assumption",
    )

    route = GeographicRoute(
        route_id="ROUTE-001",
        service_id="SERVICE-001",
        destination_geography="regional",
        round_trip_distance_km=200,
        round_trip_travel_hours=4,
        maximum_round_trip_distance_km=300,
        available_travel_hours_per_month=8,
        evidence_status="simulation_assumption",
    )

    deployment = MobileServiceDeployment(
        deployment_id="DEPLOYMENT-001",
        service_id="SERVICE-001",
        route_id="ROUTE-001",
        service_types=["audiology_assessment"],
        target_age_groups=["working_age_adult"],
        service_delivery_hours_per_trip=6,
        evidence_status="simulation_assumption",
    )

    suitability = AgeServiceSuitability(
        age_group="working_age_adult",
        service_type="audiology_assessment",
        suitability_status="suitable",
        requirements=[],
        limitations=[],
        evidence_status="simulation_assumption",
    )

    capacity = assess_mobile_service_capacity(
        workforce,
        route,
        deployment,
        suitability,
        "audiology_assessment",
        "working_age_adult",
    )

    return create_planned_service_schedule(
        capacity_assessment=capacity,
        workforce=workforce,
        deployment=deployment,
        planned_trips_per_month=1,
        planned_appointments_per_month=4,
        planned_clinical_hours_per_month=4,
    )

def create_remote_service_schedule():
    """Create the quarterly remote outreach schedule."""

    schedule = PlannedServiceSchedule(
        service_id="SERVICE-REMOTE-001",
        service_type="audiology_assessment",
        age_group="working_age_adult",
        clinician_id="CLINICIAN-001",
        planned_trips_per_month=1,
        planned_appointments_per_month=2,
        planned_clinical_hours_per_month=2,
        maximum_deliverable_appointments_per_month=2,
        schedule_status="valid",
    )

    schedule.validate()
    return schedule

def allocate_monthly_service_demands(
    agents,
    support_records,
    planned_schedule,
    duration_months,
    remote_schedule=None,
    remote_travel_hours=None,
):
    """Allocate monthly requests against planned service capacity."""

    record_lookup = {
        record.agent_id: record
        for record in support_records
    }

    agent_lookup = {
        agent.agent_id: agent
        for agent in agents
    }

    for month in range(duration_months):
        monthly_demands = [
            demand
            for record in support_records
            for demand in record.service_demands
            if demand.request_month == month
        ]

        regional_demands = [
            demand
            for demand in monthly_demands
            if agent_lookup[demand.agent_id].profile.geography == "regional"
        ]

        allocations = allocate_service_demand(
            demands=regional_demands,
            agents=agents,
            planned_schedule=planned_schedule,
        )

        
        if (
            remote_schedule is not None
            and remote_travel_hours is not None
            and month in (0, 3, 6, 9)
        ):
            remote_demands = [
                demand
                for demand in monthly_demands
                if agent_lookup[demand.agent_id].profile.geography
                == "remote_very_remote"
            ]

            remote_allocations = allocate_service_demand(
                demands=remote_demands,
                agents=agents,
                planned_schedule=remote_schedule,
            )

            allocations.extend(remote_allocations)

        for allocation in allocations:
            record_lookup[allocation.agent_id].add_service_allocation(
                allocation
            )

    return support_records

def record_monthly_service_delivery(
    support_records,
    experiment_config,
):
    """Record attendance and service delivery for allocated appointments."""

    settings = experiment_config["attendance"]
    probability = settings["attendance_probability"]
    evidence_status = settings["evidence_status"]

    seed = experiment_config["simulation"].get("random_seed")
    rng = random.Random(seed + 2 if seed is not None else None)

    for record in support_records:
        for allocation in record.service_allocations:
            if allocation.allocation_status != "allocated":
                continue

            attended = rng.random() < probability

            delivery = create_service_delivery(
                allocation=allocation,
                delivery_month=allocation_month(allocation),
                attendance_status=(
                    "attended" if attended else "did_not_attend"
                ),
                delivery_status=(
                    "delivered" if attended else "not_delivered"
                ),
                evidence_status=evidence_status,
            )

            record.add_service_delivery(delivery)

    return support_records

def record_monthly_service_delivery(
    support_records,
    experiment_config,
):
    """Record attendance and service delivery for allocated appointments."""

    settings = experiment_config["attendance"]
    probability = settings["attendance_probability"]
    evidence_status = settings["evidence_status"]

    seed = experiment_config["simulation"].get("random_seed")
    rng = random.Random(seed + 2 if seed is not None else None)

    demand_months = {
        demand.demand_id: demand.request_month
        for record in support_records
        for demand in record.service_demands
    }

    for record in support_records:
        for allocation in record.service_allocations:
            if allocation.allocation_status != "allocated":
                continue

            attended = rng.random() < probability

            delivery = create_service_delivery(
                allocation=allocation,
                delivery_month=demand_months[allocation.demand_id],
                attendance_status=(
                    "attended" if attended else "did_not_attend"
                ),
                delivery_status=(
                    "delivered" if attended else "not_delivered"
                ),
                evidence_status=evidence_status,
            )

            record.add_service_delivery(delivery)

    return support_records

def run_population_experiment(
    experiment_config_path,
    distribution_config_path,
    intervention_config_path=None,
):
    """Load configurations and initialise the synthetic population."""
    intervention = None

    if intervention_config_path is not None:
        intervention = load_intervention(
            intervention_config_path
        )

    experiment_config = load_experiment_config(
        experiment_config_path
    )

    experiment_path = Path(experiment_config_path).resolve()

    country_profile_path = (
        experiment_path.parent
        / experiment_config["country_profile"]
    )

    country_profile = load_country_profile(country_profile_path)

    distribution_path = Path(distribution_config_path)

    if not distribution_path.exists():
        raise FileNotFoundError(
            f"Population configuration not found: {distribution_path}"
        )

    with distribution_path.open("r", encoding="utf-8-sig") as file:
        distribution_config = json.load(file)

    if not isinstance(distribution_config, dict):
        raise ValueError(
            "Population distribution configuration must be an object."
        )

    agents = generate_population(
        experiment_config,
        distribution_config,
        country_profile=country_profile,
    )

    relationships = create_household_relationships(agents)

    household_config = experiment_config.get(
        "population", {}
    ).get("households", {})

    relationship_evidence_status = household_config.get(
        "evidence_status"
    )

    support_records = create_hearing_support_records(agents)

    support_records = initialise_hearing_support_needs(
        support_records
    )

    support_records = generate_service_demands(
        experiment_config,
        support_records,
        intervention=intervention,
    )
    planned_schedule = create_experiment_service_schedule()


    remote_travel_hours = (
        generate_remote_round_trip_travel_hours(
            experiment_config["simulation"].get("random_seed")
        )
        if intervention is not None
        else None
    )

    remote_schedule = (
        create_remote_service_schedule()
        if intervention is not None
        else None
    )
    support_records = allocate_monthly_service_demands(
        agents=agents,
        support_records=support_records,
        planned_schedule=planned_schedule,
        duration_months=experiment_config["simulation"]["duration_months"],
        remote_schedule=remote_schedule,
        remote_travel_hours=remote_travel_hours,
    )

    support_records = record_monthly_service_delivery(
        support_records=support_records,
        experiment_config=experiment_config,
    )

    return PopulationExperiment(
        experiment_id=experiment_config["experiment_id"],
        experiment_name=experiment_config.get(
            "experiment_name",
            experiment_config["experiment_id"],
        ),
        country_profile_id=country_profile["country_profile_id"],
        country_name=country_profile["country_name"],
        population_size=len(agents),
        duration_months=experiment_config["simulation"]["duration_months"],
        random_seed=experiment_config["simulation"].get("random_seed"),
        distribution_profile_id=distribution_config.get(
            "profile_id",
            "unknown",
        ),
        evidence_status=distribution_config["evidence_status"],
        agents=agents,
        support_records=support_records,
        relationships=relationships,
        relationship_evidence_status=relationship_evidence_status,
        intervention=intervention,
        remote_travel_hours=remote_travel_hours,
    )
