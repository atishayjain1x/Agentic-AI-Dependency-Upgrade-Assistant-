package com.example.dependencyagent.web.dto;

import com.example.dependencyagent.domain.AnalysisJob;
import com.example.dependencyagent.domain.JobStatus;
import java.time.Instant;
import java.util.UUID;

public record UploadJobResponse(
        UUID jobId,
        JobStatus status,
        Instant createdAt
) {
    public static UploadJobResponse from(AnalysisJob job) {
        return new UploadJobResponse(job.getId(), job.getStatus(), job.getCreatedAt());
    }
}
