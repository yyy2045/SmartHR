package com.smarthr.controller;

import com.smarthr.dto.JobRequest;
import com.smarthr.dto.UnifiedResponse;
import com.smarthr.entity.Job;
import com.smarthr.service.JobService;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;

import java.util.*;

@RestController
@RequestMapping("/api/jobs")
public class JobController {

    @Autowired
    private JobService jobService;

    @Value("${ai.service.url}")
    private String pythonServiceUrl;

    private final RestTemplate restTemplate = new RestTemplate();

    @PostMapping
    public UnifiedResponse<Job> create(@Valid @RequestBody JobRequest request) {
        Job job = new Job();
        job.setTitle(request.getTitle());
        job.setDescription(request.getDescription());
        job.setRequirements(request.getRequirements());
        job.setCompanyId(request.getCompanyId());
        job.setSkills(request.getSkills());
        job.setExperienceYears(request.getExperienceYears());
        job.setEducationLevel(request.getEducationLevel());
        return UnifiedResponse.success(jobService.create(job));
    }

    @GetMapping("/{id}")
    public UnifiedResponse<Job> getById(@PathVariable Long id) {
        return UnifiedResponse.success(jobService.findById(id));
    }

    @GetMapping
    public UnifiedResponse<List<Job>> getAll(
            @RequestParam(required = false) Long companyId,
            @RequestParam(required = false) String status) {
        List<Job> jobs;
        if (companyId != null) {
            jobs = jobService.findByCompanyId(companyId);
        } else if (status != null) {
            jobs = jobService.findByStatus(status);
        } else {
            jobs = jobService.findAll();
        }
        return UnifiedResponse.success(jobs);
    }

    @PutMapping("/{id}")
    public UnifiedResponse<Job> update(@PathVariable Long id, @RequestBody JobRequest request) {
        Job job = new Job();
        job.setTitle(request.getTitle());
        job.setDescription(request.getDescription());
        job.setRequirements(request.getRequirements());
        job.setSkills(request.getSkills());
        job.setExperienceYears(request.getExperienceYears());
        job.setEducationLevel(request.getEducationLevel());
        job.setStatus(request.getStatus());
        return UnifiedResponse.success(jobService.update(id, job));
    }

    @DeleteMapping("/{id}")
    public UnifiedResponse<Void> delete(@PathVariable Long id) {
        jobService.delete(id);
        return UnifiedResponse.success("Job deleted successfully", null);
    }

    @PostMapping("/{id}/extract-tags")
    public ResponseEntity<UnifiedResponse<Map<String, Object>>> extractTags(@PathVariable Long id) {
        try {
            Job job = jobService.findById(id);
            String text = (job.getRequirements() != null ? job.getRequirements() : "")
                        + "\n" + (job.getDescription() != null ? job.getDescription() : "");

            if (text.trim().isEmpty()) {
                return ResponseEntity.badRequest()
                    .body(UnifiedResponse.error("岗位要求或描述不能为空"));
            }

            String url = pythonServiceUrl + "/api/job/extract-tags";
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            Map<String, String> body = new HashMap<>();
            body.put("text", text);

            HttpEntity<Map<String, String>> entity = new HttpEntity<>(body, headers);
            ResponseEntity<Map> response = restTemplate.postForEntity(url, entity, Map.class);

            if (response.getStatusCode() == HttpStatus.OK && response.getBody() != null) {
                Map<String, Object> bodyResponse = response.getBody();
                @SuppressWarnings("unchecked")
                List<String> tags = (List<String>) bodyResponse.get("tags");
                return ResponseEntity.ok(UnifiedResponse.success(Map.of("tags", tags != null ? tags : Collections.emptyList())));
            }

            return ResponseEntity.internalServerError()
                .body(UnifiedResponse.error("AI 标签提取失败"));
        } catch (Exception e) {
            return ResponseEntity.internalServerError()
                .body(UnifiedResponse.error("标签提取失败: " + e.getMessage()));
        }
    }
}