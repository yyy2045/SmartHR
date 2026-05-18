package com.smarthr.dto;

import lombok.Data;

@Data
public class KnowledgeSearchResultDTO {
    private String content;
    private String source;
    private String docType;
    private Double similarity;
}