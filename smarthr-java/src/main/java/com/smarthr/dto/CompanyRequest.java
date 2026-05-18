package com.smarthr.dto;

import lombok.Data;
import jakarta.validation.constraints.NotBlank;

@Data
public class CompanyRequest {
    @NotBlank(message = "Company name is required")
    private String name;

    private String industry;

    private String description;
}