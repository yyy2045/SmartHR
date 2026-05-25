package com.smarthr.dto;

import lombok.Data;

@Data
public class CreateInterviewRequest {
    private Long jobId;
    private Long resumeId;
    private Long companyId;
    private String jobDescription;
    private String resumeText;
}