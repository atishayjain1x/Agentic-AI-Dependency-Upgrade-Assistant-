package com.example.dependencyagent.service;

import com.example.dependencyagent.domain.UploadedRepository;
import com.example.dependencyagent.repository.UploadedRepositoryRepository;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

@Service
public class RepositoryService {

    private final UploadedRepositoryRepository repositoryRepository;
    private final StorageService storageService;

    public RepositoryService(UploadedRepositoryRepository repositoryRepository, StorageService storageService) {
        this.repositoryRepository = repositoryRepository;
        this.storageService = storageService;
    }

    @Transactional
    public UploadedRepository upload(String name, MultipartFile file) {
        StorageService.StoredFile storedFile = storageService.storeZip(file);
        UploadedRepository repository = new UploadedRepository();
        repository.setName(resolveName(name, storedFile.originalFilename()));
        repository.setOriginalFilename(storedFile.originalFilename());
        repository.setContentType(file.getContentType() == null ? "application/zip" : file.getContentType());
        repository.setSizeBytes(file.getSize());
        repository.setStoragePath(storedFile.storagePath());
        return repositoryRepository.save(repository);
    }

    @Transactional(readOnly = true)
    public UploadedRepository get(UUID id) {
        return repositoryRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Repository upload not found: " + id));
    }

    private String resolveName(String requestedName, String originalFilename) {
        if (requestedName != null && !requestedName.isBlank()) {
            return requestedName.trim();
        }
        return originalFilename.replaceFirst("(?i)\\.zip$", "");
    }
}
