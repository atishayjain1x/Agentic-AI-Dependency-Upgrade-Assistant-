# Hibernate 6 Migration Notes

## Overview

Hibernate 6 is a major release that introduces substantial internal changes, improved SQL generation, enhanced query capabilities, and full alignment with Jakarta Persistence.

Many organizations adopt Hibernate 6 as part of a Spring Boot 3 migration because Spring Boot 3 uses Hibernate 6 by default.

## Prerequisites

Before upgrading:

* Upgrade to Java 11 or later (Java 17 recommended).
* Complete Jakarta namespace migration.
* Upgrade dependent frameworks.
* Verify database compatibility.

## Dependency

### Maven

```xml
<dependency>
    <groupId>org.hibernate.orm</groupId>
    <artifactId>hibernate-core</artifactId>
</dependency>
```

## Jakarta Persistence Migration

Hibernate 6 uses Jakarta Persistence APIs.

### Before

```java
import javax.persistence.Entity;
import javax.persistence.Id;
import javax.persistence.Table;
```

### After

```java
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
```

### Commonly Affected Imports

Review:

```java
javax.persistence.*
```

Replace with:

```java
jakarta.persistence.*
```

This affects:

* Entities
* Repositories
* Entity listeners
* Converters
* Validation integrations

## Query Language Changes

Hibernate 6 introduces a redesigned query engine.

Review:

* HQL
* JPQL
* Criteria API
* Native SQL queries

### Areas Requiring Validation

* Custom queries
* Dynamic query generation
* Projection queries
* Aggregation queries
* Complex joins

Even queries that compile successfully should be tested against production data.

## Criteria API

Most Criteria API code remains compatible, but complex criteria queries should be reviewed and tested.

Validate:

* Predicate generation
* Joins
* Subqueries
* Grouping operations

## Identifier Generation

Custom identifier strategies may require updates.

Review:

* Sequence generators
* Table generators
* UUID generators
* Custom IdentifierGenerator implementations

### Example

```java
@GeneratedValue(strategy = GenerationType.SEQUENCE)
```

Verify generated SQL and sequence behavior after migration.

## Type System Changes

Hibernate 6 significantly changes internal type handling.

Review custom implementations of:

```java
UserType
CompositeUserType
```

and any custom type mappings.

### Areas to Test

* JSON mappings
* Enum mappings
* UUID mappings
* Date/time mappings
* Custom value objects

## Dialect Changes

Database dialect implementations have been modernized.

### Review

* Custom dialect classes
* SQL overrides
* Database-specific extensions

### Common Databases

Verify compatibility with:

* PostgreSQL
* Oracle
* SQL Server
* MySQL
* MariaDB

## SQL Generation

Hibernate 6 may generate different SQL than previous releases.

Validate:

* Generated joins
* Pagination queries
* Batch operations
* Locking statements

Use SQL logging during migration testing.

## Fetching and Loading

Review:

* Lazy loading
* Eager loading
* Entity graphs
* Batch fetching

Verify that performance characteristics remain acceptable.

## Caching

If second-level caching is enabled:

Review:

* Cache providers
* Cache configuration
* Cache invalidation behavior

Common providers include:

* Ehcache
* Hazelcast
* Infinispan

## Schema Generation

Validate:

* DDL generation
* Schema validation
* Migration scripts

Review generated changes before applying them to production environments.

## Common Migration Issues

### Query Failures

Symptoms:

* Query parsing exceptions
* Runtime query errors

Resolution:

Review query syntax and generated SQL.

### Type Mapping Errors

Symptoms:

* Serialization failures
* Conversion exceptions

Resolution:

Review custom types and converters.

### Identifier Generation Problems

Symptoms:

* Primary key generation failures
* Sequence errors

Resolution:

Validate identifier strategies and database configuration.

### Dialect Compatibility Issues

Symptoms:

* SQL syntax errors
* Unsupported database features

Resolution:

Upgrade or modify dialect implementations.

## Testing Recommendations

### Functional Testing

Verify:

* CRUD operations
* Repository methods
* Transactions

### Integration Testing

Verify:

* Entity relationships
* Query execution
* Batch processing

### Performance Testing

Measure:

* Query latency
* Throughput
* Memory consumption
* Database load

### Database Validation

Verify:

* Schema compatibility
* Migration scripts
* Index usage
* Query plans

## Upgrade Checklist

1. Upgrade Java runtime.
2. Complete Jakarta migration.
3. Upgrade Hibernate dependencies.
4. Review custom queries.
5. Review custom types.
6. Review custom dialects.
7. Execute integration tests.
8. Validate generated SQL.
9. Benchmark performance.
10. Deploy incrementally.

## Recommended Migration Strategy

### Phase 1

Upgrade:

* Java
* Build tooling
* Dependencies

### Phase 2

Perform:

* Jakarta namespace migration
* Compilation fixes

### Phase 3

Validate:

* Queries
* Mappings
* Transactions

### Phase 4

Execute:

* Load testing
* Production rollout

## Related Migrations

* Spring Boot 3 Migration
* Jakarta EE 9 Migration
* Java 11 to Java 17 Migration
* Java 17 to Java 21 Migration
