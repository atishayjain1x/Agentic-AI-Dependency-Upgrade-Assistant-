package com.example.dependencyagent.service;

import com.example.dependencyagent.config.StorageProperties;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;
import org.springframework.web.multipart.MultipartFile;

@Service
public class StorageService {

    private final Path root;

    public StorageService(StorageProperties properties) {
        this.root = Path.of(properties.root()).toAbsolutePath().normalize();
    }

    public StoredFile storeZip(MultipartFile file) {
        if (file.isEmpty()) {
            throw new IllegalArgumentException("Upload file must not be empty.");
        }

        String originalFilename = StringUtils.cleanPath(
                file.getOriginalFilename() == null ? "repo.zip" : file.getOriginalFilename()
        );
        if (!originalFilename.toLowerCase().endsWith(".zip")) {
            throw new IllegalArgumentException("Only .zip uploads are supported.");
        }

        UUID uploadId = UUID.randomUUID();
        Path directory = root.resolve(uploadId.toString()).normalize();
        Path destination = directory.resolve("repo.zip").normalize();
        if (!destination.startsWith(root)) {
            throw new IllegalArgumentException("Invalid upload path.");
        }

        try {
            Files.createDirectories(directory);
            try (InputStream inputStream = file.getInputStream()) {
                Files.copy(inputStream, destination, StandardCopyOption.REPLACE_EXISTING);
            }
        } catch (IOException exception) {
            throw new StorageException("Failed to store uploaded repository.", exception);
        }

        return new StoredFile(originalFilename, destination.toString());
    }

    public record StoredFile(String originalFilename, String storagePath) {
    }
}
