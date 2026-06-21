package com.example.dependencyagent.web.dto;

import com.example.dependencyagent.domain.FixJob;
import com.example.dependencyagent.domain.JobStatus;
import java.time.Instant;
import java.util.UUID;

public record FixJobResponse(
        UUID id,
        UUID repositoryId,
        UUID analysisJobId,
        JobStatus status,
        String fixBy,
        String dependencyIds,
        String category,
        String planSummary,
        String patchSummary,
        String testOutput,
        String rebuiltReportJson,
        String workerPayload,
        Instant createdAt,
        Instant startedAt,
        Instant completedAt,
        String errorMessage
) {
    public static FixJobResponse from(FixJob job) {
        UUID analysisJobId = job.getAnalysisJob() == null ? null : job.getAnalysisJob().getId();
        return new FixJobResponse(
                job.getId(),
                job.getRepository().getId(),
                analysisJobId,
                job.getStatus(),
                job.getFixBy(),
                job.getDependencyIds(),
                job.getCategory(),
                job.getPlanSummary(),
                job.getPatchSummary(),
                job.getTestOutput(),
                job.getRebuiltReportJson(),
                job.getWorkerPayload(),
                job.getCreatedAt(),
                job.getStartedAt(),
                job.getCompletedAt(),
                job.getErrorMessage()
        );
    }
}
