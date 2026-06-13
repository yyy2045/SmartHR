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
    private List<String> matchedSkills;
    private List<String> missingSkills;
    private List<String> risks;
    private List<Map<String, Object>> evidence;
    private String traceId;
    private Map<String, Object> retrievalScores;
    private List<Map<String, Object>> rankScores;
}
