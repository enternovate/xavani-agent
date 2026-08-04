---
title: "Performing Threat Emulation With Atomic Red Team"
sidebar_label: "Performing Threat Emulation With Atomic Red Team"
description: "Executes Atomic Red Team tests for MITRE ATT&CK technique validation using the atomic-operator Python framework"
---

{/* This page is auto-generated from the skill's SKILL.md by website/scripts/generate-skill-docs.py. Edit the source SKILL.md, not this page. */}

# Performing Threat Emulation With Atomic Red Team

Executes Atomic Red Team tests for MITRE ATT&CK technique validation using the atomic-operator Python framework. Loads test definitions from YAML atomics, runs attack simulations, and validates detection coverage. Use when testing SIEM detection rules, validating EDR coverage, or conducting purple team exercises.

## Skill metadata

| | |
|---|---|
| Source | Optional — install with `xavani skills install official/cybersecurity/performing-threat-emulation-with-atomic-red-team` |
| Path | `optional-skills/cybersecurity/threat-intelligence/performing-threat-emulation-with-atomic-red-team` |
| Platforms | all |

## Reference: full SKILL.md

:::info
The following is the complete skill definition that Xavani loads when this skill is triggered. This is what the agent sees as instructions when the skill is active.
:::

# Performing Threat Emulation with Atomic Red Team


## When to Use

- When conducting security assessments that involve performing threat emulation with atomic red team
- When following incident response procedures for related security events
- When performing scheduled security testing or auditing activities
- When validating security controls through hands-on testing

## Prerequisites

- Familiarity with threat intelligence concepts and tools
- Access to a test or lab environment for safe execution
- Python 3.8+ with required dependencies installed
- Appropriate authorization for any testing activities

## Instructions

Use atomic-operator to execute Atomic Red Team tests and validate detection coverage
against MITRE ATT&CK techniques.

```python
from atomic_operator import AtomicOperator

operator = AtomicOperator()
# Run a specific technique test
operator.run(
    technique="T1059.001",  # PowerShell execution
    atomics_path="./atomic-red-team/atomics",
)
```

Key workflow:
1. Clone the atomic-red-team repository for test definitions
2. Select ATT&CK techniques matching your detection rules
3. Execute atomic tests using atomic-operator
4. Check SIEM/EDR for corresponding alerts
5. Document detection gaps and update rules

## Examples

```python
# Parse atomic test YAML definitions
import yaml
with open("atomics/T1059.001/T1059.001.yaml") as f:
    tests = yaml.safe_load(f)
for test in tests.get("atomic_tests", []):
    print(f"Test: {test['name']}")
    print(f"  Platforms: {test.get('supported_platforms', [])}")
```

## Standards mapping

- **d3fend_techniques**: Executable Denylisting, Execution Isolation, File Metadata Consistency Validation, Content Format Conversion, File Content Analysis
- **atlas_techniques**: AML.T0070, AML.T0066, AML.T0082
- **nist_ai_rmf**: MEASURE-2.7, MAP-5.1, MANAGE-2.4
- **nist_csf**: ID.RA-01, ID.RA-05, DE.CM-01, DE.AE-02
- **license**: Apache-2.0
- **author**: mahipal
