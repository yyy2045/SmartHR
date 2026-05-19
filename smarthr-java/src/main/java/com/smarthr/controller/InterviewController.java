package com.smarthr.controller;

import com.smarthr.config.JwtAuthenticationFilter.CustomAuthDetails;
import com.smarthr.dto.*;
import com.smarthr.entity.InterviewSession;
import com.smarthr.repository.InterviewSessionRepository;
import com.smarthr.repository.InterviewReportRepository;
import com.smarthr.repository.JobRepository;
import com.smarthr.repository.ResumeRepository;
import com.smarthr.service.InterviewService;
import com.smarthr.service.UserService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/interview")
public class InterviewController {

    @Autowired
    private InterviewService interviewService;

    @Autowired
    private InterviewSessionRepository sessionRepository;

    @Autowired
    private ResumeRepository resumeRepository;

    @Autowired
    private JobRepository jobRepository;

    @Autowired
    private InterviewReportRepository interviewReportRepository;

    @Autowired
    private UserService userService;

    @PostMapping("/sessions")
    @PreAuthorize("hasAnyRole('HR', 'ADMIN', 'INTERVIEWER')")
    public ResponseEntity<UnifiedResponse<InterviewSessionDTO>> createSession(
            @RequestBody CreateInterviewRequest request,
            @AuthenticationPrincipal UserDetails user) {

        Long userId = getUserId(user);
        InterviewSessionDTO session = interviewService.createSession(request, userId);
        return ResponseEntity.ok(UnifiedResponse.success("Interview session created", session));
    }

    @GetMapping("/sessions")
    @PreAuthorize("hasAnyRole('HR', 'ADMIN', 'INTERVIEWER')")
    public ResponseEntity<UnifiedResponse<java.util.List<InterviewSessionDTO>>> getSessions(
            @RequestParam(required = false) String status) {

        java.util.List<InterviewSession> sessions;
        if (status != null && !status.isEmpty()) {
            sessions = sessionRepository.findByStatus(status);
        } else {
            sessions = sessionRepository.findAll();
        }
        java.util.List<InterviewSessionDTO> dtos = sessions.stream().map(s -> {
            InterviewSessionDTO dto = new InterviewSessionDTO();
            dto.setSessionId(s.getSessionId());
            dto.setJobId(s.getJobId());
            dto.setResumeId(s.getResumeId());
            dto.setStatus(s.getStatus());
            dto.setComplete("COMPLETED".equals(s.getStatus()));
            // 查询候选人姓名和岗位名称
            if (s.getResumeId() != null) {
                resumeRepository.findById(s.getResumeId()).ifPresent(r -> dto.setCandidateName(r.getCandidateName()));
            }
            if (s.getJobId() != null) {
                jobRepository.findById(s.getJobId()).ifPresent(j -> dto.setJobTitle(j.getTitle()));
            }
            return dto;
        }).collect(java.util.stream.Collectors.toList());
        return ResponseEntity.ok(UnifiedResponse.success(dtos));
    }

    @GetMapping("/sessions/{sessionId}")
    @PreAuthorize("hasAnyRole('HR', 'ADMIN', 'INTERVIEWER')")
    public ResponseEntity<UnifiedResponse<InterviewSessionDTO>> getSession(
            @PathVariable String sessionId) {

        return sessionRepository.findBySessionId(sessionId)
                .map(session -> {
                    InterviewSessionDTO status = interviewService.getSessionStatus(sessionId);
                    InterviewSessionDTO dto = new InterviewSessionDTO();
                    dto.setSessionId(sessionId);
                    dto.setJobId(session.getJobId());
                    dto.setResumeId(session.getResumeId());
                    dto.setStatus(session.getStatus());
                    dto.setComplete("COMPLETED".equals(session.getStatus()));
                    return ResponseEntity.ok(UnifiedResponse.success(dto));
                })
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping("/sessions/{sessionId}/message")
    @PreAuthorize("hasAnyRole('HR', 'ADMIN', 'INTERVIEWER')")
    public ResponseEntity<UnifiedResponse<InterviewSessionDTO>> sendMessage(
            @PathVariable String sessionId,
            @RequestBody SendMessageRequest request) {

        InterviewSessionDTO session = interviewService.sendMessage(sessionId, request.getMessage());
        return ResponseEntity.ok(UnifiedResponse.success(session));
    }

    @PostMapping("/sessions/{sessionId}/end")
    @PreAuthorize("hasAnyRole('HR', 'ADMIN', 'INTERVIEWER')")
    public ResponseEntity<UnifiedResponse<InterviewReportDTO>> endSession(
            @PathVariable String sessionId) {

        InterviewReportDTO report = interviewService.endSession(sessionId);
        return ResponseEntity.ok(UnifiedResponse.success("Interview completed", report));
    }

    @GetMapping("/sessions/{sessionId}/report")
    @PreAuthorize("hasAnyRole('HR', 'ADMIN', 'INTERVIEWER')")
    public ResponseEntity<UnifiedResponse<InterviewReportDTO>> getReport(
            @PathVariable String sessionId) {

        InterviewReportDTO report = interviewService.getReport(sessionId);
        return ResponseEntity.ok(UnifiedResponse.success(report));
    }

    @PostMapping("/sessions/{sessionId}/resume")
    @PreAuthorize("hasAnyRole('HR', 'ADMIN', 'INTERVIEWER')")
    public ResponseEntity<UnifiedResponse<InterviewSessionDTO>> resumeSession(
            @PathVariable String sessionId) {

        InterviewSessionDTO session = interviewService.getSessionStatus(sessionId);
        return ResponseEntity.ok(UnifiedResponse.success("Session resumed", session));
    }

    private Long getUserId(UserDetails user) {
        if (user == null) return null;
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth != null && auth.getDetails() instanceof CustomAuthDetails) {
            return ((CustomAuthDetails) auth.getDetails()).getUserId();
        }
        // 兜底：从数据库查询
        com.smarthr.entity.User u = userService.findByEmail(user.getUsername());
        return u != null ? u.getId() : null;
    }

    @GetMapping("/reports/stats/count")
    @PreAuthorize("hasAnyRole('HR', 'ADMIN')")
    public ResponseEntity<UnifiedResponse<Long>> countReportsGenerated() {
        long count = interviewReportRepository.count();
        return ResponseEntity.ok(UnifiedResponse.success(count));
    }
}