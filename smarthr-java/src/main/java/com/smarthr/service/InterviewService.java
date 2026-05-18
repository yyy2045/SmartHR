package com.smarthr.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.smarthr.dto.*;
import com.smarthr.entity.InterviewReport;
import com.smarthr.entity.InterviewSession;
import com.smarthr.repository.InterviewReportRepository;
import com.smarthr.repository.InterviewSessionRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.math.BigDecimal;
import java.util.*;

@Service
public class InterviewService {

    @Value("${ai.service.url}")
    private String pythonServiceUrl;

    @Autowired
    private InterviewSessionRepository sessionRepository;

    @Autowired
    private InterviewReportRepository reportRepository;

    @Autowired
    private ObjectMapper objectMapper;

    private final RestTemplate restTemplate = new RestTemplate();

    public InterviewSessionDTO createSession(CreateInterviewRequest request, Long userId) {
        String url = pythonServiceUrl + "/api/interview/sessions";

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);

        Map<String, Object> body = new HashMap<>();
        body.put("job_id", request.getJobId().toString());
        body.put("resume_id", request.getResumeId().toString());
        body.put("job_description", request.getJobDescription());
        body.put("resume_text", request.getResumeText());

        HttpEntity<Map<String, Object>> entity = new HttpEntity<>(body, headers);

        ResponseEntity<Map> response = restTemplate.postForEntity(url, entity, Map.class);

        if (response.getStatusCode() == HttpStatus.OK && response.getBody() != null) {
            Map<String, Object> body_response = response.getBody();

            // Save session to MySQL
            InterviewSession session = new InterviewSession();
            session.setSessionId((String) body_response.get("session_id"));
            session.setJobId(request.getJobId());
            session.setResumeId(request.getResumeId());
            session.setUserId(userId);
            session.setStatus("IN_PROGRESS");
            session = sessionRepository.save(session);

            // Return DTO
            InterviewSessionDTO dto = new InterviewSessionDTO();
            dto.setSessionId((String) body_response.get("session_id"));
            dto.setJobId(request.getJobId());
            dto.setResumeId(request.getResumeId());
            dto.setStatus("IN_PROGRESS");
            dto.setComplete(false);

            Map<String, Object> question = (Map<String, Object>) body_response.get("question");
            dto.setCurrentQuestion(question);

            return dto;
        }

