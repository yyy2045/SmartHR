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
        String url = pythonServiceUrl + "/api/resume/match";

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);

        Map<String, Object> body = new HashMap<>();
        body.put("resume_id", resumeId.toString());
        body.put("job_id", jobId.toString());
        body.put("resume_text", resumeText);

        HttpEntity<Map<String, Object>> request = new HttpEntity<>(body, headers);

        ResponseEntity<String> response = restTemplate.postForEntity(url, request, String.class);

        if (response.getStatusCode() == HttpStatus.OK && response.getBody() != null) {
            try {
                JsonNode root = objectMapper.readTree(response.getBody());
                MatchResultDTO result = new MatchResultDTO();
                result.setResumeId(resumeId);
                result.setJobId(jobId);
                result.setMatchScore(root.get("match_score").asDouble());
                result.setSummary(root.has("summary") ? root.get("summary").asText() : "");
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
}