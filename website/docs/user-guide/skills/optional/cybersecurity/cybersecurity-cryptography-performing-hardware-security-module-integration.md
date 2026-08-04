---
title: "Performing Hardware Security Module Integration"
sidebar_label: "Performing Hardware Security Module Integration"
description: "Integrate Hardware Security Modules (HSMs) using PKCS#11 interface for cryptographic key management, signing operations, and secure key storage with python-p..."
---

{/* This page is auto-generated from the skill's SKILL.md by website/scripts/generate-skill-docs.py. Edit the source SKILL.md, not this page. */}

# Performing Hardware Security Module Integration

Integrate Hardware Security Modules (HSMs) using PKCS#11 interface for cryptographic key management, signing operations, and secure key storage with python-pkcs11, AWS CloudHSM, and YubiHSM2.

## Skill metadata

| | |
|---|---|
| Source | Optional — install with `xavani skills install official/cybersecurity/performing-hardware-security-module-integration` |
| Path | `optional-skills/cybersecurity/cryptography/performing-hardware-security-module-integration` |
| Platforms | all |

## Reference: full SKILL.md

:::info
The following is the complete skill definition that Xavani loads when this skill is triggered. This is what the agent sees as instructions when the skill is active.
:::

# Performing Hardware Security Module Integration

## Overview

Hardware Security Modules (HSMs) provide tamper-resistant cryptographic key storage and operations. This skill covers integrating with HSMs via the PKCS#11 standard interface using python-pkcs11, performing key generation, signing, encryption, and verification operations, querying token and slot information, and validating HSM configuration for compliance with FIPS 140-2/3 requirements.


## When to Use

- When conducting security assessments that involve performing hardware security module integration
- When following incident response procedures for related security events
- When performing scheduled security testing or auditing activities
- When validating security controls through hands-on testing

## Prerequisites

- HSM device or software HSM (SoftHSM2 for testing)
- PKCS#11 shared library (.so/.dll) for the HSM vendor
- Python 3.9+ with `python-pkcs11`
- Token initialized with SO PIN and user PIN
- For AWS CloudHSM: `cloudhsm-pkcs11` provider configured

## Steps

1. Load PKCS#11 library and enumerate available slots and tokens
2. Open session and authenticate with user PIN
3. Generate RSA 2048-bit or EC P-256 key pairs on the HSM
4. Perform signing and verification using on-device keys
5. List all objects (keys, certificates) stored on the token
6. Query mechanism list to verify supported algorithms
7. Generate compliance report with key inventory and algorithm audit

## Expected Output

- JSON report listing HSM slots, tokens, stored keys, supported mechanisms, and compliance status
- Signing test results with key metadata and algorithm details

## Standards mapping

- **atlas_techniques**: AML.T0070, AML.T0066, AML.T0082
- **nist_ai_rmf**: MEASURE-2.7, MAP-5.1, MANAGE-2.4
- **nist_csf**: PR.DS-01, PR.DS-02, PR.DS-10
- **license**: Apache-2.0
- **author**: mahipal
