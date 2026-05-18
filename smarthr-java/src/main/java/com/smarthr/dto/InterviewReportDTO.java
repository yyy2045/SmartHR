package com.smarthr.dto;

import lombok.Data;
import lombok.Builder;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import java.math.BigDecimal;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class InterviewReportDTO {
    private String sessionId;
    private BigDecimal overallScore;
    private BigDecimal skillScore;
    private BigDecimal behaviorScore;
    private String recommendation;
    private String summary;
    private List<String> strengths;
    private List<String> concerns;
    private List<String> interviewHighlights;
}