package com.smarthr.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.smarthr.dto.*;
import com.smarthr.entity.InterviewReport;
import com.smarthr.entity.InterviewSession;
import com.smarthr.entity.Job;
import com.smarthr.entity.Resume;
import com.smarthr.repository.InterviewReportRepository;
import com.smarthr.repository.InterviewSessionRepository;
import com.smarthr.repository.JobRepository;
import com.smarthr.repository.ResumeRepository;
import jakarta.annotation.PostConstruct;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.web.client.RestTemplateBuilder;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestTemplate;

import java.math.BigDecimal;
import java.time.Duration;
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
    private JobRepository jobRepository;

    @Autowired
    private ResumeRepository resumeRepository;

    @Autowired
    private ObjectMapper objectMapper;

    private RestTemplate restTemplate;

    @PostConstruct
    public void initRestTemplate() {
        // Python 端的 LLM 调用最长 120s，这里设为 180s 给总超时留余量
        this.restTemplate = new RestTemplateBuilder()
                .setConnectTimeout(Duration.ofSeconds(10))
                .setReadTimeout(Duration.ofSeconds(180))
                .build();
    }

    public InterviewSessionDTO createSession(CreateInterviewRequest request, Long userId) {
        if (request == null || request.getJobId() == null || request.getResumeId() == null) {
            throw new RuntimeException("jobId 和 resumeId 不能为空");
        }

        // 自动从数据库补充 jobDescription / resumeText（前端通常只传 ID）
        String jobDescription = request.getJobDescription();
        if (jobDescription == null || jobDescription.isEmpty()) {
            jobDescription = jobRepository.findById(request.getJobId())
                    .map(this::buildJobDescription)
                    .orElse("");
        }
        String resumeText = request.getResumeText();
        if (resumeText == null || resumeText.isEmpty()) {
            resumeText = resumeRepository.findById(request.getResumeId())
                    .map(Resume::getRawText)
                    .orElse("");
        }

        String url = pythonServiceUrl + "/api/interview/sessions";

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);

        Map<String, Object> body = new HashMap<>();
        body.put("job_id", request.getJobId().toString());
        body.put("resume_id", request.getResumeId().toString());
        body.put("job_description", jobDescription);
        body.put("resume_text", resumeText);
        if (request.getCompanyId() != null) {
            body.put("company_id", request.getCompanyId().toString());
        }

        HttpEntity<Map<String, Object>> entity = new HttpEntity<>(body, headers);

        Map<String, Object> body_response;
        try {
            ResponseEntity<Map> response = restTemplate.postForEntity(url, entity, Map.class);
            if (response.getStatusCode() != HttpStatus.OK || response.getBody() == null) {
                throw new RuntimeException("AI 服务返回异常状态: " + response.getStatusCode());
            }
            body_response = response.getBody();
        } catch (ResourceAccessException e) {
            throw new RuntimeException("无法连接 AI 服务（请检查 Python 服务是否启动 / 网络是否通畅）: " + e.getMessage());
        } catch (RestClientException e) {
            throw new RuntimeException("调用 AI 服务失败: " + e.getMessage());
        }

        String returnedSessionId = (String) body_response.get("session_id");
        if (returnedSessionId == null || returnedSessionId.isEmpty()) {
            throw new RuntimeException("AI 服务未返回 session_id");
        }

        // Save session to MySQL
        InterviewSession session = new InterviewSession();
        session.setSessionId(returnedSessionId);
        session.setJobId(request.getJobId());
        session.setResumeId(request.getResumeId());
        session.setUserId(userId);
        session.setStatus("IN_PROGRESS");
        sessionRepository.save(session);

        // Return DTO
        InterviewSessionDTO dto = new InterviewSessionDTO();
        dto.setSessionId(returnedSessionId);
        dto.setJobId(request.getJobId());
        dto.setResumeId(request.getResumeId());
        dto.setStatus("IN_PROGRESS");
        dto.setComplete(false);

        @SuppressWarnings("unchecked")
        Map<String, Object> question = (Map<String, Object>) body_response.get("question");
        dto.setCurrentQuestion(question);

        return dto;
    }

    private String buildJobDescription(Job job) {
        StringBuilder sb = new StringBuilder();
        if (job.getTitle() != null) sb.append("岗位：").append(job.getTitle()).append("\n");
        if (job.getDescription() != null) sb.append("描述：").append(job.getDescription()).append("\n");
        if (job.getRequirements() != null) sb.append("任职要求：").append(job.getRequirements()).append("\n");
        if (job.getSkills() != null) sb.append("技能：").append(job.getSkills()).append("\n");
        return sb.toString();
    }

    public InterviewSessionDTO sendMessage(String sessionId, String message) {
        String url = pythonServiceUrl + "/api/interview/sessions/" + sessionId + "/message";

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);

        Map<String, String> body = new HashMap<>();
        body.put("message", message);

        HttpEntity<Map<String, String>> entity = new HttpEntity<>(body, headers);

        Map<String, Object> body_response;
        try {
            ResponseEntity<Map> response = restTemplate.postForEntity(url, entity, Map.class);
            if (response.getStatusCode() != HttpStatus.OK || response.getBody() == null) {
                throw new RuntimeException("AI 服务返回异常状态: " + response.getStatusCode());
            }
            body_response = response.getBody();
        } catch (ResourceAccessException e) {
            throw new RuntimeException("无法连接 AI 服务: " + e.getMessage());
        } catch (RestClientException e) {
            throw new RuntimeException("调用 AI 服务失败: " + e.getMessage());
        }

        InterviewSessionDTO dto = new InterviewSessionDTO();
        dto.setSessionId(sessionId);
        dto.setStatus((String) body_response.getOrDefault("status", "IN_PROGRESS"));
        Object completeObj = body_response.get("is_complete");
        dto.setComplete(completeObj instanceof Boolean ? (Boolean) completeObj : false);

        @SuppressWarnings("unchecked")
        Map<String, Object> question = (Map<String, Object>) body_response.get("question");
        dto.setCurrentQuestion(question);

        @SuppressWarnings("unchecked")
        Map<String, Object> skillScores = (Map<String, Object>) body_response.get("skillScores");
        if (skillScores != null) dto.setSkillScores(skillScores);

        @SuppressWarnings("unchecked")
        Map<String, Object> behaviorScores = (Map<String, Object>) body_response.get("behaviorScores");
        if (behaviorScores != null) dto.setBehaviorScores(behaviorScores);

        // 如果 Python 端已标记完成，同步更新 MySQL session 状态
        if (dto.isComplete()) {
            sessionRepository.findBySessionId(sessionId).ifPresent(s -> {
                s.setStatus("COMPLETED");
                sessionRepository.save(s);
            });
        }

        return dto;
    }

    public InterviewReportDTO endSession(String sessionId) {
        String url = pythonServiceUrl + "/api/interview/sessions/" + sessionId + "/end";

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);

        HttpEntity<Void> entity = new HttpEntity<>(headers);

        ResponseEntity<Map> response = restTemplate.postForEntity(url, entity, Map.class);

        if (response.getStatusCode() == HttpStatus.OK && response.getBody() != null) {
            Map<String, Object> body_response = response.getBody();
            @SuppressWarnings("unchecked")
            Map<String, Object> report_map = (Map<String, Object>) body_response.get("report");
            if (report_map == null) {
                throw new RuntimeException("AI 服务未返回 report 数据");
            }

            // Save report to MySQL
            InterviewReport report = new InterviewReport();
            Long dbSessionId = sessionRepository.findBySessionId(sessionId)
                    .map(InterviewSession::getId)
                    .orElse(null);
            if (dbSessionId == null) {
                throw new RuntimeException("面试会话不存在: " + sessionId);
            }
            report.setSessionId(dbSessionId);
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

            Object strengthsEndObj = report_map.get("strengths");
            dto.setStrengths(strengthsEndObj instanceof List ? (List<String>) strengthsEndObj : Collections.emptyList());

            Object concernsEndObj = report_map.get("concerns");
            dto.setConcerns(concernsEndObj instanceof List ? (List<String>) concernsEndObj : Collections.emptyList());

            return dto;
        }

        throw new RuntimeException("Failed to end interview session");
    }

    public InterviewReportDTO getReport(String sessionId) {
        String url = pythonServiceUrl + "/api/interview/sessions/" + sessionId + "/report";

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);

        HttpEntity<Void> entity = new HttpEntity<>(headers);

        ResponseEntity<Map> response;
        try {
            response = restTemplate.exchange(url, HttpMethod.GET, entity, Map.class);
        } catch (HttpClientErrorException.NotFound e) {
            throw new RuntimeException("面试报告不存在（会话可能未结束）");
        } catch (RestClientException e) {
            throw new RuntimeException("调用 AI 服务失败: " + e.getMessage());
        }

        if (response.getStatusCode() == HttpStatus.OK && response.getBody() != null) {
            Map<String, Object> report_map = response.getBody();

            InterviewReportDTO dto = new InterviewReportDTO();
            dto.setSessionId(sessionId);
            dto.setOverallScore(toBigDecimal(report_map.get("overall_score")));
            dto.setSkillScore(toBigDecimal(report_map.get("skill_score")));
            dto.setBehaviorScore(toBigDecimal(report_map.get("behavior_score")));
            dto.setRecommendation((String) report_map.get("recommendation"));
            dto.setSummary((String) report_map.get("summary"));

            Object strengthsObj = report_map.get("strengths");
            dto.setStrengths(strengthsObj instanceof List ? (List<String>) strengthsObj : Collections.emptyList());

            Object concernsObj = report_map.get("concerns");
            dto.setConcerns(concernsObj instanceof List ? (List<String>) concernsObj : Collections.emptyList());

            Object highlightsObj = report_map.get("interview_highlights");
            dto.setInterviewHighlights(highlightsObj instanceof List ? (List<String>) highlightsObj : Collections.emptyList());

            Object skillScoresObj = report_map.get("skillScores");
            if (skillScoresObj instanceof Map) {
                @SuppressWarnings("unchecked")
                Map<String, Number> skillScoresMap = (Map<String, Number>) skillScoresObj;
                dto.setSkillScores(toDecimalMap(skillScoresMap));
            }

            Object behaviorScoresObj = report_map.get("behaviorScores");
            if (behaviorScoresObj instanceof Map) {
                @SuppressWarnings("unchecked")
                Map<String, Number> behaviorScoresMap = (Map<String, Number>) behaviorScoresObj;
                dto.setBehaviorScores(toDecimalMap(behaviorScoresMap));
            }

            Object qaSummaryObj = report_map.get("qaSummary");
            dto.setQaSummary(qaSummaryObj instanceof List ? (List<String>) qaSummaryObj : Collections.emptyList());

            return dto;
        }

        throw new RuntimeException("Failed to get interview report");
    }

    public InterviewSessionDTO getSessionStatus(String sessionId) {
        String url = pythonServiceUrl + "/api/interview/sessions/" + sessionId;

        HttpHeaders headers = new HttpHeaders();
        HttpEntity<Void> entity = new HttpEntity<>(headers);

        ResponseEntity<Map> response = restTemplate.exchange(url, HttpMethod.GET, entity, Map.class);

        if (response.getStatusCode() == HttpStatus.OK && response.getBody() != null) {
            Map<String, Object> body = response.getBody();

            InterviewSessionDTO dto = new InterviewSessionDTO();
            dto.setSessionId(sessionId);
            dto.setStatus(body.get("status") != null ? (String) body.get("status") : "UNKNOWN");

            @SuppressWarnings("unchecked")
            Map<String, Object> question = (Map<String, Object>) body.get("current_question");
            dto.setCurrentQuestion(question);

            Integer questionsAsked = (Integer) body.get("questions_asked");
            dto.setQuestionsAsked(questionsAsked);

            Boolean isComplete = (Boolean) body.get("is_complete");
            dto.setComplete(isComplete != null ? isComplete : false);

            @SuppressWarnings("unchecked")
            List<Map<String, Object>> history = (List<Map<String, Object>>) body.get("history");
            dto.setHistory(history != null ? history : Collections.emptyList());

            @SuppressWarnings("unchecked")
            Map<String, Object> skillScoresMap = (Map<String, Object>) body.get("skill_scores");
            if (skillScoresMap != null) dto.setSkillScores(skillScoresMap);

            @SuppressWarnings("unchecked")
            Map<String, Object> behaviorScoresMap = (Map<String, Object>) body.get("behavior_scores");
            if (behaviorScoresMap != null) dto.setBehaviorScores(behaviorScoresMap);

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

    private Map<String, BigDecimal> toDecimalMap(Map<String, Number> map) {
        if (map == null) return Collections.emptyMap();
        Map<String, BigDecimal> result = new HashMap<>();
        for (Map.Entry<String, Number> entry : map.entrySet()) {
            result.put(entry.getKey(), entry.getValue() != null
                    ? BigDecimal.valueOf(entry.getValue().doubleValue())
                    : BigDecimal.ZERO);
        }
        return result;
    }
}