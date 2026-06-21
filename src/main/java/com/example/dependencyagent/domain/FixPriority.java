package com.example.dependencyagent.domain;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;
import java.util.Arrays;

public enum FixPriority {
    CRITICAL("critical"),
    HIGH("high"),
    MEDIUM("medium"),
    LOW("low");

    private final String apiValue;

    FixPriority(String apiValue) {
        this.apiValue = apiValue;
    }

    @JsonValue
    public String getApiValue() {
        return apiValue;
    }

    @JsonCreator
    public static FixPriority fromApiValue(String value) {
        return Arrays.stream(values())
                .filter(priority -> priority.apiValue.equalsIgnoreCase(value))
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("Unsupported priority: " + value));
    }
}
