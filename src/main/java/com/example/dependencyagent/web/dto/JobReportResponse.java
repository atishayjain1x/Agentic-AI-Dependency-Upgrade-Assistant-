package com.example.dependencyagent.web.dto;

import com.example.dependencyagent.domain.AnalysisJob;
import com.example.dependencyagent.domain.JobStatus;
import java.time.Instant;
import java.util.UUID;

public record JobReportResponse(
        UUID jobId,
        JobStatus status,
        String summary,
        String reportJson,
        String workerPayload,
        Instant completedAt
) {
    public static JobReportResponse from(AnalysisJob job) {
        return new JobReportResponse(
                job.getId(),
                job.getStatus(),
                job.getSummary(),
                job.getReportJson(),
                job.getWorkerPayload(),
                job.getCompletedAt()
        );
    }
}
