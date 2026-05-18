package com.smarthr.dto;

import lombok.Data;
import jakarta.validation.constraints.NotBlank;

@Data
public class JobRequest {
    @NotBlank(message = "Title is required")
    private String title;

    private String description;

    private String requirements;

    private Long companyId;

    private String skills;

    private Integer experienceYears;

    private String educationLevel;

    private String status;
}