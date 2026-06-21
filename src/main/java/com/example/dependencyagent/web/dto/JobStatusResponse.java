package com.example.dependencyagent.web.dto;

import com.example.dependencyagent.domain.AnalysisJob;
import com.example.dependencyagent.domain.JobStatus;
import java.time.Instant;
import java.util.UUID;

public record JobStatusResponse(
        UUID jobId,
        JobStatus status,
        String repositoryName,
        Instant createdAt,
        Instant startedAt,
        Instant completedAt,
        String errorMessage
) {
    public static JobStatusResponse from(AnalysisJob job) {
        return new JobStatusResponse(
                job.getId(),
                job.getStatus(),
                job.getRepository().getName(),
                job.getCreatedAt(),
                job.getStartedAt(),
                job.getCompletedAt(),
                job.getErrorMessage()
        );
    }
}
