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
            String rawText = ""; // Would need to read file - simplified for now
            ParsedResumeDTO parsed = null;
            try {
                String parseResult = resumeAIService.uploadAndParseResume(file);
                // Raw text will be extracted by Python service
            } catch (Exception e) {
                // If AI parsing fails, still save the resume
            }

            // Create resume record
            Resume resume = new Resume();
            resume.setFilePath(filePath.toString());
            resume.setJobId(jobId);
            resume.setStatus("UPLOADED");
            // Note: parsedData and matchScore will be updated after AI processing

            // Get user ID from user details (assuming username is email, need to query)
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
            if (resumeText == null || resumeText.isEmpty()) {
                return ResponseEntity.badRequest()
                        .body(UnifiedResponse.error("No raw text available for matching"));
            }

            MatchResultDTO result = resumeAIService.matchResume(id, jobId, resumeText);

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