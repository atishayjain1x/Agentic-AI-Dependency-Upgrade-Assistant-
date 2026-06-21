# Maven Dependency Management Notes

## Purpose

Knowledge base for Maven dependency resolution, version alignment, BOM management, and automated upgrade planning.

---

# Core Concept

Use dependencyManagement to control dependency versions centrally.

Benefits

- Consistent versions
- Easier upgrades
- Reduced conflicts
- Reproducible builds

---

# Dependency Management Example

```xml
<dependencyManagement>
  <dependencies>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-dependencies</artifactId>
      <version>3.5.0</version>
      <type>pom</type>
      <scope>import</scope>
    </dependency>
  </dependencies>
</dependencyManagement>
```

---

# BOM Usage

## Spring Boot BOM

```text
org.springframework.boot:spring-boot-dependencies
```

## Jackson BOM

```text
com.fasterxml.jackson:jackson-bom
```

## Log4j BOM

```text
org.apache.logging.log4j:log4j-bom
```

---

# Resolution Rules

## Direct Dependency Wins

Example

```text
Project
 ├─ guava 33.0
 └─ libraryA
      └─ guava 31.1
```

Effective Version

```text
33.0
```

---

## Nearest Definition Wins

When multiple transitive versions exist, Maven chooses the nearest dependency path.

---

# Migration Rules

## DEP-MGMT-001

Condition

Same artifact appears with multiple versions.

Action

Manage version centrally.

Priority

HIGH

---

## DEP-MGMT-002

Condition

Dependency version declared repeatedly.

Action

Move version to dependencyManagement.

Priority

MEDIUM

---

## DEP-MGMT-003

Condition

BOM available for dependency family.

Action

Import BOM.

Priority

HIGH

Examples

- Spring Boot BOM
- Jackson BOM
- Log4j BOM

---

## DEP-MGMT-004

Condition

Transitive dependency causes vulnerability.

Action

Override version in dependencyManagement.

Priority

CRITICAL

---

## DEP-MGMT-005

Condition

Version drift across modules.

Action

Centralize version management.

Priority

HIGH

