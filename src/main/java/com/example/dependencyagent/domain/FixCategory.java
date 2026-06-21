package com.example.dependencyagent.domain;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;
import java.util.Arrays;

public enum FixCategory {
    VERSION_BUMP("version_bump"),
    PARENT_UPGRADE("parentUpgrade");

    private final String apiValue;

    FixCategory(String apiValue) {
        this.apiValue = apiValue;
    }

    @JsonValue
    public String getApiValue() {
        return apiValue;
    }

    @JsonCreator
    public static FixCategory fromApiValue(String value) {
        return Arrays.stream(values())
                .filter(category -> category.apiValue.equalsIgnoreCase(value))
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("Unsupported category: " + value));
    }
}
