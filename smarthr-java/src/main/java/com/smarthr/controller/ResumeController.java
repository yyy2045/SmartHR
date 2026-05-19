package com.smarthr.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.smarthr.dto.MatchResultDTO;
import com.smarthr.dto.ParsedResumeDTO;
import com.smarthr.dto.UnifiedResponse;
import com.smarthr.entity.Resume;
import com.smarthr.repository.ResumeRepository;
import com.smarthr.service.ResumeAIService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.web.PageableDefault;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.math.BigDecimal;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.*;

@RestController
@RequestMapping("/api/resumes")
public class ResumeController {

    @Autowired
    private ResumeRepository resumeRepository;

    @Autowired
    private ResumeAIService resumeAIService;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private com.smarthr.repository.JobRepository jobRepository;

    private final String uploadDir = "./uploads/resumes";

    @PostMapping("/upload")
    public ResponseEntity<UnifiedResponse<Resume>> uploadResume(
            @RequestParam("file") MultipartFile file,
            @RequestParam(value = "jobId", required = false) Long jobId,
            @AuthenticationPrincipal UserDetails user) {

        try {
            // Create upload directory if not exists
            Path uploadPath = Paths.get(uploadDir);
            if (!Files.exists(uploadPath)) {
                Files.createDirectories(uploadPath);
            }

            // Generate unique filename
            String originalFilename = file.getOriginalFilename();
            String extension = "";
            if (originalFilename != null && originalFilename.contains(".")) {
                extension = originalFilename.substring(originalFilename.substring(1).lastIndexOf("."));
            }
            String filename = UUID.randomUUID().toString() + extension;
            Path filePath = uploadPath.resolve(filename);

            // Save file
            Files.copy(file.getInputStream(), filePath);

            // Call Python AI service to parse resume
            String rawText = "";
            ParsedResumeDTO parsed = null;
            try {
                String parseResult = resumeAIService.uploadAndParseResume(file);
                // 解析 Python 返回的 JSON，获取 rawText 和结构化数据
                com.fasterxml.jackson.databind.JsonNode root = objectMapper.readTree(parseResult);
                rawText = root.has("raw_text") ? root.get("raw_text").asText() : "";

                if (root.has("data")) {
                    parsed = objectMapper.treeToValue(root.get("data"), ParsedResumeDTO.class);
                }
            } catch (Exception e) {
                // 不阻塞简历落库，但要记录原因（Python 服务挂了 / LLM 失败 / 文件格式异常等）
                System.err.println("[ResumeController] AI 解析失败，将仅保存原始文件：" + e.getMessage());
            }

            // Create resume record
            Resume resume = new Resume();
            resume.setFilePath(filePath.toString());
            resume.setRawText(rawText);
            resume.setJobId(jobId);
            resume.setStatus("UPLOADED");

            // 如果解析成功，填充结构化数据
            if (parsed != null) {
                resume.setCandidateName(parsed.getCandidateName());
                resume.setEmail(parsed.getEmail());
                resume.setPhone(parsed.getPhone());
                resume.setParsedData(objectMapper.writeValueAsString(parsed));
                resume.setStatus("PARSED");
            }

            resume = resumeRepository.save(resume);

            return ResponseEntity.ok(UnifiedResponse.success("Resume uploaded successfully", resume));
        } catch (Exception e) {
            return ResponseEntity.internalServerError()
                    .body(UnifiedResponse.error("Failed to upload resume: " + e.getMessage()));
        }
    }

    @GetMapping
    public ResponseEntity<UnifiedResponse<Page<Resume>>> listResumes(
            @RequestParam(required = false) Long jobId,
            @RequestParam(required = false) String status,
            @PageableDefault(size = 20) Pageable pageable) {

        Page<Resume> resumes;
        if (jobId != null) {
            resumes = resumeRepository.findByJobId(jobId, pageable);
        } else {
            resumes = resumeRepository.findAll(pageable);
        }

        return ResponseEntity.ok(UnifiedResponse.success(resumes));
    }

