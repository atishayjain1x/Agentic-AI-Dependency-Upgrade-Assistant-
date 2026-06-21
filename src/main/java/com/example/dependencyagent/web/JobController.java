package com.example.dependencyagent.web;

import com.example.dependencyagent.service.JobService;
import com.example.dependencyagent.web.dto.CreateFixJobRequest;
import com.example.dependencyagent.web.dto.FixJobResponse;
import com.example.dependencyagent.web.dto.JobReportResponse;
import com.example.dependencyagent.web.dto.JobStatusResponse;
import com.example.dependencyagent.web.dto.UploadJobResponse;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

@Validated
@RestController
@RequestMapping("/api/jobs")
public class JobController {

    private final JobService jobService;

    public JobController(JobService jobService) {
        this.jobService = jobService;
    }

    @PostMapping(consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    @ResponseStatus(HttpStatus.CREATED)
    public UploadJobResponse uploadAndStartAnalysis(
            @RequestParam(required = false) String name,
            @RequestParam("file") @NotNull MultipartFile file
    ) {
        return UploadJobResponse.from(jobService.uploadAndCreateAnalysisJob(name, file));
    }

    @GetMapping
    public List<JobStatusResponse> listJobs() {
        return jobService.listAnalysisJobs().stream()
                .map(JobStatusResponse::from)
                .toList();
    }

    @GetMapping("/{jobId}")
    public JobStatusResponse getJob(@PathVariable UUID jobId) {
        return JobStatusResponse.from(jobService.getAnalysisJob(jobId));
    }

    @GetMapping("/{jobId}/report")
    public JobReportResponse getReport(@PathVariable UUID jobId) {
        return JobReportResponse.from(jobService.getAnalysisJob(jobId));
    }

    @PostMapping("/{jobId}/fix")
    @ResponseStatus(HttpStatus.CREATED)
    public FixJobResponse startFixJob(
            @PathVariable UUID jobId,
            @RequestBody @Valid CreateFixJobRequest request
    ) {
        return FixJobResponse.from(jobService.createFixJob(jobId, request));
    }
}
