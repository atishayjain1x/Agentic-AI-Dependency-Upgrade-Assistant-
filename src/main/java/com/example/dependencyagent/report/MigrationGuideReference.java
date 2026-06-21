package com.example.dependencyagent.report;

public record MigrationGuideReference(
        String title,
        String source,
        String url,
        double relevanceScore
) {
}
