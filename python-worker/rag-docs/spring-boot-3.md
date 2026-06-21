# Spring Boot 3 Migration Notes

## Overview

Spring Boot 3 is a major release built on Spring Framework 6 and Jakarta EE 9. The migration from Spring Boot 2.x to Spring Boot 3 typically involves Java upgrades, Jakarta namespace migration, Hibernate upgrades, and security configuration changes.

## Prerequisites

### Java 17

Spring Boot 3 requires Java 17 or newer.

Before upgrading:

* Upgrade developer environments.
* Upgrade CI/CD build agents.
* Upgrade runtime containers.
* Verify Java 17 compatibility for all dependencies.

### Spring Framework 6

Spring Boot 3 is based on Spring Framework 6 and inherits many of its API and behavioral changes.

## Recommended Upgrade Path

### Step 1

Upgrade to the latest Spring Boot 2.7.x release.

This reduces migration complexity and exposes deprecation warnings before the major upgrade.

### Step 2

Upgrade to Java 17.

Resolve:

* Compiler issues
* Runtime warnings
* Illegal reflective access problems

### Step 3

Upgrade to Spring Boot 3.

Address Jakarta namespace migration and framework changes.

## Jakarta Namespace Migration

The most significant migration task is replacing Java EE namespaces with Jakarta EE namespaces.

### JPA

Before:

```java
import javax.persistence.Entity;
import javax.persistence.Id;
```

After:

```java
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
```

### Validation

Before:

```java
import javax.validation.Valid;
import javax.validation.constraints.NotNull;
```

After:

```java
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
```

### Servlet APIs

Before:

```java
import javax.servlet.Filter;
import javax.servlet.http.HttpServletRequest;
```

After:

```java
import jakarta.servlet.Filter;
import jakarta.servlet.http.HttpServletRequest;
```

### Common Areas Affected

Review:

* JPA entities
* Bean validation
* Servlet filters
* Listeners
* JMS integrations
* WebSocket implementations
* Third-party libraries

## Spring Security Migration

Spring Security underwent substantial modernization before Spring Boot 3.

### WebSecurityConfigurerAdapter Removal

Before:

```java
@Configuration
@EnableWebSecurity
public class SecurityConfig
        extends WebSecurityConfigurerAdapter {

}
```

After:

```java
@Bean
SecurityFilterChain securityFilterChain(
        HttpSecurity http) throws Exception {

    return http.build();
}
```

### Method Security

Before:

```java
@EnableGlobalMethodSecurity
```

After:

```java
@EnableMethodSecurity
```

Review all security configurations carefully.

## Hibernate Upgrade

Spring Boot 3 uses Hibernate 6.

Potentially affected areas:

* HQL queries
* JPQL queries
* Custom dialects
* UserType implementations
* Identifier generation strategies

Refer to the Hibernate 6 migration guide for additional details.

## Configuration Property Changes

Some configuration properties have been renamed, removed, or reorganized.

Review:

* application.properties
* application.yml
* externalized configuration

Enable startup diagnostics and review warnings during migration.

## Actuator Changes

Review:

* Custom health indicators
* Management endpoints
* Metrics integrations
* Monitoring dashboards

Verify compatibility with existing observability tooling.

## Native Image Support

Spring Boot 3 significantly improves support for GraalVM Native Image.

Applications considering native compilation should review:

* Reflection usage
* Dynamic proxies
* Serialization requirements

## Dependency Review

Common dependency upgrades include:

| Component        | Typical Upgrade           |
| ---------------- | ------------------------- |
| Java             | 17+                       |
| Spring Framework | 6.x                       |
| Hibernate        | 6.x                       |
| Tomcat           | 10.x                      |
| Jackson          | Current supported release |
| Micrometer       | Current supported release |

## Testing Recommendations

Perform:

### Unit Testing

Verify:

* Services
* Controllers
* Configuration classes

### Integration Testing

Verify:

* Database interactions
* Security behavior
* REST endpoints
* Messaging integrations

### End-to-End Testing

Verify:

* Authentication
* Authorization
* Session management
* Production workflows

## Common Migration Issues

### Missing Jakarta Imports

Symptoms:

* Compilation failures
* Missing class errors

Resolution:

Replace all `javax.*` imports with `jakarta.*` equivalents.

### Security Configuration Failures

Symptoms:

* Authentication failures
* Bean creation errors

Resolution:

Migrate to `SecurityFilterChain` configuration.

### Hibernate Query Issues

Symptoms:

* Query parsing failures
* Runtime exceptions

Resolution:

Review and validate all custom queries.

### Third-Party Dependency Compatibility

Symptoms:

* Class loading failures
* Startup exceptions

Resolution:

Upgrade incompatible libraries.

## Deployment Checklist

Before production deployment:

* Upgrade Java runtime.
* Execute regression tests.
* Validate monitoring.
* Validate logging.
* Validate security controls.
* Benchmark performance.
* Verify database migrations.

## Migration Strategy

### Phase 1

Upgrade:

* Java
* Build tooling
* CI/CD pipelines

### Phase 2

Upgrade:

* Spring Boot
* Spring Framework
* Hibernate

### Phase 3

Resolve:

* Jakarta migration issues
* Security changes
* Dependency compatibility

### Phase 4

Execute:

* Functional testing
* Load testing
* Production rollout

## Related Migrations

* Java 11 to Java 17
* Java 17 to Java 21
* Hibernate 6 Migration
* Jakarta EE 9 Migration
* Spring Security 6 Migration
