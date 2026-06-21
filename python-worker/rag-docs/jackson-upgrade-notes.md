# Jackson Upgrade Notes

## Overview

Jackson is the most widely used JSON processing library in the Java ecosystem. It provides serialization, deserialization, tree-model processing, streaming APIs, and integrations with major frameworks such as Spring Boot, Micronaut, Quarkus, and Hibernate.

Jackson upgrades are generally straightforward, but applications should review custom serializers, deserializers, modules, polymorphic type handling, and security-sensitive deserialization configurations.

## Core Artifacts

### Jackson Databind

```xml
<dependency>
    <groupId>com.fasterxml.jackson.core</groupId>
    <artifactId>jackson-databind</artifactId>
</dependency>
```

### Jackson Core

```xml
<dependency>
    <groupId>com.fasterxml.jackson.core</groupId>
    <artifactId>jackson-core</artifactId>
</dependency>
```

### Jackson Annotations

```xml
<dependency>
    <groupId>com.fasterxml.jackson.core</groupId>
    <artifactId>jackson-annotations</artifactId>
</dependency>
```

## Recommended Upgrade Strategy

### Keep Jackson Modules Aligned

Upgrade all Jackson artifacts together.

Preferred:

```xml
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>com.fasterxml.jackson</groupId>
            <artifactId>jackson-bom</artifactId>
            <version>${jackson.version}</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>
```

Avoid mixing different Jackson minor versions.

## Common Upgrade Areas

### ObjectMapper Configuration

Review custom configuration.

Example:

```java
ObjectMapper mapper = new ObjectMapper()
    .findAndRegisterModules();
```

Verify:

* Serialization behavior
* Deserialization behavior
* Null handling
* Unknown property handling

after upgrades.

## Java Time Support

Applications using Java date and time APIs should register:

```java
JavaTimeModule
```

Example:

```java
ObjectMapper mapper = new ObjectMapper();
mapper.registerModule(new JavaTimeModule());
```

Validate serialization formats after upgrading.

## Custom Serializers

Review implementations of:

```java
JsonSerializer<T>
```

Validate:

* Generated JSON structure
* Field names
* Date formatting
* Null handling

## Custom Deserializers

Review implementations of:

```java
JsonDeserializer<T>
```

Validate:

* Backward compatibility
* Input validation
* Error handling

## Polymorphic Type Handling

Jackson supports polymorphic deserialization using annotations such as:

```java
@JsonTypeInfo
@JsonSubTypes
```

Review carefully during upgrades because these features are frequently involved in security-related changes.

## Security Considerations

Historically, many Jackson security advisories involved unsafe polymorphic deserialization.

Review usages of:

```java
enableDefaultTyping(...)
```

and similar legacy configurations.

Prefer explicit type registration where possible.

## Module Compatibility

Review installed modules:

### Java Time

```xml
jackson-datatype-jsr310
```

### JDK 8 Types

```xml
jackson-datatype-jdk8
```

### Parameter Names

```xml
jackson-module-parameter-names
```

### Kotlin

```xml
jackson-module-kotlin
```

Ensure all modules use compatible versions.

## Spring Boot Integration

Spring Boot manages Jackson versions automatically.

Avoid overriding Jackson dependencies unless necessary.

If overriding:

* Upgrade all Jackson modules together.
* Validate application startup.
* Verify API compatibility.

## Records Support

Modern Jackson versions provide strong support for Java records.

Example:

```java
public record User(
    String name,
    int age
) {}
```

Validate:

* Constructor binding
* Property names
* Serialization formats

## Performance Validation

Benchmark:

* Serialization throughput
* Deserialization throughput
* Memory consumption
* Streaming workloads

especially when upgrading across multiple major versions.

## Common Migration Issues

### Unknown Property Failures

Symptoms:

```text
UnrecognizedPropertyException
```

Resolution:

Review DTO definitions and deserialization configuration.

### Date Serialization Changes

Symptoms:

* Different JSON date formats
* Timezone issues

Resolution:

Review JavaTimeModule configuration.

### Module Version Mismatches

Symptoms:

* Class loading errors
* Runtime exceptions

Resolution:

Align all Jackson module versions.

### Custom Serializer Failures

Symptoms:

* Incorrect JSON output
* Serialization exceptions

Resolution:

Review serializer implementations and regression tests.

## Testing Recommendations

### Unit Testing

Verify:

* Serialization
* Deserialization
* DTO mappings

### Integration Testing

Verify:

* REST APIs
* Message consumers
* Message producers
* Database JSON mappings

### Contract Testing

Validate:

* Public APIs
* External integrations
* Backward compatibility

## Upgrade Checklist

1. Upgrade all Jackson modules together.
2. Prefer BOM-based version management.
3. Validate ObjectMapper configuration.
4. Review custom serializers.
5. Review custom deserializers.
6. Validate date/time handling.
7. Execute API contract tests.
8. Verify performance characteristics.
9. Review security-sensitive deserialization settings.
10. Deploy incrementally.

## Related Topics

* Spring Boot 3 Migration
* Java 17 Migration
* Java 21 Migration
* Maven Dependency Management
* JSON API Compatibility
