package com.example.dependencyagent.domain;

public enum JobStatus {
    UPLOADED,
    ANALYSIS_RUNNING,
    ANALYSIS_COMPLETED,
    ANALYSIS_FAILED,
    FIX_RUNNING,
    FIX_COMPLETED,
    FIX_FAILED,
    TEST_RUNNING,
    TEST_COMPLETED,
    TEST_FAILED,
    REPORT_REBUILDING,
    COMPLETED,
    FAILED
}
