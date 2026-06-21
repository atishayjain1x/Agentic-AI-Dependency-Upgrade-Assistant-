package com.example.dependencyagent.web.dto;

import jakarta.validation.constraints.NotNull;
import java.util.List;

public record CreateFixJobRequest(
        @NotNull String fixBy,
        List<String> dependencyIds,
        String category
) {
}
