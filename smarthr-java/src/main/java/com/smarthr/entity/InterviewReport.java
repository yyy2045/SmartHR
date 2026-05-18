package com.smarthr.entity;

import jakarta.persistence.*;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "interview_reports")
public class InterviewReport {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private Long sessionId;

    private BigDecimal overallScore;

    private BigDecimal skillScore;

    private BigDecimal behaviorScore;

    private BigDecimal experienceScore;

    private String recommendation; // STRONG_HIRE, HIRE, NO_HIRE, WEAK_NO_HIRE

    @Column(columnDefinition = "JSON")
    private String reportData; // Full structured report JSON

    @Column(columnDefinition = "TEXT")
    private String summary; // Executive summary

    @Column(updatable = false)
    private LocalDateTime createdAt;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
    }
}