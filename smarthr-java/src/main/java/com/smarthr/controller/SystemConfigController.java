package com.smarthr.controller;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.smarthr.dto.UnifiedResponse;
import com.smarthr.entity.Job;
import com.smarthr.entity.KnowledgeDocument;
import com.smarthr.entity.RagEvaluationRun;
import com.smarthr.entity.Resume;
import com.smarthr.repository.JobRepository;
import com.smarthr.repository.KnowledgeDocumentRepository;
import com.smarthr.repository.RagEvaluationRunRepository;
import com.smarthr.repository.ResumeRepository;
import com.smarthr.service.KnowledgeService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
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
    private JobRepository jobRepository;

    @Autowired
    private ResumeRepository resumeRepository;

    @Autowired
    private KnowledgeDocumentRepository knowledgeDocumentRepository;

    @Autowired
    private KnowledgeService knowledgeService;

    @Autowired
    private ObjectMapper objectMapper;

    private final RestTemplate restTemplate = new RestTemplate();

    private static final Map<String, Object> llmConfig = new HashMap<>();
    private static boolean llmConfigInitialized = false;

    // 对外返回密钥时的脱敏占位，绝不回传明文 apiKey。
    private static final String API_KEY_MASK = "********";

    @GetMapping("/llm")
    @PreAuthorize("hasRole('ADMIN')")
    public UnifiedResponse<Map<String, Object>> getLlmConfig() {
        if (!llmConfigInitialized) {
            llmConfig.put("baseUrl", "https://api.deepseek.com");
            llmConfig.put("modelName", "deepseek-chat");
            llmConfig.put("apiKey", "");
            llmConfigInitialized = true;
        }
        return UnifiedResponse.success(maskedView());
    }

    @PostMapping("/llm")
    @PreAuthorize("hasRole('ADMIN')")
    public UnifiedResponse<Map<String, Object>> saveLlmConfig(@RequestBody Map<String, Object> config) {
        Map<String, Object> incoming = new HashMap<>(config);
        // 前端回传脱敏占位或空值时，保留已存储的真实密钥，避免把密钥覆盖成掩码。
        Object incomingKey = incoming.get("apiKey");
        if (incomingKey == null || String.valueOf(incomingKey).isBlank()
                || API_KEY_MASK.equals(String.valueOf(incomingKey))) {
            incoming.remove("apiKey");
        }
        llmConfig.putAll(incoming);
        return UnifiedResponse.success(maskedView());
    }

    // 构造脱敏后的配置视图：apiKey 不回传明文，仅返回是否已配置。
    private Map<String, Object> maskedView() {
        Map<String, Object> view = new HashMap<>(llmConfig);
        Object apiKey = view.get("apiKey");
        boolean configured = apiKey != null && !String.valueOf(apiKey).isBlank();
        view.put("apiKey", configured ? API_KEY_MASK : "");
        view.put("apiKeyConfigured", configured);
        return view;
    }

    @PostMapping("/rag-index/rebuild")
    public UnifiedResponse<Map<String, Object>> rebuildRagIndex(@RequestBody(required = false) Map<String, Object> request) {
        try {
            Long companyId = longValue(request != null ? request.get("companyId") : null);
            List<Map<String, Object>> documents = new ArrayList<>();

            List<Job> jobs = companyId != null ? jobRepository.findByCompanyId(companyId) : jobRepository.findAll();
            for (Job job : jobs) {
                String text = buildJobText(job);
                if (text.isBlank()) {
                    continue;
                }
                Map<String, Object> item = new HashMap<>();
                item.put("sourceType", "job");
                item.put("sourceId", String.valueOf(job.getId()));
                item.put("title", job.getTitle());
                item.put("text", text);
                item.put("companyId", job.getCompanyId() != null ? String.valueOf(job.getCompanyId()) : "default");
                item.put("metadata", Map.of(
                        "company_id", job.getCompanyId() != null ? String.valueOf(job.getCompanyId()) : "default",
                        "department", job.getDepartment() != null ? job.getDepartment() : "",
                        "skills", job.getSkills() != null ? job.getSkills() : ""
                ));
                documents.add(item);
            }

            List<Resume> resumes = companyId != null ? resumeRepository.findAllByCompanyId(companyId) : resumeRepository.findAll();
            for (Resume resume : resumes) {
                if (resume.getRawText() == null || resume.getRawText().isBlank()) {
                    continue;
                }
                Map<String, Object> item = new HashMap<>();
                item.put("sourceType", "resume");
                item.put("sourceId", String.valueOf(resume.getId()));
                item.put("title", resume.getCandidateName() != null ? resume.getCandidateName() : "简历 " + resume.getId());
                item.put("text", resume.getRawText());
                item.put("companyId", resume.getCompanyId() != null ? String.valueOf(resume.getCompanyId()) : "default");
                item.put("metadata", Map.of(
                        "company_id", resume.getCompanyId() != null ? String.valueOf(resume.getCompanyId()) : "default",
                        "candidate_name", resume.getCandidateName() != null ? resume.getCandidateName() : "",
                        "job_id", resume.getJobId() != null ? String.valueOf(resume.getJobId()) : "",
                        "parsed_data", resume.getParsedData() != null ? resume.getParsedData() : ""
                ));
                documents.add(item);
            }

            Map<String, Object> body = new HashMap<>();
            body.put("documents", documents);
            ResponseEntity<Map> response = restTemplate.postForEntity(
                    aiServiceUrl + "/api/rag/rebuild",
                    body,
                    Map.class
            );

            Map<String, Object> result = response.getBody() != null ? new HashMap<>(response.getBody()) : new HashMap<>();
            int knowledgeIndexed = 0;
            int knowledgeFailed = 0;
            List<String> knowledgeErrors = new ArrayList<>();
            List<KnowledgeDocument> knowledgeDocuments = companyId != null
                    ? knowledgeDocumentRepository.findAllByCompanyId(companyId)
                    : knowledgeDocumentRepository.findAll();
            for (KnowledgeDocument doc : knowledgeDocuments) {
                try {
                    knowledgeService.reindexDocument(doc.getId());
                    knowledgeIndexed++;
                } catch (Exception e) {
                    knowledgeFailed++;
                    knowledgeErrors.add(doc.getDocumentId() + ": " + e.getMessage());
                }
            }

            result.put("businessDocuments", documents.size());
            result.put("knowledgeIndexed", knowledgeIndexed);
            result.put("knowledgeFailed", knowledgeFailed);
            result.put("knowledgeErrors", knowledgeErrors);
            return UnifiedResponse.success(result);
        } catch (Exception e) {
            return UnifiedResponse.error("RAG 索引重建失败: " + e.getMessage());
        }
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

    private String buildJobText(Job job) {
        StringBuilder sb = new StringBuilder();
        if (job.getTitle() != null) sb.append("岗位：").append(job.getTitle()).append("\n");
        if (job.getDepartment() != null) sb.append("部门：").append(job.getDepartment()).append("\n");
        if (job.getDescription() != null) sb.append("描述：").append(job.getDescription()).append("\n");
        if (job.getRequirements() != null) sb.append("任职要求：").append(job.getRequirements()).append("\n");
        if (job.getSkills() != null) sb.append("技能：").append(job.getSkills()).append("\n");
        if (job.getExperienceYears() != null) sb.append("经验年限：").append(job.getExperienceYears()).append("\n");
        if (job.getEducationLevel() != null) sb.append("学历：").append(job.getEducationLevel()).append("\n");
        return sb.toString();
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

    private Long longValue(Object value) {
        if (value instanceof Number number) {
            return number.longValue();
        }
        if (value != null) {
            try {
                return Long.parseLong(String.valueOf(value));
            } catch (NumberFormatException ignored) {
            }
        }
        return null;
    }
}
