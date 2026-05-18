package com.smarthr.controller;

import com.smarthr.dto.*;
import com.smarthr.entity.InterviewSession;
import com.smarthr.repository.InterviewSessionRepository;
import com.smarthr.service.InterviewService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
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

    @PostMapping("/sessions")
    public ResponseEntity<UnifiedResponse<InterviewSessionDTO>> createSession(
            @RequestBody CreateInterviewRequest request,
            @AuthenticationPrincipal UserDetails user) {

        Long userId = getUserId(user);
        InterviewSessionDTO session = interviewService.createSession(request, userId);
        return ResponseEntity.ok(UnifiedResponse.success("Interview session created", session));
    }

    @GetMapping("/sessions/{sessionId}")
    public ResponseEntity<UnifiedResponse<InterviewSessionDTO>> getSession(
            @PathVariable String sessionId) {

        return sessionRepository.findBySessionId(sessionId)
                .map(session -> {
                    Map<String, Object> status = interviewService.getSessionStatus(sessionId);
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
    public ResponseEntity<UnifiedResponse<InterviewSessionDTO>> sendMessage(
            @PathVariable String sessionId,
            @RequestBody SendMessageRequest request) {

        InterviewSessionDTO session = interviewService.sendMessage(sessionId, request.getMessage());
        return ResponseEntity.ok(UnifiedResponse.success(session));
    }

    @PostMapping("/sessions/{sessionId}/end")
    public ResponseEntity<UnifiedResponse<InterviewReportDTO>> endSession(
            @PathVariable String sessionId) {

        InterviewReportDTO report = interviewService.endSession(sessionId);
        return ResponseEntity.ok(UnifiedResponse.success("Interview completed", report));
    }

    @GetMapping("/sessions/{sessionId}/report")
    public ResponseEntity<UnifiedResponse<InterviewReportDTO>> getReport(
            @PathVariable String sessionId) {

        InterviewReportDTO report = interviewService.getReport(sessionId);
        return ResponseEntity.ok(UnifiedResponse.success(report));
    }

    @PostMapping("/sessions/{sessionId}/resume")
    public ResponseEntity<UnifiedResponse<InterviewSessionDTO>> resumeSession(
            @PathVariable String sessionId) {

        InterviewSessionDTO session = interviewService.resumeSession(sessionId);
        return ResponseEntity.ok(UnifiedResponse.success("Session resumed", session));
    }

    private Long getUserId(UserDetails user) {
        // In production, would query UserService to get user ID by email/username
        return 1L;
    }
}