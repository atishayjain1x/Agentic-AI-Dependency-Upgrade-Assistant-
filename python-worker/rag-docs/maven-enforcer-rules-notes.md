# Maven Enforcer Rules

## Overview

The Maven Enforcer Plugin helps enforce project-wide standards and build requirements. It is commonly used to ensure consistent Java versions, Maven versions, dependency convergence, and compliance with organizational policies.

**Plugin Coordinate**

```xml
<plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-enforcer-plugin</artifactId>
</plugin>
```

## Common Enforcer Rules

### Require Java Version

Ensures that builds are executed using an approved Java version.

```xml
<requireJavaVersion>
    <version>[17,)</version>
</requireJavaVersion>
```

This is frequently used during migrations to Java 17 or Java 21.

### Require Maven Version

Ensures developers and CI systems use a supported Maven version.

```xml
<requireMavenVersion>
    <version>[3.9,)</version>
</requireMavenVersion>
```

### Dependency Convergence

Detects situations where multiple versions of the same dependency appear in the dependency graph.

For example:

```text
guava:31.1-jre
guava:33.0.0-jre
```

Dependency convergence failures are common after framework upgrades and often indicate the need for version alignment or dependency exclusions.

### Require Upper Bound Dependencies

Ensures that Maven resolves the highest compatible dependency version available in the dependency graph.

This rule helps prevent older transitive dependencies from unexpectedly overriding newer versions.

### Ban Duplicate Classes

Detects duplicate class definitions across artifacts.

Common causes include:

* Competing logging implementations
* Multiple servlet APIs
* Shaded libraries

Duplicate classes can lead to unpredictable runtime behavior.

### Banned Dependencies

Blocks the use of disallowed dependencies.

Example:

```xml
<bannedDependencies>
    <excludes>
        <exclude>log4j:log4j</exclude>
    </excludes>
</bannedDependencies>
```

This is frequently used to prevent vulnerable or deprecated libraries from entering the dependency tree.

## Common Remediation Strategies

### Dependency Convergence Failures

When multiple versions of a dependency are detected:

1. Identify the conflicting dependency paths.
2. Align versions through `dependencyManagement`.
3. Add exclusions where appropriate.
4. Rebuild and verify the dependency tree.

### Duplicate Classes

When duplicate classes are reported:

1. Identify the conflicting artifacts.
2. Determine which dependency should remain.
3. Remove the duplicate through exclusions or version alignment.
4. Re-run Enforcer validation.

### Java Version Violations

When the configured Java version does not satisfy Enforcer requirements:

1. Upgrade the local JDK.
2. Update CI build images.
3. Update Maven toolchains if used.
4. Verify compiler plugin configuration.

## Best Practices

* Use dependency convergence checks in multi-module projects.
* Centralize versions in `dependencyManagement`.
* Keep Enforcer enabled in CI pipelines.
* Treat Enforcer failures as build failures.
* Review banned dependency lists regularly for security updates.
