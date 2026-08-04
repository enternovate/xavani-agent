---
title: "Implementing Container Network Policies With Calico"
sidebar_label: "Implementing Container Network Policies With Calico"
description: "Enforce Kubernetes network segmentation using Calico CNI network policies and global network policies to control pod-to-pod traffic, restrict egress, and imp..."
---

{/* This page is auto-generated from the skill's SKILL.md by website/scripts/generate-skill-docs.py. Edit the source SKILL.md, not this page. */}

# Implementing Container Network Policies With Calico

Enforce Kubernetes network segmentation using Calico CNI network policies and global network policies to control pod-to-pod traffic, restrict egress, and implement zero-trust microsegmentation.

## Skill metadata

| | |
|---|---|
| Source | Optional — install with `xavani skills install official/cybersecurity/implementing-container-network-policies-with-calico` |
| Path | `optional-skills/cybersecurity/container-security/implementing-container-network-policies-with-calico` |
| Platforms | all |

## Reference: full SKILL.md

:::info
The following is the complete skill definition that Xavani loads when this skill is triggered. This is what the agent sees as instructions when the skill is active.
:::

# Implementing Container Network Policies with Calico

## Overview

Calico provides Kubernetes-native and extended network policy enforcement through its CNI plugin. This skill covers creating and auditing Calico NetworkPolicy and GlobalNetworkPolicy resources to implement pod-to-pod traffic control, namespace isolation, egress restrictions, and DNS-based policy rules using calicoctl and the Kubernetes API.


## When to Use

- When deploying or configuring implementing container network policies with calico capabilities in your environment
- When establishing security controls aligned to compliance requirements
- When building or improving security architecture for this domain
- When conducting security assessments that require this implementation

## Prerequisites

- Kubernetes cluster with Calico CNI installed
- Python 3.9+ with `kubernetes` client library
- calicoctl CLI tool installed and configured
- kubectl access with RBAC permissions for network policy management

## Steps

### Step 1: Audit Existing Network Policies
Use calicoctl and kubectl to inventory current network policies and identify unprotected namespaces.

### Step 2: Implement Default-Deny Policies
Create default-deny ingress and egress policies per namespace as a zero-trust baseline.

### Step 3: Create Workload-Specific Allow Rules
Define granular allow rules for legitimate pod-to-pod and pod-to-service communication.

### Step 4: Validate Policy Enforcement
Test connectivity between pods to verify policies are correctly enforced.

## Expected Output

JSON audit report listing all network policies, unprotected namespaces, policy rule counts, and connectivity test results.

## Standards mapping

- **nist_csf**: PR.PS-01, PR.IR-01, ID.AM-08, DE.CM-01
- **license**: Apache-2.0
- **author**: mahipal
