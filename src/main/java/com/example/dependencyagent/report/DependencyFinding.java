package com.example.dependencyagent.report;

import com.example.dependencyagent.domain.FixCategory;
import com.example.dependencyagent.domain.FixPriority;
import java.util.List;

public record DependencyFinding(
        String dependencyId,
        String groupId,
        String artifactId,
        String currentVersion,
        String recommendedVersion,
        String latestVersion,
        String scope,
        String usageLocation,
        FixPriority priority,
        FixCategory category,
        String reason,
        List<MigrationGuideReference> migrationGuideRefs,
        boolean fixAvailable
) {
}
