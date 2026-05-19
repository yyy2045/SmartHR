package com.smarthr.entity;

import jakarta.persistence.*;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "resumes")
public class Resume {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String candidateName;

    private String email;

    private String phone;

    @Column(length = 500)
    private String filePath;

    @Column(columnDefinition = "TEXT")
    private String rawText;

    @Column(columnDefinition = "JSON")
    private String parsedData; // JSON structure: skills, experience, education

    private BigDecimal matchScore;

    private Long jobId;

    private Long userId; // HR who uploaded

    private Long companyId; // Company this resume belongs to

    private String status; // PARSED, MATCHED, REVIEWED

    @Column(updatable = false)
    private LocalDateTime createdAt;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
        if (status == null) {
            status = "UPLOADED";
        }
    }
}