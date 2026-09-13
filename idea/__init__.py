"""Wakala product spec: theme 1, trusted digital identity and cross-border verification."""

from __future__ import annotations

from core.agent import Case
from core.idea import ConsentPlan, IdeaSpec, LevelStyle, Scenario, UiSpec
from core.simulator import LineProfile

from .policy import WakalaPolicy

POLICY = WakalaPolicy()

# The consular district the citizen declares for a heavy act. Istanbul, where a
# large Arab diaspora actually lives.
DISTRICT = (41.0369, 28.9850)
DISTRICT_RADIUS_M = 25000

_M_PER_DEG_LAT = 111320.0

LINE_LIGHT = LineProfile(
    msisdn="+905320000601",
    label="Citizen in Istanbul changing an address on file",
    roaming=True,
    country_code=90,
    country_name="TUR",
    latitude=DISTRICT[0],
    longitude=DISTRICT[1],
    location_accuracy_m=3000,
    notes="A light act. One unit of proof, and one unit is the right amount.",
)

LINE_MEDIUM = LineProfile(
    msisdn="+905320000602",
    label="Citizen registering a company from abroad",
    roaming=True,
    country_code=90,
    country_name="TUR",
    latitude=DISTRICT[0],
    longitude=DISTRICT[1],
    location_accuracy_m=3000,
    notes="Medium tier: SIM and handset checks, both clean.",
)

LINE_HEAVY_CLEAN = LineProfile(
    msisdn="+905320000603",
    label="Citizen selling an inherited flat, everything consistent",
    roaming=True,
    country_code=90,
    country_name="TUR",
    latitude=DISTRICT[0],
    longitude=DISTRICT[1],
    location_accuracy_m=3000,
    notes="The full report: five elements, high assurance.",
)

LINE_HEAVY_SWAP = LineProfile(
    msisdn="+905320000604",
    label="Property sale, SIM changed two days ago",
    sim_swap_hours_ago=48,
    roaming=True,
    country_code=90,
    country_name="TUR",
    latitude=DISTRICT[0],
    longitude=DISTRICT[1],
    location_accuracy_m=3000,
    notes="The fraud that has moved real property in more than one country.",
)

LINE_MISMATCH = LineProfile(
    msisdn="+905320000605",
    label="Declared Turkey, line is on a German network",
    roaming=True,
    country_code=49,
    country_name="DEU",
    latitude=DISTRICT[0],
    longitude=DISTRICT[1],
    location_accuracy_m=3000,
    notes="A declaration to correct, not a fraud to prosecute.",
)

LINE_DEVICE = LineProfile(
    msisdn="+905320000606",
    label="Property-grade act from a handset bought yesterday",
    device_swap_hours_ago=22,
    roaming=True,
    country_code=90,
    country_name="TUR",
    latitude=DISTRICT[0],
    longitude=DISTRICT[1],
    location_accuracy_m=3000,
    notes="Same SIM, new phone. One extra human check, not a refusal.",
)

LINE_UNVERIFIED = LineProfile(
    msisdn="+905320000607",
    label="Network will not confirm the line belongs to this handset",
    number_verified=False,
    roaming=True,
    country_code=90,
    country_name="TUR",
    notes="No assurance level can be claimed, at any tier.",
)


def _act(subject: str, citizen: str, act_type: str, tier: str, value: str,
         label: str, declared: str = "TUR", with_district: bool = False) -> Case:
    return Case(
        subject=subject,
        kind="legal_act",
        label=label,
        facts={
            "citizen": citizen,
            "act_type": act_type,
            "act_tier": tier,
            "value": value,
            "declared_country": declared,
            "notary": "Notary Office 14, Amman",
        },
        latitude=DISTRICT[0] if with_district else None,
        longitude=DISTRICT[1] if with_district else None,
        radius_m=DISTRICT_RADIUS_M,
    )


