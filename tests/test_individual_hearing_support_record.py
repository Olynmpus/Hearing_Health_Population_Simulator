import unittest

from src.agents.agent import Agent, AgentProfile
from src.hearing_support.funding import FundingArrangement
from src.hearing_support.service_access import ServiceAccess
from src.hearing_support.journey import HearingCareJourney, JourneyEvent
from src.hearing_support.individual_record import (
    IndividualHearingSupportRecord,
)


def create_agent(agent_id="PERSON-001"):
    return Agent(
        agent_id=agent_id,
        profile=AgentProfile(
            age_group="working_age_adult",
            hearing_profile="moderate",
            geography="regional",
        ),
    )


class TestIndividualHearingSupportRecord(unittest.TestCase):

    def setUp(self):
        self.agent = create_agent()
        self.record = IndividualHearingSupportRecord(
            agent=self.agent
        )

    def test_empty_record_is_valid(self):
        self.assertTrue(self.record.validate())

    def test_agent_id_matches(self):
        self.assertEqual(self.record.agent_id, "PERSON-001")

    def test_add_funding_arrangement(self):
        arrangement = FundingArrangement(
            agent_id="PERSON-001",
            funding_pathway="mixed",
            private_contribution=300.0,
            out_of_pocket_cost=400.0,
        )

        self.record.add_funding_arrangement(arrangement)

        self.assertEqual(len(self.record.funding_arrangements), 1)
        self.assertTrue(self.record.validate())

    def test_add_service_access(self):
        access = ServiceAccess(
            agent_id="PERSON-001",
            service_type="audiology_assessment",
            pathway="public",
            availability_status="available",
            appointment_status="scheduled",
        )

        self.record.add_service_access(access)

        self.assertEqual(len(self.record.service_access_records), 1)
        self.assertTrue(self.record.validate())

    def test_add_journey(self):
        journey = HearingCareJourney(
            agent_id="PERSON-001",
            journey_id="JOURNEY-001",
            status="active",
        )

        self.record.add_journey(journey)

        self.assertEqual(len(self.record.journeys), 1)
        self.assertTrue(self.record.validate())

    def test_reject_funding_for_different_agent(self):
        arrangement = FundingArrangement(
            agent_id="PERSON-002"
        )

        with self.assertRaises(ValueError):
            self.record.add_funding_arrangement(arrangement)

    def test_reject_service_access_for_different_agent(self):
        access = ServiceAccess(
            agent_id="PERSON-002"
        )

        with self.assertRaises(ValueError):
            self.record.add_service_access(access)

    def test_reject_journey_for_different_agent(self):
        journey = HearingCareJourney(
            agent_id="PERSON-002",
            journey_id="JOURNEY-001",
        )

        with self.assertRaises(ValueError):
            self.record.add_journey(journey)

    def test_reject_wrong_record_type(self):
        with self.assertRaises(ValueError):
            self.record.add_funding_arrangement("not a funding record")

    def test_multiple_records_per_individual(self):
        self.record.add_funding_arrangement(
            FundingArrangement(agent_id="PERSON-001")
        )
        self.record.add_funding_arrangement(
            FundingArrangement(
                agent_id="PERSON-001",
                funding_pathway="private",
            )
        )

        self.record.add_service_access(
            ServiceAccess(
                agent_id="PERSON-001",
                service_type="audiology_assessment",
            )
        )
        self.record.add_service_access(
            ServiceAccess(
                agent_id="PERSON-001",
                service_type="rehabilitation",
            )
        )

        self.record.add_journey(
            HearingCareJourney(
                agent_id="PERSON-001",
                journey_id="JOURNEY-001",
            )
        )
        self.record.add_journey(
            HearingCareJourney(
                agent_id="PERSON-001",
                journey_id="JOURNEY-002",
            )
        )

        self.assertEqual(len(self.record.funding_arrangements), 2)
        self.assertEqual(len(self.record.service_access_records), 2)
        self.assertEqual(len(self.record.journeys), 2)

    def test_serialisation(self):
        self.record.add_funding_arrangement(
            FundingArrangement(
                agent_id="PERSON-001",
                private_contribution=300.0,
                out_of_pocket_cost=400.0,
            )
        )

        result = self.record.to_dict()

        self.assertIn("agent", result)
        self.assertIn("funding_arrangements", result)
        self.assertIn("service_access_records", result)
        self.assertIn("journeys", result)

        funding = result["funding_arrangements"][0]

        self.assertEqual(funding["private_contribution"], 300.0)
        self.assertEqual(funding["out_of_pocket_cost"], 400.0)

    def test_invalid_associated_record_is_detected(self):
        self.record.funding_arrangements.append(
            FundingArrangement(agent_id="PERSON-002")
        )

        with self.assertRaises(ValueError):
            self.record.validate()