        throw new RuntimeException("Failed to create interview session");
    }

    public InterviewSessionDTO sendMessage(String sessionId, String message) {
        String url = pythonServiceUrl + "/api/interview/sessions/" + sessionId + "/message";

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);

        Map<String, String> body = new HashMap<>();
        body.put("message", message);

        HttpEntity<Map<String, String>> entity = new HttpEntity<>(body, headers);

        ResponseEntity<Map> response = restTemplate.postForEntity(url, entity, Map.class);

        if (response.getStatusCode() == HttpStatus.OK && response.getBody() != null) {
            Map<String, Object> body_response = response.getBody();

            InterviewSessionDTO dto = new InterviewSessionDTO();
            dto.setSessionId(sessionId);
            dto.setStatus((String) body_response.get("status"));
            dto.setComplete((Boolean) body_response.get("is_complete"));

            Map<String, Object> question = (Map<String, Object>) body_response.get("question");
            dto.setCurrentQuestion(question);

            return dto;
        }

        throw new RuntimeException("Failed to send message");
    }

    public InterviewReportDTO endSession(String sessionId) {
        String url = pythonServiceUrl + "/api/interview/sessions/" + sessionId + "/end";

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);

        HttpEntity<Void> entity = new HttpEntity<>(headers);

        ResponseEntity<Map> response = restTemplate.postForEntity(url, entity, Map.class);

        if (response.getStatusCode() == HttpStatus.OK && response.getBody() != null) {
            Map<String, Object> body_response = response.getBody();
            Map<String, Object> report_map = (Map<String, Object>) body_response.get("report");

            // Save report to MySQL
            InterviewReport report = new InterviewReport();
            report.setSessionId(sessionRepository.findBySessionId(sessionId)
                    .map(InterviewSession::getId)
                    .orElse(null));
            report.setOverallScore(toBigDecimal(report_map.get("overall_score")));
            report.setSkillScore(toBigDecimal(report_map.get("skill_score")));
            report.setBehaviorScore(toBigDecimal(report_map.get("behavior_score")));
            report.setRecommendation((String) report_map.get("recommendation"));
            report.setSummary((String) report_map.get("summary"));

            try {
                report.setReportData(objectMapper.writeValueAsString(report_map));
            } catch (Exception e) {
                report.setReportData("{}");
            }

            reportRepository.save(report);

            // Update session status
            sessionRepository.findBySessionId(sessionId).ifPresent(session -> {
                session.setStatus("COMPLETED");
                sessionRepository.save(session);
            });

            // Build DTO
            InterviewReportDTO dto = new InterviewReportDTO();
            dto.setSessionId(sessionId);
            dto.setOverallScore(report.getOverallScore());
            dto.setSkillScore(report.getSkillScore());
            dto.setBehaviorScore(report.getBehaviorScore());
            dto.setRecommendation(report.getRecommendation());
            dto.setSummary(report.getSummary());

            @SuppressWarnings("unchecked")
            List<String> strengths = (List<String>) report_map.get("strengths");
            dto.setStrengths(strengths != null ? strengths : Collections.emptyList());

            @SuppressWarnings("unchecked")
            List<String> concerns = (List<String>) report_map.get("concerns");
            dto.setConcerns(concerns != null ? concerns : Collections.emptyList());

            return dto;
        }

        throw new RuntimeException("Failed to end interview session");
    }

    public InterviewReportDTO getReport(String sessionId) {
        String url = pythonServiceUrl + "/api/interview/sessions/" + sessionId + "/report";

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);

        HttpEntity<Void> entity = new HttpEntity<>(headers);

        ResponseEntity<Map> response = restTemplate.postForEntity(url, entity, Map.class);

        if (response.getStatusCode() == HttpStatus.OK && response.getBody() != null) {
            Map<String, Object> report_map = response.getBody();

            InterviewReportDTO dto = new InterviewReportDTO();
            dto.setSessionId(sessionId);
            dto.setOverallScore(toBigDecimal(report_map.get("overall_score")));
            dto.setSkillScore(toBigDecimal(report_map.get("skill_score")));
            dto.setBehaviorScore(toBigDecimal(report_map.get("behavior_score")));
            dto.setRecommendation((String) report_map.get("recommendation"));
            dto.setSummary((String) report_map.get("summary"));

            @SuppressWarnings("unchecked")
            List<String> strengths = (List<String>) report_map.get("strengths");
            dto.setStrengths(strengths != null ? strengths : Collections.emptyList());

            @SuppressWarnings("unchecked")
            List<String> concerns = (List<String>) report_map.get("concerns");
            dto.setConcerns(concerns != null ? concerns : Collections.emptyList());

            return dto;
        }

        throw new RuntimeException("Failed to get interview report");
    }

    public Map<String, Object> getSessionStatus(String sessionId) {
        String url = pythonServiceUrl + "/api/interview/sessions/" + sessionId + "/status";

        HttpHeaders headers = new HttpHeaders();
        HttpEntity<Void> entity = new HttpEntity<>(headers);

        ResponseEntity<Map> response = restTemplate.getForEntity(url, Map.class);

        if (response.getStatusCode() == HttpStatus.OK && response.getBody() != null) {
            return response.getBody();
        }

        throw new RuntimeException("Failed to get session status");
    }

    public InterviewSessionDTO resumeSession(String sessionId) {
        String url = pythonServiceUrl + "/api/interview/sessions/" + sessionId + "/resume";

        HttpHeaders headers = new HttpHeaders();
        HttpEntity<Void> entity = new HttpEntity<>(headers);

        ResponseEntity<Map> response = restTemplate.postForEntity(url, entity, Map.class);

        if (response.getStatusCode() == HttpStatus.OK && response.getBody() != null) {
            Map<String, Object> body = response.getBody();

            InterviewSessionDTO dto = new InterviewSessionDTO();
            dto.setSessionId(sessionId);
            dto.setStatus((String) body.get("status"));

            @SuppressWarnings("unchecked")
            Map<String, Object> question = (Map<String, Object>) body.get("current_question");
            dto.setCurrentQuestion(question);

            Integer questionsAsked = (Integer) body.get("questions_asked");
            dto.setQuestionsAsked(questionsAsked);

            return dto;
        }

        throw new RuntimeException("Failed to resume session");
    }

    private BigDecimal toBigDecimal(Object value) {
        if (value == null) return BigDecimal.ZERO;
        if (value instanceof BigDecimal) return (BigDecimal) value;
        if (value instanceof Number) return BigDecimal.valueOf(((Number) value).doubleValue());
        try {
            return new BigDecimal(value.toString());
        } catch (NumberFormatException e) {
            return BigDecimal.ZERO;
        }
    }
}