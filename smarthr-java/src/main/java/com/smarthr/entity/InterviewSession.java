package com.smarthr.entity;

import jakarta.persistence.*;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "interview_sessions")
public class InterviewSession {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(unique = true, nullable = false, length = 100)
    private String sessionId;

    private Long jobId;

    private Long resumeId;

    private Long userId;

    private String status; // IN_PROGRESS, COMPLETED, ABANDONED

    private Integer currentQuestionIndex;

    @Column(columnDefinition = "TEXT")
    private String interviewHistory; // JSON array of Q&A

    @Column(updatable = false)
    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;

    private LocalDateTime completedAt;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
        updatedAt = LocalDateTime.now();
        status = "IN_PROGRESS";
    }

    @PreUpdate
    protected void onUpdate() {
        updatedAt = LocalDateTime.now();
    }
}