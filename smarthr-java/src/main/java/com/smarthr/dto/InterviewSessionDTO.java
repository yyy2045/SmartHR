package com.smarthr.dto;

import lombok.Data;
import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

@Data
public class InterviewSessionDTO {
    private String sessionId;
    private Long jobId;
    private Long resumeId;
    private String status;
    private String currentAgent;
    private Integer questionsAsked;
    private boolean complete;
    private Map<String, Object> currentQuestion;
    private List<Map<String, Object>> history;
    private Map<String, Object> skillScores;
    private Map<String, Object> behaviorScores;
    private String candidateName;
    private String jobTitle;
}