package com.example.dependencyagent.repository;

import com.example.dependencyagent.domain.FixJob;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;

public interface FixJobRepository extends JpaRepository<FixJob, UUID> {

    @Override
    @EntityGraph(attributePaths = {"repository", "analysisJob"})
    Optional<FixJob> findById(UUID id);

    @EntityGraph(attributePaths = {"repository", "analysisJob"})
    List<FixJob> findAllByOrderByCreatedAtDesc();

    @EntityGraph(attributePaths = {"repository", "analysisJob"})
    List<FixJob> findByRepositoryIdOrderByCreatedAtDesc(UUID repositoryId);
}
