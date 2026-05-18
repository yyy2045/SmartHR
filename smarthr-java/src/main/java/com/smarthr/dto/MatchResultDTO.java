package com.smarthr.dto;

import lombok.Data;
import java.util.List;
import java.util.Map;

@Data
public class MatchResultDTO {
    private Long resumeId;
    private Long jobId;
    private Double matchScore;
    private String summary;
    private List<Map<String, Object>> matchingPoints;
    private List<Map<String, Object>> riskPoints;
}