SCENARIOS = [
    Scenario(
        id="light-address-change",
        title="Change of address on file",
        subtitle="A light act, from a citizen living in Istanbul",
        expect_level="sign",
        lines=[LINE_LIGHT],
        narrative="Proportionate proof, in seconds.",
        teaches=(
            "One network call, no SMS code, no consulate appointment. Spending more "
            "than an act is worth is its own kind of failure, and this is the tier "
            "where adoption actually starts because the law already allows remote "
            "handling."
        ),
        build_case=lambda: _act(
            LINE_LIGHT.msisdn, "Layla H.", "change of registered address", "light",
            "none", "Light act, address change",
        ),
    ),
    Scenario(
        id="medium-company-registration",
        title="Register a company from abroad",
        subtitle="Medium tier: SIM and handset checks added",
        expect_level="sign_with_record",
        lines=[LINE_MEDIUM],
        narrative="The tier most remote acts sit in.",
        teaches=(
            "The act earns the SIM and device change checks. Both come back clean, "
            "so the notary signs with an assurance report attached rather than "
            "sending the citizen to a queue."
        ),
        build_case=lambda: _act(
            LINE_MEDIUM.msisdn, "Omar S.", "company registration", "medium",
            "share capital 50,000", "Medium act, company registration",
        ),
    ),
    Scenario(
        id="heavy-property-sale",
        title="Sell an inherited flat",
        subtitle="Heavy tier: everything, including the declared country and district",
        expect_level="sign_with_record",
        lines=[LINE_HEAVY_CLEAN],
        narrative="Weeks of waiting replaced by a one-page report.",
        teaches=(
            "Five independent elements in one report: the line, no SIM change, no "
            "handset change, the declared country matching the visited network, and "
            "the line inside the consular district. A video call offers one element "
            "and a good copy of a face defeats it."
        ),
        build_case=lambda: _act(
            LINE_HEAVY_CLEAN.msisdn, "Nadia K.", "sale of inherited property", "heavy",
            "180,000", "Heavy act, property sale", with_district=True,
        ),
    ),
    Scenario(
        id="heavy-sim-two-days",
        title="Property sale, SIM changed two days ago",
        subtitle="The takeover that has already moved real property",
        expect_level="refuse",
        lines=[LINE_HEAVY_SWAP],
        narrative="The fraud this product has to stop to be worth deploying.",
        teaches=(
            "A stolen number plus a copy of an identity card has been enough to "
            "transfer property. The agent buys the SIM change timestamp, finds 48 "
            "hours, and refuses - and the report says exactly which signal decided "
            "it, for the dispute that follows."
        ),
        build_case=lambda: _act(
            LINE_HEAVY_SWAP.msisdn, "Account of Y. Mansour", "sale of apartment", "heavy",
            "240,000", "Heavy act, fresh SIM change", with_district=True,
        ),
    ),
    Scenario(
        id="country-mismatch",
        title="Declared Turkey, line is in Germany",
        subtitle="A consistency check on the declaration",
        expect_level="step_up",
        lines=[LINE_MISMATCH],
        narrative="How not to criminalise moving house.",
        teaches=(
            "Every citizen here is abroad, so roaming can never be the red flag. "
            "It is only useful as a check against what they declared, and the "
            "outcome is a correction to the paperwork rather than an accusation."
        ),
        build_case=lambda: _act(
            LINE_MISMATCH.msisdn, "Hassan D.", "general power of attorney", "heavy",
            "unlimited", "Heavy act, country mismatch", with_district=True,
        ),
    ),
    Scenario(
        id="heavy-new-handset",
        title="Property-grade act from a new phone",
        subtitle="Handset changed yesterday, SIM untouched",
        expect_level="step_up",
        lines=[LINE_DEVICE],
        narrative="Weighing a signal instead of blocking on it.",
        teaches=(
            "The SIM is unchanged, so this is almost certainly a person who bought "
            "a phone. For a property-grade act that still earns one more human "
            "element - and notably not a refusal."
        ),
        build_case=lambda: _act(
            LINE_DEVICE.msisdn, "Rania T.", "sale of land parcel", "heavy",
            "95,000", "Heavy act, new handset", with_district=True,
        ),
    ),
    Scenario(
        id="unverified-line",
        title="The network will not confirm the line",
        subtitle="A medium act from a handset that does not hold this number",
        expect_level="refuse",
        lines=[LINE_UNVERIFIED],
        narrative="One unit, and no assurance level can be claimed.",
        teaches=(
            "The floor under every tier. Without number verification there is no "
            "report to write, and the agent stops rather than gathering evidence "
            "about a line it cannot attribute."
        ),
        build_case=lambda: _act(
            LINE_UNVERIFIED.msisdn, "Unknown requester", "limited power of attorney",
            "medium", "not stated", "Medium act, unverified line",
        ),
    ),
]

