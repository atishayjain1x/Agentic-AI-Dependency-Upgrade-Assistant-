package com.example.dependencyagent.repository;

import com.example.dependencyagent.domain.AnalysisJob;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;

public interface AnalysisJobRepository extends JpaRepository<AnalysisJob, UUID> {

    @Override
    @EntityGraph(attributePaths = "repository")
    Optional<AnalysisJob> findById(UUID id);

    @EntityGraph(attributePaths = "repository")
    List<AnalysisJob> findAllByOrderByCreatedAtDesc();

    @EntityGraph(attributePaths = "repository")
    List<AnalysisJob> findByRepositoryIdOrderByCreatedAtDesc(UUID repositoryId);
}
