# Master Services Agreement — Statement of Work No. 3

## Parties and effective date

This Statement of Work is entered into under the Master Services Agreement dated 14 January 2026 between Northgate Analytics Ltd ("Provider") and Halden Municipal Water ("Client"), and is effective on the date of the last signature below.

## Background

The Client operates a telemetry network of 1,400 sensors across its distribution system. Under Statements of Work No. 1 and No. 2 the Provider migrated the historical sensor data to the Client's data platform and delivered the first version of the leak-detection dashboard. This Statement of Work covers the second version of the dashboard and the operational hand-over.

## Services

The Provider shall deliver the following:

1. A revised leak-detection model retrained on the full 2025 dataset, with documented precision and recall on the Client's labelled incident set.
2. Alerting integrated with the Client's on-call system, configurable per district.
3. A hand-over package: deployment runbook, model card, and two training sessions for the Client's operations staff.

The Provider must deliver items 1 and 2 by 30 November 2026 and item 3 by 15 December 2026. The Client shall provide access to the incident set within ten business days of the effective date.

## Fees

Fees are fixed at £84,000, invoiced in three equal instalments on acceptance of each item. Payment terms are thirty days from invoice.

## Example alert

An alert carries the district identifier, the detection timestamp, the estimated flow deviation in litres per minute, and a confidence score, for example: `district=NW-07 ts=2026-09-30T02:14Z deviation=42.5 confidence=0.91`.

## General terms

All other terms of the Master Services Agreement apply. This Statement of Work may be amended only in writing signed by both parties. Nothing in this document creates an employment relationship.

Signed for the Provider: ______________________ Date: ____________

Signed for the Client: ________________________ Date: ____________
