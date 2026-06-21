package com.example.dependencyagent.service;

import com.example.dependencyagent.domain.AnalysisJob;
import com.example.dependencyagent.domain.FixJob;
import com.example.dependencyagent.domain.JobStatus;
import com.example.dependencyagent.domain.UploadedRepository;
import com.example.dependencyagent.repository.AnalysisJobRepository;
import com.example.dependencyagent.repository.FixJobRepository;
import com.example.dependencyagent.worker.WorkerAnalysisResult;
import com.example.dependencyagent.worker.WorkerClient;
import com.example.dependencyagent.worker.WorkerFixResult;
import com.example.dependencyagent.web.dto.CreateFixJobRequest;
import java.time.Instant;
import java.util.List;
import java.util.stream.Collectors;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

@Service
public class JobService {

    private final RepositoryService repositoryService;
    private final AnalysisJobRepository analysisJobRepository;
    private final FixJobRepository fixJobRepository;
    private final WorkerClient workerClient;

    public JobService(
            RepositoryService repositoryService,
            AnalysisJobRepository analysisJobRepository,
            FixJobRepository fixJobRepository,
            WorkerClient workerClient
    ) {
        this.repositoryService = repositoryService;
        this.analysisJobRepository = analysisJobRepository;
        this.fixJobRepository = fixJobRepository;
        this.workerClient = workerClient;
    }

    @Transactional
    public AnalysisJob uploadAndCreateAnalysisJob(String name, MultipartFile file) {
        UploadedRepository repository = repositoryService.upload(name, file);
        AnalysisJob job = new AnalysisJob();
        job.setRepository(repository);
        job.setStatus(JobStatus.UPLOADED);
        AnalysisJob saved = analysisJobRepository.save(job);
        runAnalysis(saved);
        return saved;
    }

    @Transactional(readOnly = true)
    public AnalysisJob getAnalysisJob(UUID id) {
        return analysisJobRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Analysis job not found: " + id));
    }

    @Transactional(readOnly = true)
    public List<AnalysisJob> listAnalysisJobs() {
        return analysisJobRepository.findAllByOrderByCreatedAtDesc();
    }

    @Transactional
    public FixJob createFixJob(UUID jobId, CreateFixJobRequest request) {
        AnalysisJob analysisJob = getAnalysisJob(jobId);
        FixJob job = new FixJob();
        job.setRepository(analysisJob.getRepository());
        job.setAnalysisJob(analysisJob);
        job.setFixBy(request.fixBy());
        job.setDependencyIds((request.dependencyIds() == null ? List.<String>of() : request.dependencyIds())
                .stream()
                .collect(Collectors.joining(",")));
        job.setCategory(request.category());
        FixJob saved = fixJobRepository.save(job);
        runFix(saved);
        return saved;
    }

    @Transactional(readOnly = true)
    public FixJob getFixJob(UUID id) {
        return fixJobRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Fix job not found: " + id));
    }

    @Transactional(readOnly = true)
    public List<FixJob> listFixReports() {
        return fixJobRepository.findAllByOrderByCreatedAtDesc();
    }

    private void runAnalysis(AnalysisJob job) {
        job.setStatus(JobStatus.ANALYSIS_RUNNING);
        job.setStartedAt(Instant.now());
        try {
            WorkerAnalysisResult result = workerClient.analyze(job);
            job.setSummary(result.summary());
            job.setReportJson(result.reportJson());
            job.setWorkerPayload(result.rawPayload());
            job.setStatus(JobStatus.ANALYSIS_COMPLETED);
        } catch (RuntimeException exception) {
            job.setStatus(JobStatus.ANALYSIS_FAILED);
            job.setErrorMessage(exception.getMessage());
        } finally {
            job.setCompletedAt(Instant.now());
        }
    }

    private void runFix(FixJob job) {
        job.setStatus(JobStatus.FIX_RUNNING);
        job.setStartedAt(Instant.now());
        try {
            WorkerFixResult result = workerClient.fix(job);
            job.setPlanSummary(result.planSummary());
            job.setPatchSummary(result.patchSummary());
            job.setTestOutput(result.testOutput());
            job.setStatus(JobStatus.REPORT_REBUILDING);
            job.setRebuiltReportJson(result.rebuiltReportJson());
            job.setWorkerPayload(result.rawPayload());
            job.setStatus(JobStatus.COMPLETED);
        } catch (RuntimeException exception) {
            job.setStatus(JobStatus.FIX_FAILED);
            job.setErrorMessage(exception.getMessage());
        } finally {
            job.setCompletedAt(Instant.now());
        }
    }
}
