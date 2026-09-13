# Wakala

> Network proof that lets a citizen abroad sign a legal act

**MENA Ignite Hackathon - GSMA Open Gateway - Theme 1: Trusted Digital Identity & Cross-Border Verification**

A property sale needs stronger proof than an address change. Wakala buys proof in proportion to the act and hands the notary a report, not a decision.

Millions of citizens live outside their home country and must appear at a consulate to sign a legal act, because an SMS code has never been strong enough proof. Wakala is an AI agent that matches the network proof to the stakes of the act and hands a notary a one-page assurance report. The notary still signs.

---

## Quick start

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Open http://localhost:8000. You need no credentials, because the app starts in
`simulator` mode and every answer is tagged with its source.

Full instructions, including the Gemini planner and the live Nokia gateway, are
in **INSTRUCTIONS.md**. The design is in **ARCHITECTURE.md**.

## What it is

An AI agent that decides *which* CAMARA network check is worth making for a
given case, spends against a budget, refuses calls it has no consent for, and
explains every decision with the network answers behind it.

- **7 scenarios** ship with it, all reaching the outcome they claim
- **5 CAMARA APIs** on the Nokia Network-as-Code platform
- **42.9% cheaper** than calling every available check on every case
- **1 to 7 calls** per case, depending on what the case deserves

## Scenarios

- Change of address on file. A light act, from a citizen living in Istanbul (expects `sign`)
- Register a company from abroad. Medium tier: SIM and handset checks added (expects `sign_with_record`)
- Sell an inherited flat. Heavy tier: everything, including the declared country and district (expects `sign_with_record`)
- Property sale, SIM changed two days ago. The takeover that has already moved real property (expects `refuse`)
- Declared Turkey, line is in Germany. A consistency check on the declaration (expects `step_up`)
- Property-grade act from a new phone. Handset changed yesterday, SIM untouched (expects `step_up`)
- The network will not confirm the line. A medium act from a handset that does not hold this number (expects `refuse`)

## CAMARA APIs used

| CAMARA API | What the agent asks it | Cost | Reveals |
| --- | --- | --- | --- |
| `number-verification` | Confirm the line on the phone | 1 | boolean |
| `sim-swap` | Has the SIM changed recently | 3 | boolean |
| `sim-swap` | When did the SIM last change | 3 | enum |
| `device-swap` | Has the handset changed recently | 3 | boolean |
| `device-status` | Is the line roaming, and where | 1 | enum |
| `location-verification` | Is the line inside this area | 2 | boolean |
| `device-status` | Can the line be reached | 1 | enum |

## The agent

```
planner proposes one call  ->  runtime checks allowlist, consent, budget
      ^                                        |
      |                                        v
  answer becomes a fact   <-   CAMARA call recorded with provenance
      |
      +--> planner submits a decision  ->  policy floor applied  ->  ledger
```

The planner is Google AI Studio (Gemini) through Pydantic AI when
`AGENT_PROVIDER=gemini` and a `GEMINI_API_KEY` are both set, and a deterministic
policy ladder otherwise. Pydantic AI returns a typed proposal only; the runtime
still holds the budget, allowlist and consent gate, and the policy holds a floor
the model cannot talk its way under.

## Tests

```bash
pytest -q
```

## What this does not do

- Wakala never decides whether an act is lawful. It produces evidence; a notary signs. Any product that blurs that line should not be deployed.
- It proves which line and which handset, not which human. A family member holding the citizen's phone with their PIN passes every check here.
- Adoption is the hard part, not the technology. Light acts where remote handling is already lawful are the only realistic entry point; property registries move in years.
- Assurance levels here are ours, not a legal standard. Mapping them onto eIDAS or a national framework is work we have not done and would not fake.

## Layout

```
main.py            uvicorn entry point
app_spec.py        re-exports this product's spec
core/              shared platform: CAMARA client, agent, consent, ledger, UI
  camara.py        the eleven CAMARA API families, live + simulator
  simulator.py     deterministic network simulator
  agent.py         the agent loop, budget, guardrail
  tools.py         CAMARA tool registry with cost and reveal metadata
  consent.py       consent ledger enforced in the transport path
  ledger.py        SQLite decision ledger
  signals.py       CAMARA answers -> named facts
  server.py        FastAPI app
  webui.py         the operator console
idea/              this product: policy, scenarios, demo lines, copy
tests/             pytest suite
```

## Licence

MIT. See LICENSE.
