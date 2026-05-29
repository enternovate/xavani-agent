---
name: tukey-guidelines
description: John Tukey's principles — Exploratory Data Analysis, robust statistics, the right question before the exact answer, visual summaries.
domain: data-analysis
mandatory: true
priority: 95
version: 1.0
sources:
  - "Exploratory Data Analysis (Tukey 1977)"
  - "The Future of Data Analysis (Tukey 1962, Annals of Mathematical Statistics)"
  - "Understanding Robust and Exploratory Data Analysis (Hoaglin, Mosteller, Tukey 1983)"
---

# John Tukey — Operating Guidelines

> "Far better an approximate answer to the right question, which is often vague, than an exact answer to the wrong question, which can always be made precise."

## Core Principles (always-on)

1. **Look at the data before modelling.** Plot it. Summarise it. Notice outliers. Most modelling failures are data failures discovered too late. EDA is not optional pre-work; it is the work.

2. **Right question > exact answer.** A precisely-wrong answer is worse than a roughly-right one. Spend disproportionate effort on framing the question correctly.

3. **Robust over efficient.** Estimators that work under perfect assumptions but break under reality are worse than estimators that work everywhere with slightly less precision. Use median over mean when outliers are possible.

4. **Visual summaries first.** Box plots, stem-and-leaf, five-number summaries — these compress thousands of observations into eyeball-able form. Build the visualisation before the model.

5. **Confirmatory analysis is for the second pass.** First, explore. Discover the structure. Then, confirm with a fresh dataset. Mixing exploration and confirmation on the same data inflates false positives.

6. **Multiple comparisons require correction.** Twenty independent tests at p=0.05 expect one false positive. Adjust accordingly — or admit you're exploring, not confirming.

## Heuristics for the agent

- Before fitting a model, **plot the raw data** — at least a histogram or summary.
- Default to **robust statistics** (median, MAD) unless the distribution is known clean.
- Phrase a question as **"what does the data show?"** before "is X significant?"
- When reporting metrics, include the **five-number summary** alongside the mean.
- For any A/B claim, ask: **how many comparisons did we make?** and adjust.

## Anti-patterns to reject

- "We computed the mean, the mean is X" — without distribution shape the mean lies.
- "p < 0.05, ship it" — multiple comparisons + small samples + cherry-picking = noise.
- "The model assumes normality, and the data is normally distributed" — verify, don't assume.

## When to invoke

- Reviewing experimental results.
- Designing dashboards, metrics, or evaluations.
- Diagnosing model behaviour from logged data.
