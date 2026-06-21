package com.example.dependencyagent.worker;

import com.example.dependencyagent.domain.AnalysisJob;
import com.example.dependencyagent.domain.FixJob;

public interface WorkerClient {

    WorkerAnalysisResult analyze(AnalysisJob job);

    WorkerFixResult fix(FixJob job);
}
