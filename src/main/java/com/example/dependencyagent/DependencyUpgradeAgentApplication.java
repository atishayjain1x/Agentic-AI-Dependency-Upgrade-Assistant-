package com.example.dependencyagent;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;

@SpringBootApplication
@ConfigurationPropertiesScan
public class DependencyUpgradeAgentApplication {

    public static void main(String[] args) {
        SpringApplication.run(DependencyUpgradeAgentApplication.class, args);
    }
}
