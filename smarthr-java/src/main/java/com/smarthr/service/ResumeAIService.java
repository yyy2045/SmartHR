package com.smarthr.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.smarthr.dto.ParsedResumeDTO;
import com.smarthr.dto.MatchResultDTO;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.multipart.MultipartFile;

import java.util.HashMap;
import java.util.Map;

@Service
public class ResumeAIService {

    @Value("${ai.service.url}")
    private String pythonServiceUrl;

    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper;

    public ResumeAIService() {
        this.restTemplate = new RestTemplate();
        this.objectMapper = new ObjectMapper();
    }

    public ParsedResumeDTO parseResume(String rawText) {
        String url = pythonServiceUrl + "/api/resume/parse";

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);

        Map<String, String> body = new HashMap<>();
        body.put("raw_text", rawText);

        HttpEntity<Map<String, String>> request = new HttpEntity<>(body, headers);

        ResponseEntity<String> response = restTemplate.postForEntity(url, request, String.class);

        if (response.getStatusCode() == HttpStatus.OK && response.getBody() != null) {
            try {
                JsonNode root = objectMapper.readTree(response.getBody());
                JsonNode data = root.get("data");
                return objectMapper.treeToValue(data, ParsedResumeDTO.class);
            } catch (Exception e) {
                throw new RuntimeException("Failed to parse resume response", e);
            }
        }

        throw new RuntimeException("Failed to parse resume: " + response.getStatusCode());
    }

    public MatchResultDTO matchResume(Long resumeId, Long jobId, String resumeText) {
        return matchResume(resumeId, jobId, resumeText, null, null);
    }

    public MatchResultDTO matchResume(Long resumeId, Long jobId, String resumeText,
                                      String jobText, String parsedResumeJson) {
        String url = pythonServiceUrl + "/api/resume/match";

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);

        Map<String, Object> body = new HashMap<>();
        body.put("resume_id", resumeId.toString());
        body.put("job_id", jobId.toString());
        body.put("resume_text", resumeText);
        if (jobText != null && !jobText.isEmpty()) {
            body.put("job_text", jobText);
        }
        if (parsedResumeJson != null && !parsedResumeJson.isEmpty()) {
            try {
                body.put("parsed_resume", objectMapper.readTree(parsedResumeJson));
            } catch (Exception ignore) {}
        }

        HttpEntity<Map<String, Object>> request = new HttpEntity<>(body, headers);

        ResponseEntity<String> response = restTemplate.postForEntity(url, request, String.class);

        if (response.getStatusCode() == HttpStatus.OK && response.getBody() != null) {
            try {
                JsonNode root = objectMapper.readTree(response.getBody());
                MatchResultDTO result = new MatchResultDTO();
                result.setResumeId(resumeId);
                result.setJobId(jobId);
                result.setMatchScore(root.has("match_score") ? root.get("match_score").asDouble() : 0.0);
                result.setSummary(root.has("summary") ? root.get("summary").asText() : "");
                if (root.has("matching_points") && root.get("matching_points").isArray()) {
                    result.setMatchingPoints(objectMapper.convertValue(
                        root.get("matching_points"),
                        new com.fasterxml.jackson.core.type.TypeReference<java.util.List<java.util.Map<String, Object>>>() {}
                    ));
                }
                if (root.has("risk_points") && root.get("risk_points").isArray()) {
                    result.setRiskPoints(objectMapper.convertValue(
                        root.get("risk_points"),
                        new com.fasterxml.jackson.core.type.TypeReference<java.util.List<java.util.Map<String, Object>>>() {}
                    ));
                }
                return result;
            } catch (Exception e) {
                throw new RuntimeException("Failed to parse match response", e);
            }
        }

        throw new RuntimeException("Failed to match resume: " + response.getStatusCode());
    }

    public String uploadAndParseResume(MultipartFile file) {
        String url = pythonServiceUrl + "/api/resume/upload";

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);

        org.springframework.util.MultiValueMap<String, Object> body
            = new org.springframework.util.LinkedMultiValueMap<>();
        body.add("file", file.getResource());

        HttpEntity<org.springframework.util.MultiValueMap<String, Object>> requestEntity
            = new HttpEntity<>(body, headers);

        ResponseEntity<String> response = restTemplate.postForEntity(
            url, requestEntity, String.class);

        if (response.getStatusCode() == HttpStatus.OK && response.getBody() != null) {
            return response.getBody();
        }

        throw new RuntimeException("Failed to upload resume: " + response.getStatusCode());
    }

    /**
     * 从已保存到磁盘的文件重新调用 Python 服务提取 rawText（用于补救历史无 rawText 的简历）
     */
    public String extractRawTextFromFile(java.io.File file) {
        String url = pythonServiceUrl + "/api/resume/upload";

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);

        org.springframework.core.io.FileSystemResource resource = new org.springframework.core.io.FileSystemResource(file);
        org.springframework.util.MultiValueMap<String, Object> body
            = new org.springframework.util.LinkedMultiValueMap<>();
        body.add("file", resource);

        HttpEntity<org.springframework.util.MultiValueMap<String, Object>> requestEntity
            = new HttpEntity<>(body, headers);

        ResponseEntity<String> response = restTemplate.postForEntity(
            url, requestEntity, String.class);

        if (response.getStatusCode() == HttpStatus.OK && response.getBody() != null) {
            try {
                JsonNode root = objectMapper.readTree(response.getBody());
                return root.has("raw_text") ? root.get("raw_text").asText() : "";
            } catch (Exception e) {
                throw new RuntimeException("Failed to parse upload response", e);
            }
        }

        throw new RuntimeException("Failed to extract raw text: " + response.getStatusCode());
    }
}