package com.example.dependencyagent.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.PrePersist;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "fix_jobs")
public class FixJob {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "repository_id", nullable = false)
    private UploadedRepository repository;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "analysis_job_id")
    private AnalysisJob analysisJob;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private JobStatus status = JobStatus.FIX_RUNNING;

    @Column(nullable = false)
    private String fixBy;

    @Column(columnDefinition = "text")
    private String dependencyIds;

    private String category;

    @Column(columnDefinition = "text")
    private String planSummary;

    @Column(columnDefinition = "text")
    private String patchSummary;

    @Column(columnDefinition = "text")
    private String workerPayload;

    @Column(columnDefinition = "text")
    private String testOutput;

    @Column(columnDefinition = "text")
    private String rebuiltReportJson;

    @Column(nullable = false, updatable = false)
    private Instant createdAt;

    private Instant startedAt;

    private Instant completedAt;

    private String errorMessage;

    @PrePersist
    void prePersist() {
        createdAt = Instant.now();
    }

    public UUID getId() {
        return id;
    }

    public UploadedRepository getRepository() {
        return repository;
    }

    public void setRepository(UploadedRepository repository) {
        this.repository = repository;
    }

    public AnalysisJob getAnalysisJob() {
        return analysisJob;
    }

    public void setAnalysisJob(AnalysisJob analysisJob) {
        this.analysisJob = analysisJob;
    }

    public JobStatus getStatus() {
        return status;
    }

    public void setStatus(JobStatus status) {
        this.status = status;
    }

    public String getFixBy() {
        return fixBy;
    }

    public void setFixBy(String fixBy) {
        this.fixBy = fixBy;
    }

    public String getDependencyIds() {
        return dependencyIds;
    }

    public void setDependencyIds(String dependencyIds) {
        this.dependencyIds = dependencyIds;
    }

    public String getCategory() {
        return category;
    }

    public void setCategory(String category) {
        this.category = category;
    }

    public String getPlanSummary() {
        return planSummary;
    }

    public void setPlanSummary(String planSummary) {
        this.planSummary = planSummary;
    }

    public String getPatchSummary() {
        return patchSummary;
    }

    public void setPatchSummary(String patchSummary) {
        this.patchSummary = patchSummary;
    }

    public String getWorkerPayload() {
        return workerPayload;
    }

    public void setWorkerPayload(String workerPayload) {
        this.workerPayload = workerPayload;
    }

    public String getTestOutput() {
        return testOutput;
    }

    public void setTestOutput(String testOutput) {
        this.testOutput = testOutput;
    }

    public String getRebuiltReportJson() {
        return rebuiltReportJson;
    }

    public void setRebuiltReportJson(String rebuiltReportJson) {
        this.rebuiltReportJson = rebuiltReportJson;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public Instant getStartedAt() {
        return startedAt;
    }

    public void setStartedAt(Instant startedAt) {
        this.startedAt = startedAt;
    }

    public Instant getCompletedAt() {
        return completedAt;
    }

    public void setCompletedAt(Instant completedAt) {
        this.completedAt = completedAt;
    }

    public String getErrorMessage() {
        return errorMessage;
    }

    public void setErrorMessage(String errorMessage) {
        this.errorMessage = errorMessage;
    }
}
