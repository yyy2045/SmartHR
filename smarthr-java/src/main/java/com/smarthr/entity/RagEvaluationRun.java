package com.smarthr.entity;

import jakarta.persistence.*;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "rag_evaluation_runs")
public class RagEvaluationRun {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(unique = true, length = 100)
    private String runId;

    private String status;

    private String evaluator;

    private BigDecimal thresholdScore;

    private Integer sampleCount;

    @Column(columnDefinition = "JSON")
    private String metrics;

    @Column(columnDefinition = "JSON")
    private String failedSamples;

    @Column(columnDefinition = "JSON")
    private String sampleResults;

    @Column(columnDefinition = "TEXT")
    private String notes;

    private String startedAt;

    private String completedAt;

    @Column(updatable = false)
    private LocalDateTime createdAt;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
    }
}