    @GetMapping("/{id}")
    public ResponseEntity<UnifiedResponse<Resume>> getResume(@PathVariable Long id) {
        return resumeRepository.findById(id)
                .map(resume -> ResponseEntity.ok(UnifiedResponse.success(resume)))
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping("/{id}/parse")
    public ResponseEntity<UnifiedResponse<ParsedResumeDTO>> parseResume(@PathVariable Long id) {
        try {
            Resume resume = resumeRepository.findById(id)
                    .orElseThrow(() -> new RuntimeException("Resume not found"));

            // If no raw text, read from file
            String rawText = resume.getRawText();
            if (rawText == null || rawText.isEmpty()) {
                // For now, return error - need to implement file reading
                return ResponseEntity.badRequest()
                        .body(UnifiedResponse.error("No raw text available. Please upload with raw text."));
            }

            ParsedResumeDTO parsed = resumeAIService.parseResume(rawText);

            // Update resume with parsed data
            resume.setParsedData(objectMapper.writeValueAsString(parsed));
            resume.setCandidateName(parsed.getCandidateName());
            resume.setEmail(parsed.getEmail());
            resume.setPhone(parsed.getPhone());
            resume.setStatus("PARSED");
            resumeRepository.save(resume);

            return ResponseEntity.ok(UnifiedResponse.success(parsed));
        } catch (Exception e) {
            return ResponseEntity.internalServerError()
                    .body(UnifiedResponse.error("Failed to parse resume: " + e.getMessage()));
        }
    }

    @PostMapping("/{id}/match")
    public ResponseEntity<UnifiedResponse<MatchResultDTO>> matchResume(
            @PathVariable Long id,
            @RequestParam Long jobId) {
        try {
            Resume resume = resumeRepository.findById(id)
                    .orElseThrow(() -> new RuntimeException("Resume not found"));

            String resumeText = resume.getRawText();

            // 兜底：rawText 为空时尝试从已保存的文件中重新提取
            if ((resumeText == null || resumeText.isEmpty()) && resume.getFilePath() != null) {
                java.io.File savedFile = new java.io.File(resume.getFilePath());
                if (savedFile.exists()) {
                    try {
                        resumeText = resumeAIService.extractRawTextFromFile(savedFile);
                        if (resumeText != null && !resumeText.isEmpty()) {
                            resume.setRawText(resumeText);
                            resumeRepository.save(resume);
                        }
                    } catch (Exception ex) {
                        return ResponseEntity.badRequest()
                                .body(UnifiedResponse.error("简历文本提取失败：" + ex.getMessage()));
                    }
                }
            }

            if (resumeText == null || resumeText.isEmpty()) {
                return ResponseEntity.badRequest()
                        .body(UnifiedResponse.error("无可用简历文本，请重新上传简历"));
            }

            // 取出 JD 全文（标题+描述+要求+技能）一并传给 Python，避免 LLM 凭空生成
            String jobText = jobRepository.findById(jobId).map(j -> {
                StringBuilder sb = new StringBuilder();
                if (j.getTitle() != null) sb.append("岗位：").append(j.getTitle()).append("\n");
                if (j.getDescription() != null) sb.append("描述：").append(j.getDescription()).append("\n");
                if (j.getRequirements() != null) sb.append("任职要求：").append(j.getRequirements()).append("\n");
                if (j.getSkills() != null) sb.append("技能：").append(j.getSkills()).append("\n");
                return sb.toString();
            }).orElse("");

            String parsedResumeJson = resume.getParsedData();

            MatchResultDTO result = resumeAIService.matchResume(id, jobId, resumeText, jobText, parsedResumeJson);

            // Update resume with match score
            resume.setMatchScore(BigDecimal.valueOf(result.getMatchScore()));
            resume.setJobId(jobId);
            resume.setStatus("MATCHED");
            resumeRepository.save(resume);

            return ResponseEntity.ok(UnifiedResponse.success(result));
        } catch (Exception e) {
            return ResponseEntity.internalServerError()
                    .body(UnifiedResponse.error("Failed to match resume: " + e.getMessage()));
        }
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<UnifiedResponse<String>> deleteResume(@PathVariable Long id) {
        try {
            resumeRepository.deleteById(id);
            return ResponseEntity.ok(UnifiedResponse.success("Resume deleted successfully", null));
        } catch (Exception e) {
            return ResponseEntity.internalServerError()
                    .body(UnifiedResponse.error("Failed to delete resume: " + e.getMessage()));
        }
    }
}