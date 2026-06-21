package com.example.dependencyagent.worker;

public record WorkerFixResult(
        String planSummary,
        String patchSummary,
        String testOutput,
        String rebuiltReportJson,
        String rawPayload
) {
}
