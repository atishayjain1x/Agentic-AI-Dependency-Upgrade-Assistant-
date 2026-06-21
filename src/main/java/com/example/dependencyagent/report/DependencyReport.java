package com.example.dependencyagent.report;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

public record DependencyReport(
        UUID jobId,
        String repositoryName,
        String buildTool,
        Instant generatedAt,
        List<DependencyFinding> findings,
        ReportSummary summary
) {
}
