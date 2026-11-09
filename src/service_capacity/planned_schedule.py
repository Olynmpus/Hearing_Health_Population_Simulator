"""Explicit planned service delivery schedules."""

from dataclasses import asdict, dataclass
import math

from .assessment import ServiceCapacityAssessment
from .deployment import MobileServiceDeployment
from .workforce import WorkforceMember


@dataclass
class PlannedServiceSchedule:
    """Monthly planned delivery activity for one assessed service."""

    service_id: str
    service_type: str
    age_group: str
    clinician_id: str

    planned_trips_per_month: int
    planned_appointments_per_month: int
    planned_clinical_hours_per_month: float

    maximum_deliverable_appointments_per_month: int
    schedule_status: str

    def validate(self):
        """Validate the schedule's internal data and consistency."""

        for name, value in (
            ("service_id", self.service_id),
            ("service_type", self.service_type),
            ("age_group", self.age_group),
            ("clinician_id", self.clinician_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string.")

        for name, value in (
            ("planned_trips_per_month", self.planned_trips_per_month),
            ("planned_appointments_per_month", self.planned_appointments_per_month),
            (
                "maximum_deliverable_appointments_per_month",
                self.maximum_deliverable_appointments_per_month,
            ),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer.")

        hours = self.planned_clinical_hours_per_month

        if (
            isinstance(hours, bool)
            or not isinstance(hours, (int, float))
            or not math.isfinite(hours)
            or hours < 0
        ):
            raise ValueError(
                "planned_clinical_hours_per_month must be finite and non-negative."
            )

        if self.schedule_status != "valid":
            raise ValueError("Schedule must have valid status.")

        if (
            self.planned_appointments_per_month
            > self.maximum_deliverable_appointments_per_month
        ):
            raise ValueError(
                "Planned appointments exceed maximum deliverable capacity."
            )

    def to_dict(self):
        self.validate()
        return asdict(self)


def create_planned_service_schedule(
    capacity_assessment: ServiceCapacityAssessment,
    workforce: WorkforceMember,
    deployment: MobileServiceDeployment,
    planned_trips_per_month: int,
    planned_appointments_per_month: int,
    planned_clinical_hours_per_month: float,
) -> PlannedServiceSchedule:
    """Validate a proposed monthly schedule against assessed capacity."""

    if not isinstance(capacity_assessment, ServiceCapacityAssessment):
        raise TypeError(
            "capacity_assessment must be a ServiceCapacityAssessment."
        )

    if not isinstance(workforce, WorkforceMember):
        raise TypeError("workforce must be a WorkforceMember.")

    if not isinstance(deployment, MobileServiceDeployment):
        raise TypeError("deployment must be a MobileServiceDeployment.")

    workforce.validate()
    deployment.validate()

    for name, value in (
        ("planned_trips_per_month", planned_trips_per_month),
        ("planned_appointments_per_month", planned_appointments_per_month),
    ):
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
        ):
            raise ValueError(
                f"{name} must be a non-negative integer."
            )

    if (
        isinstance(planned_clinical_hours_per_month, bool)
        or not isinstance(planned_clinical_hours_per_month, (int, float))
        or not math.isfinite(planned_clinical_hours_per_month)
        or planned_clinical_hours_per_month < 0
    ):
        raise ValueError(
            "planned_clinical_hours_per_month must be finite "
            "and non-negative."
        )

    if capacity_assessment.assessment_status != "eligible":
        raise ValueError(
            "A planned delivery schedule requires an eligible "
            "capacity assessment."
        )

    if deployment.service_id != capacity_assessment.service_id:
        raise ValueError(
            "Deployment service ID does not match capacity assessment."
        )

    if capacity_assessment.service_type not in deployment.service_types:
        raise ValueError(
            "Deployment does not support the assessed service type."
        )

    if capacity_assessment.age_group not in deployment.target_age_groups:
        raise ValueError(
            "Deployment does not target the assessed age group."
        )

    if capacity_assessment.service_type not in workforce.service_types:
        raise ValueError(
            "Workforce member does not support the assessed service type."
        )

    if capacity_assessment.age_group not in workforce.supported_age_groups:
        raise ValueError(
            "Workforce member does not support the assessed age group."
        )

    if planned_trips_per_month > capacity_assessment.trips_per_month:
        raise ValueError(
            "Planned trips exceed available monthly trip capacity."
        )

    maximum_appointments_from_trips = (
        planned_trips_per_month
        * capacity_assessment.appointments_per_trip
    )

    if (
        planned_appointments_per_month
        > maximum_appointments_from_trips
    ):
        raise ValueError(
            "Planned appointments exceed the capacity of planned trips."
        )

    if (
        planned_appointments_per_month
        > capacity_assessment.deliverable_capacity_per_month
    ):
        raise ValueError(
            "Planned appointments exceed assessed deliverable capacity."
        )

    required_clinical_hours = (
        planned_appointments_per_month
        * workforce.appointment_duration_minutes
        / 60
    )

    if planned_clinical_hours_per_month < required_clinical_hours:
        raise ValueError(
            "Planned clinical hours are insufficient for the "
            "planned appointments."
        )

    if (
        planned_clinical_hours_per_month
        > workforce.available_clinical_hours_per_month
    ):
        raise ValueError(
            "Planned clinical hours exceed monthly workforce availability."
        )

    maximum_deployment_hours = (
        planned_trips_per_month
        * deployment.service_delivery_hours_per_trip
    )

    if planned_clinical_hours_per_month > maximum_deployment_hours:
        raise ValueError(
            "Planned clinical hours exceed deployment delivery hours."
        )

    schedule = PlannedServiceSchedule(
        service_id=capacity_assessment.service_id,
        service_type=capacity_assessment.service_type,
        age_group=capacity_assessment.age_group,
        clinician_id=workforce.clinician_id,
        planned_trips_per_month=planned_trips_per_month,
        planned_appointments_per_month=planned_appointments_per_month,
        planned_clinical_hours_per_month=(
            planned_clinical_hours_per_month
        ),
        maximum_deliverable_appointments_per_month=(
            capacity_assessment.deliverable_capacity_per_month
        ),
        schedule_status="valid",
    )

    schedule.validate()
    return schedule
