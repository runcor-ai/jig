# Design note: human experts as a kind of agent

**Status: design only. Nothing here is built or tested.** Written on 14 November 2026 alongside the pilot study
*Abstraction for AI Work*.

## The idea in one line

A pool of human experts becomes one more kind of agent in Jig, so that any step can be done by people
(`agent="experts"`) with the same contract, checks and records as a step done by a model.

```python
v = verify(spec, agent="experts")                                     # the same step, done by people
r = review(spec, criteria=["clinically safe"], agent="experts", reviewers=3)
```

## Why

Some quality cannot be captured by a test: whether a memo is wise, a design usable, an answer fair or safe. Having
experts check AI output in bulk does not scale. The layers Jig and The Reality Engine already provide mean most of it
is unnecessary:

| Layer | Covers | Cost per output |
|---|---|---|
| Code checks (Jig validators) | Fabricated files, functions, tests and sources; the computed verdict | Free |
| Hidden tests | Anything a test can express | Free once written |
| Measurement on unseen cases (The Reality Engine) | How often a way of working is within tolerance, and why it fails | A few hundred cases per way of working, then spot checks |
| **Experts** | Judgement no test can capture; calibrating AI judges; auditing samples | High: used only where routed |

Experts move from checking every output to setting the exam and checking where measured trust runs out.

## How it fits Jig

Jig already separates *what a step is* (the command: prompt, tool policy, answer format, checks) from *who does it*
(the agent: `opus` through Claude Code, `luna` through Codex). An expert pool is a third kind of agent, configured in
`jig.yaml` like the others:

```yaml
agents:
  experts:
    adapter: experts              # a new adapter
    pool: clinical-reviewers      # who may take the task
    reviewers: 3                  # judgements collected per item
    aggregate: majority           # majority | mean | adjudicate
    timeout_hours: 48
    gold_rate: 0.1                # share of tasks with a known answer, to check reviewers
```

### The task a reviewer sees

The adapter renders the step's prompt and its answer format (the command's JSON Schema) as a form: one field per
required output field, with the rubric, the data to judge (fenced and marked as material, never as instructions),
and the allowed values. A reviewer's answer is validated against the same schema as a model's answer, and fails the
same checks if it cites a file that does not exist.

### Several reviewers, and agreement

- Each item goes to `reviewers` people independently.
- Answers are combined by the `aggregate` rule. `adjudicate` sends disagreements to a senior reviewer.
- Agreement is measured per item and per rubric field (percent agreement; Krippendorff's alpha across items).
  Low agreement is reported as a finding: the rubric is unclear or the item is genuinely hard. It is never hidden
  by averaging.

### Checking the reviewers

A share of tasks (`gold_rate`) have known answers. A reviewer's accuracy on them is recorded and can exclude them
from the pool. This is the same idea as the Reality Engine's sealed items, applied to people.

### Time

People take hours or days. A Jig step already records its state and supports `--resume`, so an expert step is a step
that waits: the script resumes when the judgements are in, or the step fails with `E_TIMEOUT` after `timeout_hours`.

## Routing: what goes to experts

Volume is not the goal. A script decides with plain logic what needs a person:

```python
v = verify(spec)                                       # an AI check first, as today
t = test(spec, run=TEST)
unsure = v.output and v.output.verdict.result == "pass" and t.status != "completed"
if unsure or high_stakes or sample(0.03):              # checks disagree, high stakes, or a 3% random sample
    e = verify(spec, agent="experts")
```

(`sample()` would be a small new builtin: true with the given probability, seeded and recorded so a run can be
replayed.)

| Send to experts when | Because |
|---|---|
| The cheap checks disagree, or the AI verifier is unsure | The automatic layers conflict |
| The work is high-stakes (medical, legal, financial) | The cost of an error justifies the cost of a person |
| A small random sample, e.g. 2-5% | Keeps the automatic layers honest over time |
| A new way of working, before it is trusted | Builds the evidence for how much sampling it needs |

## How it ties to The Reality Engine

- **Experts as the scorer.** Where hidden tests cannot reach, a Reality Engine pack scores a run with expert
  judgements collected through this adapter, with agreement reported alongside the score.
- **Calibrating AI judges.** A sample scored by both experts and an AI judge shows how far the judge can be trusted;
  the engine's first case study checked its AI judge only against another model.
- **Trust decides the sampling rate.** The trust report says how often a way of working is within tolerance on unseen
  cases. That number sets how much expert sampling it needs: light at 99%, heavy (or a better design) at 70%.

## Open questions

- **Privacy and confidentiality.** Expert pools see the material they judge. Steps must support redaction and pools
  with the right agreements; some material should never leave the organisation.
- **Platforms.** A first version could use an internal queue (tasks as files or a small web form). External expert
  platforms would each need an adapter; none is chosen here.
- **Pay and fairness.** Reviewer pay, time limits and workload need to be set with the people doing the work, not just
  for throughput.
- **Bias.** Experts disagree for good reasons. Aggregation rules should keep disagreement visible rather than force
  a single answer.

## What would be built, in order

1. The `experts` adapter with an internal queue and a simple review form; `reviewers`, `aggregate`, `timeout_hours`.
2. Agreement measurement and gold items.
3. The `sample()` builtin, seeded and recorded.
4. A Reality Engine pack scored by experts, with an AI judge calibrated against them.
