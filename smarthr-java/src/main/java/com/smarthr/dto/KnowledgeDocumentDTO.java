package com.smarthr.dto;

import lombok.Data;
import lombok.Builder;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class KnowledgeDocumentDTO {
    private Long id;
    private String documentId;
    private String title;
    private String filename;
    private String docType;
    private Long companyId;
    private String indexedStatus;
    private Integer chunks;
    private String createdAt;
}