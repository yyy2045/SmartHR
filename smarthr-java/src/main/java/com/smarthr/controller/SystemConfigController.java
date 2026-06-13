package com.smarthr.controller;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.smarthr.dto.UnifiedResponse;
import com.smarthr.entity.RagEvaluationRun;
import com.smarthr.repository.RagEvaluationRunRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;

import java.math.BigDecimal;
import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/config")
public class SystemConfigController {

    @Value("${ai.service.url:http://localhost:8001}")
    private String aiServiceUrl;

    @Autowired
    private RagEvaluationRunRepository ragEvaluationRunRepository;

    @Autowired
    private ObjectMapper objectMapper;

    private final RestTemplate restTemplate = new RestTemplate();

    private static final Map<String, Object> llmConfig = new HashMap<>();
    private static boolean llmConfigInitialized = false;

    @GetMapping("/llm")
    public UnifiedResponse<Map<String, Object>> getLlmConfig() {
        if (!llmConfigInitialized) {
            llmConfig.put("baseUrl", "https://api.deepseek.com");
            llmConfig.put("modelName", "deepseek-chat");
            llmConfig.put("apiKey", "");
            llmConfigInitialized = true;
        }
        return UnifiedResponse.success(new HashMap<>(llmConfig));
    }

    @PostMapping("/llm")
    public UnifiedResponse<Map<String, Object>> saveLlmConfig(@RequestBody Map<String, Object> config) {
        llmConfig.putAll(config);
        return UnifiedResponse.success(new HashMap<>(llmConfig));
    }

    @PostMapping("/rag-evaluation/run")
    public UnifiedResponse<Map<String, Object>> runRagEvaluation(@RequestBody(required = false) Map<String, Object> request) {
        try {
            Map<String, Object> body = request != null ? request : new HashMap<>();
            ResponseEntity<Map> response = restTemplate.postForEntity(
                    aiServiceUrl + "/api/rag/evaluations/run",
                    body,
                    Map.class
            );
            if (!response.getStatusCode().is2xxSuccessful() || response.getBody() == null) {
                return UnifiedResponse.error("RAG 评测服务无响应");
            }
            @SuppressWarnings("unchecked")
            Map<String, Object> result = response.getBody();
            RagEvaluationRun saved = saveEvaluationRun(result);
            return UnifiedResponse.success(toResponse(saved));
        } catch (Exception e) {
            return UnifiedResponse.error("RAG 评测失败: " + e.getMessage());
        }
    }

    @GetMapping("/rag-evaluation")
    public UnifiedResponse<Map<String, Object>> getLatestRagEvaluation() {
        return ragEvaluationRunRepository.findTopByOrderByCreatedAtDesc()
                .map(run -> UnifiedResponse.success(toResponse(run)))
                .orElseGet(() -> {
                    Map<String, Object> empty = new HashMap<>();
                    empty.put("status", "empty");
                    empty.put("message", "暂无 RAG 评测记录");
                    return UnifiedResponse.success(empty);
                });
    }

    private RagEvaluationRun saveEvaluationRun(Map<String, Object> result) throws Exception {
        RagEvaluationRun run = new RagEvaluationRun();
        run.setRunId(stringValue(result.get("runId")));
        run.setStatus(stringValue(result.get("status")));
        run.setEvaluator(stringValue(result.get("evaluator")));
        run.setThresholdScore(decimalValue(result.get("threshold")));
        run.setSampleCount(intValue(result.get("sampleCount")));
        run.setMetrics(toJson(result.get("metrics")));
        run.setFailedSamples(toJson(result.get("failedSamples")));
        run.setSampleResults(toJson(result.get("sampleResults")));
        run.setNotes(stringValue(result.get("notes")));
        run.setStartedAt(stringValue(result.get("startedAt")));
        run.setCompletedAt(stringValue(result.get("completedAt")));
        return ragEvaluationRunRepository.save(run);
    }

    private Map<String, Object> toResponse(RagEvaluationRun run) {
        Map<String, Object> response = new HashMap<>();
        response.put("id", run.getId());
        response.put("runId", run.getRunId());
        response.put("status", run.getStatus());
        response.put("evaluator", run.getEvaluator());
        response.put("threshold", run.getThresholdScore());
        response.put("sampleCount", run.getSampleCount());
        response.put("metrics", fromJson(run.getMetrics()));
        response.put("failedSamples", fromJson(run.getFailedSamples()));
        response.put("sampleResults", fromJson(run.getSampleResults()));
        response.put("notes", run.getNotes());
        response.put("startedAt", run.getStartedAt());
        response.put("completedAt", run.getCompletedAt());
        response.put("createdAt", run.getCreatedAt());
        return response;
    }

    private String toJson(Object value) throws Exception {
        return objectMapper.writeValueAsString(value);
    }

    private Object fromJson(String json) {
        if (json == null || json.isBlank()) {
            return null;
        }
        try {
            return objectMapper.readValue(json, new TypeReference<Object>() {});
        } catch (Exception e) {
            return null;
        }
    }

    private String stringValue(Object value) {
        return value != null ? String.valueOf(value) : null;
    }

    private BigDecimal decimalValue(Object value) {
        if (value instanceof Number number) {
            return BigDecimal.valueOf(number.doubleValue());
        }
        if (value != null) {
            try {
                return new BigDecimal(String.valueOf(value));
            } catch (NumberFormatException ignored) {
            }
        }
        return BigDecimal.ZERO;
    }

    private Integer intValue(Object value) {
        if (value instanceof Number number) {
            return number.intValue();
        }
        if (value != null) {
            try {
                return Integer.parseInt(String.valueOf(value));
            } catch (NumberFormatException ignored) {
            }
        }
        return 0;
    }
}
