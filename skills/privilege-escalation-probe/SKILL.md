# Skill: privilege-escalation-probe

## Purpose
FR : Ce skill encapsule les cas de test TrustGate pour le pilier STRIDE "privilege-escalation-probe".
     Il est concu pour etre charge a la demande (progressive disclosure) par
     l'AttackGeneratorAgent, comme enseigne au Jour 3 du cours ("Agent Skills").

EN : This skill encapsulates TrustGate test cases for STRIDE pillar "privilege-escalation-probe".
     It is designed to be loaded on demand (progressive disclosure) by the
     AttackGeneratorAgent, as taught on Day 3 of the course ("Agent Skills").

## Tools exposed
- list_cases : renvoie les cas de test de ce pilier via le serveur MCP.
               returns test cases for this pillar via the MCP server.

## How to invoke (Antigravity / agents-cli)
    agents-cli skill load privilege-escalation-probe

## Expected output
FR : Liste JSON avec test_id, name, payload, expected_safe_behavior.
EN : JSON list with test_id, name, payload, expected_safe_behavior.

## Integration
FR : Requiert "target_profile" dans le contexte partage avant le chargement.
EN : Requires "target_profile" in the shared context before loading.
