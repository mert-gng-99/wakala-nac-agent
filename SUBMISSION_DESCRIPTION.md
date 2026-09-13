## Wakala - Network proof that lets a citizen abroad sign a legal act

Millions of citizens live outside their home country and must appear at a consulate to sign a legal act, because an SMS code has never been strong enough proof. Wakala is an AI agent that matches the network proof to the stakes of the act and hands a notary a one-page assurance report. The notary still signs.

### The problem

A property sale needs stronger proof than an address change. Wakala buys proof in proportion to the act and hands the notary a report, not a decision.

### What the prototype actually does

Wakala is a working web application with an operator console, a REST API, and
a live WebSocket feed of the agent's reasoning. Open it, click a scenario, and
you watch the agent choose CAMARA calls one at a time and then justify its
decision with the network answers behind it.

It runs in three modes. `simulator` needs no credentials and answers every
CAMARA call in the real CAMARA response shape, which is how the organisers
recommend demonstrating and how the test suite stays deterministic. `live`
calls the Nokia Network-as-Code gateway with your own key. `hybrid` uses live
where credentials allow and falls back per call. Every answer is tagged with
its source in the UI, so a simulated result can never pass itself off as a real
network answer.

### The AI agent layer

The agent is a planner over a CAMARA tool registry, not a script with an LLM
bolted on. Each tool in the registry carries its price, its typical latency and
how much it reveals about a person, and the planner is judged on choosing well:

1. The planner proposes one call, with a stated reason.
2. The runtime, never the model, checks it against the tool allowlist, the
   consent ledger and the remaining budget.
3. The CAMARA answer is recorded with full provenance and turned into a fact.
4. Repeat until the planner submits a decision, or the budget runs out.

The planner is Google AI Studio (Gemini) through **Pydantic AI**'s typed,
structured-output path. It is enabled by setting `AGENT_PROVIDER=gemini`
alongside a `GEMINI_API_KEY`. A model turn may only propose a next CAMARA check
or a decision; it cannot execute a network call itself. The runtime remains the
only executor of consent, the tool allowlist, argument filtering and budget.

Gemini is opt-in on both counts deliberately: a key sitting in the environment
should not be enough to start spending on a model. Otherwise a deterministic
policy planner implementing the same escalation ladder takes over, so the
prototype is demonstrable offline and CI has something stable to assert. If a
configured model cannot complete a turn, the finished case is explicitly
labelled `policy-fallback` with a bounded error reason. It is never presented
as a successful Gemini-planned decision.

**The guardrail is the part worth looking at.** The policy computes a floor for
every case from the facts alone. If the model proposes something less cautious
than the floor, the floor wins and the disagreement is written into the
decision record. A language model should choose which checks to buy; it should
not be able to clear a case the evidence says to escalate. There is a test for
exactly this.

### Results from the shipped scenarios

7 scenarios ship with the prototype, and all 7 reach the
outcome they claim. The demo and the test suite assert the same thing, so a
scenario drifting from the pitch is a build failure.

- Outcome levels reached: `sign`, `sign_with_record`, `step_up`, `refuse`
- CAMARA calls per case: 1 to 7 (average 4.3)
- Total spend across all scenarios: 56 units, against 98 if
  every available check were called on every case, a saving of 42.9%

| Scenario | Outcome | CAMARA calls | Spend |
| --- | --- | --- | --- |
| Change of address on file | `sign` | 1 | 1 |
| Register a company from abroad | `sign_with_record` | 3 | 7 |
| Sell an inherited flat | `sign_with_record` | 6 | 11 |
| Property sale, SIM changed two days ago | `refuse` | 7 | 14 |
| Declared Turkey, line is in Germany | `step_up` | 6 | 11 |
| Property-grade act from a new phone | `step_up` | 6 | 11 |
| The network will not confirm the line | `refuse` | 1 | 1 |

The cheapest case, *Change of address on file*, resolves in 1 call(s). The
most expensive, *Property sale, SIM changed two days ago*, earns 7. That gap is the product:
an agent that calls everything on everyone is safe, useless and unaffordable.

### CAMARA APIs on Nokia Network as Code

`number-verification`, `sim-swap`, `device-swap`, `device-status`, `location-verification`

| CAMARA API | What the agent asks it | Cost | Reveals |
| --- | --- | --- | --- |
| `number-verification` | Confirm the line on the phone | 1 | boolean |
| `sim-swap` | Has the SIM changed recently | 3 | boolean |
| `sim-swap` | When did the SIM last change | 3 | enum |
| `device-swap` | Has the handset changed recently | 3 | boolean |
| `device-status` | Is the line roaming, and where | 1 | enum |
| `location-verification` | Is the line inside this area | 2 | boolean |
| `device-status` | Can the line be reached | 1 | enum |

### Consent

CAMARA identity, location and geofencing APIs are only lawful with the consent
of the line owner, so consent is enforced in the transport path rather than
described in a policy document. An ungranted call raises before a request is
built.

Consent is taken at the moment of use, because the citizen is the one asking
for the act, from the citizen, who owns the line and is requesting the act in
their own name. The grant covers this single act and expires with it. A
citizen who declines simply uses the existing consulate appointment route.
Nothing is lost except the weeks of waiting.

You can prove this in the running app: press **Withdraw consent**, run the same
case again, and watch the agent get refused at the transport layer with zero
CAMARA calls made.

### What this does not do

- Wakala never decides whether an act is lawful. It produces evidence; a notary signs. Any product that blurs that line should not be deployed.
- It proves which line and which handset, not which human. A family member holding the citizen's phone with their PIN passes every check here.
- Adoption is the hard part, not the technology. Light acts where remote handling is already lawful are the only realistic entry point; property registries move in years.
- Assurance levels here are ours, not a legal standard. Mapping them onto eIDAS or a national framework is work we have not done and would not fake.

### Who pays

- Notaries, land registries, banks and law firms paying per act
- Consulates and e-government platforms, who want shorter queues
- Mobile operators, who share the API income

### Verification

Run `pytest -q` in the repository. The suite covers the CAMARA transport and
its provenance, the consent gate, budget enforcement, the tool allowlist, the
guardrail floor overruling an over-confident model, the LLM planner loop
against a scripted model, the full HTTP surface, and every shipped scenario.
