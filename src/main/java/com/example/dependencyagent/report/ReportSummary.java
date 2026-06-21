package com.example.dependencyagent.report;

public record ReportSummary(
        int totalDependencies,
        int upgradeCandidates,
        int criticalCount,
        int highCount,
        int mediumCount,
        int lowCount
) {
}