SPEC = IdeaSpec(
    slug="wakala",
    name="Wakala",
    tagline="Network proof that lets a citizen abroad sign a legal act",
    theme_number=1,
    theme_name="Trusted Digital Identity & Cross-Border Verification",
    submission_title="Wakala - network proof that lets a citizen abroad sign a legal act",
    submission_description=(
        "Millions of citizens live outside their home country and must appear at a "
        "consulate to sign a legal act, because an SMS code has never been strong "
        "enough proof. Wakala is an AI agent that matches the network proof to the "
        "stakes of the act and hands a notary a one-page assurance report. The "
        "notary still signs."
    ),
    policy=POLICY,
    scenarios=SCENARIOS,
    lines=[
        LINE_LIGHT,
        LINE_MEDIUM,
        LINE_HEAVY_CLEAN,
        LINE_HEAVY_SWAP,
        LINE_MISMATCH,
        LINE_DEVICE,
        LINE_UNVERIFIED,
    ],
    consent=ConsentPlan(
        moment="at the moment of use, because the citizen is the one asking for the act",
        scopes=[
            "identity:verify",
            "fraud:sim-swap",
            "fraud:device-swap",
            "device:status",
            "location:verify",
        ],
        who_consents="the citizen, who owns the line and is requesting the act in their own name",
        duration_note="The grant covers this single act and expires with it.",
        revocation=(
            "A citizen who declines simply uses the existing consulate appointment "
            "route. Nothing is lost except the weeks of waiting."
        ),
    ),
    ui=UiSpec(
        accent="#6b5bc4",
        accent_soft="#eceaf9",
        hero_kicker=(
            "A property sale needs stronger proof than an address change. Wakala "
            "buys proof in proportion to the act and hands the notary a report, not "
            "a decision."
        ),
        subject_label="Citizen line (MSISDN)",
        case_label="Legal act",
        run_all_label="Run all seven acts",
        ad_hoc_placeholder="+905320000604",
        ad_hoc_help=(
            "An ad-hoc check runs the medium tier. Unregistered numbers get a "
            "stable derived profile."
        ),
        levels=[
            LevelStyle("sign", "Sign - proportionate proof", "calm",
                       "A light act with the network confirmation it needs."),
            LevelStyle("sign_with_record", "Sign and attach the report", "calm",
                       "Nothing in the network contradicts the citizen."),
            LevelStyle("step_up", "Step up - one more human element", "warn",
                       "Something belongs in front of a person first."),
            LevelStyle("refuse", "Refuse - in person only", "alarm",
                       "The network evidence says do not proceed remotely."),
        ],
    ),
    honest_limits=[
        "Wakala never decides whether an act is lawful. It produces evidence; a "
        "notary signs. Any product that blurs that line should not be deployed.",
        "It proves which line and which handset, not which human. A family member "
        "holding the citizen's phone with their PIN passes every check here.",
        "Adoption is the hard part, not the technology. Light acts where remote "
        "handling is already lawful are the only realistic entry point; property "
        "registries move in years.",
        "Assurance levels here are ours, not a legal standard. Mapping them onto "
        "eIDAS or a national framework is work we have not done and would not fake.",
    ],
    buyers=[
        "Notaries, land registries, banks and law firms paying per act",
        "Consulates and e-government platforms, who want shorter queues",
        "Mobile operators, who share the API income",
    ],
    repo_name="wakala-nac-agent",
    demo_notes=(
        "Run the light act first to show one unit of spend, then the property sale "
        "with the fresh SIM change. The contrast between the two is the pitch."
    ),
)
