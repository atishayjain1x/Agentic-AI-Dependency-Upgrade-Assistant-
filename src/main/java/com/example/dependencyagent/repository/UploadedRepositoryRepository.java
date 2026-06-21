package com.example.dependencyagent.repository;

import com.example.dependencyagent.domain.UploadedRepository;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface UploadedRepositoryRepository extends JpaRepository<UploadedRepository, UUID> {
}
