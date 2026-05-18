package com.smarthr.entity;

import jakarta.persistence.*;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@Entity
@Table(name = "knowledge_documents")
public class KnowledgeDocument {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String title;

    private String filename;

    @Column(nullable = false)
    private String docType; // POLICY, MANUAL, HISTORY, OTHER

    private String filePath;

    private Long companyId;

    @Column(nullable = false)
    private String indexedStatus; // PENDING, INDEXED, FAILED

    private Integer chunks;

    @Column(columnDefinition = "JSON")
    private String chunkIds; // JSON array of chunk IDs

    @Column(columnDefinition = "TEXT")
    private String metadata; // Additional metadata JSON

    @Column(updatable = false)
    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
        updatedAt = LocalDateTime.now();
        if (indexedStatus == null) {
            indexedStatus = "PENDING";
        }
    }

    @PreUpdate
    protected void onUpdate() {
        updatedAt = LocalDateTime.now();
    }
}