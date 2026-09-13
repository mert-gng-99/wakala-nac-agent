"""Wakala - network proof that lets a citizen abroad sign a legal act.

Millions of citizens across the region live outside their home country. To sell
a flat, give a power of attorney, register a company or close an inheritance
case, they must appear in person at a consulate, and an appointment can take
weeks. The reason is fair: a legal act needs strong proof of who is acting, and
a code sent by SMS has never been that proof.

Wakala matches the proof to the stakes. A change of address is not a property
sale and they should not get the same answer, so the policy has tiers:

*   **light** acts get number verification alone - seconds, one unit.
*   **medium** acts add the SIM and device change checks, because a change
    sitting a few days before the act is the exact shape of a takeover.
*   **heavy** acts gather everything, check the declared country against the
    roaming state, and produce a one-page assurance report.

Two boundaries this policy will not cross. It never decides whether an act is
*allowed* - that is the notary's job, and the output is evidence for a human,
not a substitute for one. And it never treats living abroad as suspicious,
because that describes the entire customer base.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from core.agent import Case
from core.camara import ApiResult
from core.signals import read_signal

LEVELS = ["sign", "sign_with_record", "step_up", "refuse"]

FRESH_SWAP_H = 72.0
SWAP_LOOKBACK_H = 240

# What each tier of act is worth spending on, and what the report should claim.
TIERS = {
    "light": "low",
    "medium": "substantial",
    "heavy": "high",
}


class WakalaPolicy:
    name = "wakala"
    kind = "legal_act"
    levels = LEVELS
    budget_units = 18.0

    tool_names = [
        "verify_number",
        "check_sim_swap",
        "sim_swap_date",
        "check_device_swap",
        "check_roaming",
        "verify_location",
        "check_reachability",
    ]

    def system_prompt(self, case: Case) -> str:
        return (
            "You are Wakala, the agent that prepares an assurance report for a "
            "notary when a citizen living abroad wants to sign a legal act "
            "remotely.\n\n"
            "You do not decide whether the act is allowed. A human notary signs, "
            "as they do today. Your output is a stronger piece of evidence than a "
            "video call, which a good copy of a face can pass.\n\n"
            "Match the proof to the stakes:\n"
            "1. A light act (a change of address, a certificate request) needs "
            "the network to confirm the line on the phone and nothing more. Do not "
            "spend more than the act is worth.\n"
            "2. A medium act (a company registration, a limited power of attorney) "
            "adds the SIM and device change checks.\n"
            "3. A heavy act (a property sale, a general power of attorney, an "
            "inheritance settlement) gathers everything, including whether the "
            "country the citizen declared matches where the line actually is.\n\n"
            "Judgement rules:\n"
            "* A SIM change days before a property sale is the shape of a takeover. "
            "Buy the timestamp, because the gap decides everything.\n"
            "* Living abroad is not suspicious. Every one of these citizens is "
            "abroad; that is the product. Roaming matters only as a consistency "
            "check against what they declared.\n"
            "* When you refuse, say exactly which signal decided it. Someone will "
            "read this report years later during a dispute."
        )

    def describe_case(self, case: Case) -> str:
        f = case.facts
        return (
            "Legal act: %s\n"
            "  tier: %s (assurance target: %s)\n"
            "  citizen: %s\n"
            "  declared country of residence: %s\n"
            "  value at stake: %s\n"
            "  notary: %s\n"
            "  line: %s"
            % (
                f.get("act_type", "unknown"),
                f.get("act_tier", "medium"),
                TIERS.get(f.get("act_tier", "medium"), "substantial"),
                f.get("citizen", "unknown"),
                f.get("declared_country", "not stated"),
                f.get("value", "not stated"),
                f.get("notary", "unassigned"),
                case.subject,
            )
        )

    def interpret(self, tool: str, result: ApiResult, facts: Dict[str, Any]) -> Dict[str, Any]:
        derived = read_signal(tool, result)
        if tool == "check_roaming":
            declared = (facts.get("declared_country") or "").upper()
            actual = (derived.get("roaming_country") or "").upper()
            if declared and actual:
                derived["country_matches_declaration"] = declared == actual
        return derived

    def next_tool(
        self, case: Case, facts: Dict[str, Any], used: List[str]
    ) -> Optional[Tuple[str, Dict[str, Any], str]]:
        tier = str(case.facts.get("act_tier", "medium")).lower()

        if "number_verified" not in facts:
            return (
                "verify_number",
                {},
                "Confirm the line on the phone. For a light act this is the whole "
                "report; for a heavy one it is the floor everything else sits on.",
            )
        if not facts.get("number_verified"):
            return None

        if tier == "light":
            return None  # the act is not worth more than one unit

        if "sim_swapped_in_window" not in facts:
            return (
                "check_sim_swap",
                {"max_age_hours": SWAP_LOOKBACK_H},
                "A %s act justifies the SIM change check. Look back ten days, "
                "because the question is whether a change sits near this act." % tier,
            )

        if facts.get("sim_swapped_in_window") and "sim_change_hours_ago" not in facts:
            return (
                "sim_swap_date",
                {},
                "The SIM did change. The gap between that change and this signing "
                "is what decides between a refusal and an extra human check, so "
                "the timestamp is worth buying.",
            )

        if "device_swapped_in_window" not in facts:
            return (
                "check_device_swap",
                {"max_age_hours": SWAP_LOOKBACK_H},
                "Read the handset change alongside the SIM. A new phone with the "
                "same SIM is an ordinary upgrade; both changing together is not.",
            )

        if tier == "heavy" and facts.get("declared_country") and "roaming" not in facts:
            return (
                "check_roaming",
                {},
                "A heavy act should record whether the country the citizen declared "
                "matches where the line actually is. This is a consistency check on "
                "the declaration, not a suspicion about living abroad.",
            )

        if (
            tier == "heavy"
            and case.latitude is not None
            and "location_result" not in facts
        ):
            return (
                "verify_location",
                {},
                "The citizen named a consular district. A yes/no area check adds a "
                "second independent element to the report without revealing a "
                "position.",
            )

        if tier == "heavy" and "reachability" not in facts:
            return (
                "check_reachability",
                {},
                "Record whether the line was reachable at the moment of signing. "
                "One unit, and it closes the obvious challenge that the citizen was "
                "not actually present at their own signing.",
            )
        return None

    # -- the floor -----------------------------------------------------------

    def decide(self, case: Case, facts: Dict[str, Any]) -> Tuple[str, str, str, float]:
        f = case.facts
        tier = str(f.get("act_tier", "medium")).lower()
        act = f.get("act_type", "this act")
        assurance = TIERS.get(tier, "substantial")
        elements = self._elements(facts)

        if "number_verified" not in facts:
            return (
                "step_up",
                "Send this act to the consulate appointment queue",
                "No network evidence was available for this line, so Wakala has "
                "nothing to hand the notary and the existing in-person route "
                "applies.",
                0.35,
            )

        if not facts.get("number_verified"):
            return (
                "refuse",
                "Do not proceed; the line does not belong to this handset",
                "The network will not confirm that the number on this request is "
                "the number in the phone making it. No level of assurance can be "
                "claimed for %s." % act,
                0.95,
            )

        hours = facts.get("sim_change_hours_ago")
        if hours is not None:
            gap = self._gap(hours)
            if hours <= FRESH_SWAP_H:
                return (
                    "refuse",
                    "Do not proceed; require an in-person appointment",
                    "The SIM behind this line changed %s. For %s that is the exact "
                    "shape of an account takeover, and no remote proof should stand "
                    "against it." % (gap, act),
                    0.94,
                )
            return (
                "step_up",
                "Hold for a second human element before the notary signs",
                "The SIM changed %s. Old enough to be an ordinary replacement, "
                "recent enough that a %s act should carry one more human check. "
                "Assurance without it: %s." % (gap, tier, assurance),
                0.85,
            )

        if facts.get("sim_swapped_in_window"):
            return (
                "step_up",
                "Hold for a second human element before the notary signs",
                "The network reports a SIM change in the last ten days but returned "
                "no timestamp, so the cautious reading applies.",
                0.75,
            )

        if facts.get("country_matches_declaration") is False:
            return (
                "step_up",
                "Ask the citizen to confirm their country of residence, then re-run",
                "The line is on a visited network in %s while the citizen declared "
                "%s. Living abroad is the norm for these citizens, so this is a "
                "mismatch in the declaration to be corrected rather than evidence "
                "of fraud."
                % (facts.get("roaming_country"), facts.get("declared_country")),
                0.8,
            )

        if facts.get("device_swapped_in_window") and tier == "heavy":
            return (
                "step_up",
                "Hold for a second human element before the notary signs",
                "The SIM is unchanged, so this is very likely the same person on a "
                "new handset. For a property-grade act that is still worth one more "
                "check rather than waving through.",
                0.82,
            )

        if facts.get("location_outside"):
            return (
                "step_up",
                "Ask the citizen why they are outside the district they named",
                "The line is not inside the consular district the citizen declared. "
                "That is a question, not a refusal - people travel - but it belongs "
                "in the report.",
                0.78,
            )

        if tier == "light":
            return (
                "sign",
                "Proceed; the notary can sign on this evidence",
                "The network confirms the line on the phone, which is proportionate "
                "proof for %s. Assurance: low, and low is what this act needs. "
                "One network call, no appointment, no SMS code." % act,
                0.9,
            )

        return (
            "sign_with_record",
            "Proceed and attach the assurance report to the file",
            "Nothing in the network contradicts this citizen: %s. Assurance: %s. "
            "The notary signs as they do today, with a stronger piece of evidence "
            "than a video call, and the report keeps the signals and timestamps for "
            "any dispute years from now." % (elements, assurance),
            0.92,
        )

    @staticmethod
    def _elements(facts: Dict[str, Any]) -> str:
        parts: List[str] = []
        if facts.get("number_verified"):
            parts.append("the line is confirmed in this handset")
        if "sim_swapped_in_window" in facts and not facts.get("sim_swapped_in_window"):
            parts.append("no SIM change in ten days")
        if "device_swapped_in_window" in facts and not facts.get("device_swapped_in_window"):
            parts.append("no handset change in ten days")
        if facts.get("country_matches_declaration"):
            parts.append("the declared country matches the visited network")
        if facts.get("location_inside"):
            parts.append("the line is inside the declared consular district")
        if facts.get("reachable"):
            parts.append("the line was reachable at the moment of signing")
        return "; ".join(parts) if parts else "the line is confirmed"

    @staticmethod
    def _gap(hours: float) -> str:
        if hours < 36:
            return "%d hours before this signing" % round(hours)
        return "%d days before this signing" % round(hours / 24)