if __name__ == "__main__":
    unittest.main()


class TestIndividualServiceDeliveryRecords(unittest.TestCase):

    def setUp(self):
        from src.hearing_support.individual_record import (
            IndividualHearingSupportRecord,
        )
        self.record = IndividualHearingSupportRecord(
            agent=create_agent()
        )

    def test_add_service_demand(self):
        from src.service_delivery.demand import ServiceDemand

        demand = ServiceDemand(
            demand_id="DEMAND-001",
            agent_id="PERSON-001",
            service_type="audiology_assessment",
            request_month=1,
            request_source="individual_request",
        )

        self.record.add_service_demand(demand)

        self.assertEqual(len(self.record.service_demands), 1)
        self.assertTrue(self.record.validate())

    def test_add_service_allocation(self):
        from src.service_delivery.allocation import ServiceAllocation

        allocation = ServiceAllocation(
            demand_id="DEMAND-001",
            agent_id="PERSON-001",
            service_id="SERVICE-001",
            service_type="audiology_assessment",
            age_group="working_age_adult",
            clinician_id="CLINICIAN-001",
            allocation_status="allocated",
            reason="matching_request_allocated",
        )

        self.record.add_service_allocation(allocation)

        self.assertEqual(len(self.record.service_allocations), 1)

    def test_add_service_delivery(self):
        from src.service_delivery.delivery import ServiceDelivery

        delivery = ServiceDelivery(
            demand_id="DEMAND-001",
            agent_id="PERSON-001",
            service_id="SERVICE-001",
            service_type="audiology_assessment",
            clinician_id="CLINICIAN-001",
            delivery_month=2,
            attendance_status="attended",
            delivery_status="delivered",
        )

        self.record.add_service_delivery(delivery)

        self.assertEqual(len(self.record.service_deliveries), 1)

    def test_rejects_service_demand_for_another_agent(self):
        from src.service_delivery.demand import ServiceDemand

        demand = ServiceDemand(
            demand_id="DEMAND-001",
            agent_id="PERSON-002",
            service_type="audiology_assessment",
            request_month=1,
            request_source="individual_request",
        )

        with self.assertRaises(ValueError):
            self.record.add_service_demand(demand)

    def test_serialises_service_delivery_records(self):
        from src.service_delivery.demand import ServiceDemand
        from src.service_delivery.allocation import ServiceAllocation
        from src.service_delivery.delivery import ServiceDelivery

        self.record.add_service_demand(ServiceDemand(
            demand_id="DEMAND-001",
            agent_id="PERSON-001",
            service_type="audiology_assessment",
            request_month=1,
            request_source="individual_request",
        ))

        self.record.add_service_allocation(ServiceAllocation(
            demand_id="DEMAND-001",
            agent_id="PERSON-001",
            service_id="SERVICE-001",
            service_type="audiology_assessment",
            age_group="working_age_adult",
            clinician_id="CLINICIAN-001",
            allocation_status="allocated",
            reason="matching_request_allocated",
        ))

        self.record.add_service_delivery(ServiceDelivery(
            demand_id="DEMAND-001",
            agent_id="PERSON-001",
            service_id="SERVICE-001",
            service_type="audiology_assessment",
            clinician_id="CLINICIAN-001",
            delivery_month=2,
            attendance_status="attended",
            delivery_status="delivered",
        ))

        result = self.record.to_dict()

        self.assertEqual(len(result["service_demands"]), 1)
        self.assertEqual(len(result["service_allocations"]), 1)
        self.assertEqual(len(result["service_deliveries"]), 1)
