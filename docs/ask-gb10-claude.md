# Request to the Claude instance running on the Dell GB10 box

> Paste this verbatim into the Claude session on the NVIDIA/Dell machine.
> Goal: a written integration report so the two of us don't build the same thing twice.
> We (the dashboard/backend side) already have a canonical `LeadAnalysis` JSON object and a
> FastAPI orchestrator. We want to HAND OFF to your existing Hermes + Discord instead of
> duplicating them.

---

Hi — I'm Claude on the partner machine building the **observability dashboard + lead-analysis
backend** for "Local Voice Lead Closer." You own the live **Hermes** service and **Discord**
integration in `.hermes/` on this box. Before we wire anything together, please give me a
concise integration report. Do **not** change any code — just inspect `.hermes/` and report.

Please answer all of the following, with concrete values (paths, ports, exact field names):

### A. Hermes — what it is and how to call it
1. What is Hermes, exactly — a long-running HTTP service, a CLI, a library, or a bot process?
2. **How is it started**, and on what **host:port**? (exact command + any required env vars)
3. List its **public endpoints / entry points** I can call — for each: method, path, purpose,
   and a sample request + response body (real JSON, not described).
4. Does Hermes already do **lead scoring / qualification / LLM reasoning**? If yes, describe
   the input it expects and the output object it returns (full field list). This is the most
   important question — it tells us who owns scoring.
5. Does it talk to the **GB10 Nemotron** model itself? If so: what endpoint URL, what served
   model id, what serving engine (vLLM / NIM / Ollama / TGI), and is an API key required?

### B. Discord — how alerts are sent
6. How does Hermes post to Discord — bot token + channel, or webhook URL? Which channel(s)?
7. What **payload/shape** does the Discord-send function take as input? (so I can format to it)
8. Is there a single function/endpoint I can call with a lead summary to trigger a staff alert,
   or does Discord posting only happen inside a larger Hermes flow?

### C. The data contract (critical for non-duplication)
9. Does Hermes have its **own schema / data model** for a lead, call, or conversation? Paste it.
   I will map our `LeadAnalysis` object to it rather than inventing a parallel one.
10. Where does a conversation/transcript **enter** the system (voice? PersonaPlex? a webhook?),
    and where does the final result **exit** (Discord? a DB? an API response?)? Draw the flow.

### D. The integration seam — where do WE plug in?
11. Given that we produce a complete `LeadAnalysis` (transcript + extracted slots + hot/warm/cold
    score + deal value + next-best-action), what is the **cleanest single hand-off point**:
    - Option A: we POST our `LeadAnalysis` to a Hermes endpoint and Hermes handles Discord + tasks.
    - Option B: Hermes calls *us* to score, then continues its own flow.
    - Option C: we both call Nemotron independently and only share Discord formatting.
    Recommend one, and tell me the exact endpoint/function signature to use.
12. Anything already built that we should **stop building** (e.g. you already do Discord alerts,
    so our ChatAdapter should just call yours)? List concrete overlaps.

### E. Run/repro details
13. Exact steps to run Hermes locally so I can integration-test against it.
14. Any env vars, secrets, or config files I must set (names only, not the secret values).

Please return this as a single markdown report. Keep it factual and paste real code/JSON where
asked — I'll use it to write the adapter that hands off to you.
