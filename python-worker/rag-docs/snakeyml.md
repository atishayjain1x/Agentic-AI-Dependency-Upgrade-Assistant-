# SnakeYAML Upgrade Notes

## Purpose

Upgrade and security guidance for SnakeYAML.

---

# Maven Coordinate

org.yaml:snakeyaml

---

# Security Context

Older SnakeYAML versions have been associated with unsafe deserialization concerns.

---

# Recommended Baseline

2.x+

---

# Major Change

Old:

Yaml yaml = new Yaml();

Preferred:

Use SafeConstructor or secure loader configuration.

---

# Migration Rules

## SNAKEYAML-001

Condition:
Version < approved baseline

Action:
Upgrade

## SNAKEYAML-002

Condition:
Default Yaml constructor usage

Action:
Review for secure loading

---

# Review Areas

Custom constructors

Type descriptions

Object binding

Configuration loading

---

