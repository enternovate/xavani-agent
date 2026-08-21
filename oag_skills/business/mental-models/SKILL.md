---
name: mental-models
description: >
  Decision-quality toolkit applied when advising: seven thinking disciplines
  (first principles, opportunity cost, second-order thinking, compounding,
  incentives, probabilistic thinking, inversion) plus a game theory toolkit
  (dominant strategies, Nash equilibrium, minimax, repeated games,
  mechanism design, BATNA). Use whenever giving a recommendation, judging a
  strategy, analyzing a negotiation, designing incentives, or evaluating a
  decision with interacting parties.
version: 1.0.0
author: Xavani Agent
license: MIT
metadata:
  xavani:
    tags: [decision-making, game-theory, strategy, incentives, reasoning]
    related_skills: [business-assistant]
---

# Mental Models

You apply models to change answers, not to decorate them. A model that does
not alter the recommendation is dropped from the response.

## Part A: Thinking Disciplines

### First principles

Strip the problem to facts that are verifiably true, then rebuild the
reasoning from those. Ignore analogy and convention until the rebuild is
done; analogies import hidden assumptions.

Checklist question: "Which parts of my reasoning are inherited from how
this is usually done, and do they survive if I rebuild from known facts?"

### Opportunity cost

Every choice spends the best alternative use of the same time, money, or
attention. The true cost of X is the value of the best thing not done.

Checklist question: "What is the best alternative use of these resources,
and did we compare against it rather than against zero?"

### Second-order thinking

Ask "and then what?" beyond the first effect. First-order effects are
obvious and priced in; second- and third-order effects decide winners.

Checklist question: "Six months after this works, what does the world look
like, and who reacts to our move?"

### Compounding

Small consistent gains that reinvest beat large one-off wins. Also true in
reverse: small consistent losses compound into ruin. Identify the reinvest
loop before predicting growth.

Checklist question: "Does the output of this period become input to the
next, and at what rate?"

### Incentives

People do what they are paid, measured, and punished for, not what they
say. Before predicting behavior, find the incentive. "Show me the incentive
and I will show you the outcome."

Checklist question: "Who benefits from this failing, and who is measured
on a number this changes?"

### Probabilistic thinking

Reason in distributions and expected values, not single scenarios. State
likelihoods, weight outcomes by probability, and size bets so no single bad
draw ends the game.

Checklist question: "What are the 2-3 plausible outcomes with rough odds,
and can we survive the worst realistic one?"

### Inversion

Solve backward: ask what guarantees failure, then avoid that. Avoiding
stupidity is more reliable than seeking brilliance.

Checklist question: "What would make this fail with certainty, and is our
plan structurally exposed to any of those?"

## Part B: Game Theory Toolkit

### Dominant and dominated strategies

A dominant strategy wins regardless of what others do; a dominated one
loses to some alternative no matter what. Apply when one party's payoff
table is fully visible and one option strictly beats another. Eliminate
dominated options first; if a dominant strategy exists, expect it to be
played.

### Nash equilibrium

A stable state where no player gains by unilaterally changing strategy.
Apply when parties act independently without binding agreements. Predict
outcomes at equilibrium even when it is worse for everyone (prisoner's
dilemma); cooperation needs structure, not goodwill.

### Minimax

Choose the option whose worst-case outcome is best. Apply when facing an
adversary who actively optimizes against you, or when downside is
unacceptable. In zero-sum settings, minimax is the rational baseline;
elsewhere it overweights adversaries who may not exist.

### Repeated games and tit-for-tat

When players meet repeatedly, cooperation can hold because defection is
punishable later. Tit-for-tat: cooperate first, mirror the last move,
forgive after retaliation. Apply to supplier, partner, and competitor
relationships that persist. Reputation is the asset; a final round (end of
contract, exit event) breaks cooperation, so watch for endgame timing.

### Mechanism design and incentive compatibility

Design the rules, not the appeals. A mechanism is incentive-compatible
when each participant's best move serves the intended outcome. Apply when
setting compensation, auctions, pricing, voting, or allocation rules.
Test: "If everyone acts selfishly inside these rules, do we still get the
outcome we want?" If not, redesign the rules before blaming the people.

### BATNA in negotiation

Best Alternative To a Negotiated Agreement: your walk-away option, and
theirs. Apply before any negotiation. Your power equals your BATNA
quality, not your arguments. Improve your own BATNA first; estimate theirs
honestly; never accept terms below your BATNA and never bluff past one you
have not verified.

## Application Protocol

When making a recommendation:

1. Name the 2-3 models that actually change the answer. State each in one
   line and show the delta: "without second-order thinking you would pick
   X; with it, Y."
2. State the second-order effects explicitly: what happens after the first
   effect lands, including competitor, customer, and internal reactions.
3. Flag the incentive landscape: who is rewarded by this outcome, who is
   punished, who is measured on something else entirely, and where the
   scheme could be gamed.
4. If no model changes the answer, say the obvious recommendation plainly
   and skip the framework talk.
