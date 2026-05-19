package com.smarthr.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.smarthr.dto.*;
import com.smarthr.entity.KnowledgeDocument;
import com.smarthr.repository.KnowledgeDocumentRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.*;

@Service
public class KnowledgeService {

    @Value("${ai.service.url}")
    private String pythonServiceUrl;

    @Autowired
    private KnowledgeDocumentRepository documentRepository;

    @Autowired
    private ObjectMapper objectMapper;

    private final org.springframework.web.client.RestTemplate restTemplate = new org.springframework.web.client.RestTemplate();

    public KnowledgeDocumentDTO uploadDocument(MultipartFile file, String docType, Long companyId) {
        // 1. Java generates UUID -贯穿 MySQL/Redis/Chroma 三层
        String documentId = UUID.randomUUID().toString();

        // 2. Save file locally with UUID naming
        String originalFilename = file.getOriginalFilename();
        String extension = "";
        if (originalFilename != null && originalFilename.contains(".")) {
            extension = originalFilename.substring(originalFilename.lastIndexOf("."));
        }
        Path filePath = Paths.get("/tmp/smarthr-docs/" + documentId + extension);
        try {
            Files.createDirectories(filePath.getParent());
            Files.write(filePath, file.getBytes());
        } catch (Exception e) {
            throw new RuntimeException("Failed to save file locally: " + e.getMessage());
        }

        // 3. Call Python with UUID in path
        String pythonUrl = pythonServiceUrl + "/api/knowledge/documents/" + documentId;

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);

        org.springframework.util.MultiValueMap<String, Object> body
            = new org.springframework.util.LinkedMultiValueMap<>();
        body.add("file", filePath.toFile());
        body.add("company_id", companyId.toString());
        body.add("doc_type", docType);

        HttpEntity<org.springframework.util.MultiValueMap<String, Object>> entity
            = new HttpEntity<>(body, headers);

        ResponseEntity<Map> response = restTemplate.postForEntity(pythonUrl, entity, Map.class);

        if (response.getStatusCode() == HttpStatus.OK && response.getBody() != null) {
            Map<String, Object> body_response = response.getBody();

            // 4. Save to MySQL with documentId = UUID
            KnowledgeDocument doc = new KnowledgeDocument();
            doc.setDocumentId(documentId);  // Use Java-generated UUID
            doc.setTitle((String) body_response.get("title"));
            doc.setFilename(originalFilename);
            doc.setDocType(docType);
            doc.setCompanyId(companyId);
            doc.setIndexedStatus((String) body_response.get("status"));
            doc.setChunks((Integer) body_response.get("chunks"));
            doc.setFilePath(filePath.toString());

            try {
                Object chunkIdsObj = body_response.get("chunk_ids");
                if (chunkIdsObj instanceof List) {
                    doc.setChunkIds(objectMapper.writeValueAsString(chunkIdsObj));
                } else {
                    doc.setChunkIds("[]");
                }
            } catch (Exception e) {
                doc.setChunkIds("[]");
            }

            doc = documentRepository.save(doc);

            // Return DTO
            KnowledgeDocumentDTO dto = new KnowledgeDocumentDTO();
            dto.setId(doc.getId());
            dto.setDocumentId(doc.getDocumentId());  // Use actual documentId field
            dto.setTitle(doc.getTitle());
            dto.setFilename(doc.getFilename());
            dto.setDocType(doc.getDocType());
            dto.setCompanyId(doc.getCompanyId());
            dto.setIndexedStatus(doc.getIndexedStatus());
            dto.setChunks(doc.getChunks());

            return dto;
        }

        throw new RuntimeException("Failed to upload document");
    }

    public Page<KnowledgeDocumentDTO> listDocuments(Long companyId, String docType, Pageable pageable) {
        Page<KnowledgeDocument> docs;
        if (docType != null && !docType.isEmpty()) {
            docs = documentRepository.findByCompanyIdAndDocType(companyId, docType, pageable);
        } else {
            docs = documentRepository.findByCompanyId(companyId, pageable);
        }

        return docs.map(doc -> {
            KnowledgeDocumentDTO dto = new KnowledgeDocumentDTO();
            dto.setId(doc.getId());
            dto.setDocumentId(doc.getDocumentId());
            dto.setTitle(doc.getTitle());
            dto.setFilename(doc.getFilename());
            dto.setDocType(doc.getDocType());
            dto.setCompanyId(doc.getCompanyId());
            dto.setIndexedStatus(doc.getIndexedStatus());
            dto.setChunks(doc.getChunks());
            dto.setCreatedAt(doc.getCreatedAt() != null ? doc.getCreatedAt().toString() : null);
            return dto;
        });
    }

    public void reindexDocument(Long id) {
        documentRepository.findById(id).ifPresent(doc -> {
            String documentId = doc.getDocumentId();
            String url = pythonServiceUrl + "/api/knowledge/documents/" + documentId + "/reindex";
            try {
                restTemplate.postForEntity(url, null, Map.class);
            } catch (Exception e) {
                throw new RuntimeException("Failed to reindex document: " + e.getMessage());
            }
        });
    }

    public KnowledgeDocumentDTO getDocument(Long id) {
        return documentRepository.findById(id).map(doc -> {
            KnowledgeDocumentDTO dto = new KnowledgeDocumentDTO();
            dto.setId(doc.getId());
            dto.setDocumentId(doc.getDocumentId());
            dto.setTitle(doc.getTitle());
            dto.setFilename(doc.getFilename());
            dto.setDocType(doc.getDocType());
            dto.setCompanyId(doc.getCompanyId());
            dto.setIndexedStatus(doc.getIndexedStatus());
            dto.setChunks(doc.getChunks());
            dto.setCreatedAt(doc.getCreatedAt() != null ? doc.getCreatedAt().toString() : null);
            return dto;
        }).orElse(null);
    }

    public void deleteDocument(Long id) {
        // Call Python to delete from vector store - use documentId (UUID), not MySQL id
        documentRepository.findById(id).ifPresent(doc -> {
            String documentId = doc.getDocumentId();  // Java-generated UUID
            String url = pythonServiceUrl + "/api/knowledge/documents/" + documentId;
            try {
                restTemplate.delete(url);
            } catch (Exception e) {
                // Continue with local deletion even if remote fails
            }
        });

        documentRepository.deleteById(id);
    }

    public List<KnowledgeSearchResultDTO> searchKnowledge(String query, Long companyId, int topK) {
        String url = pythonServiceUrl + "/api/knowledge/search?query=" + query
            + "&company_id=" + companyId + "&top_k=" + topK;

        HttpHeaders headers = new HttpHeaders();
        HttpEntity<Void> entity = new HttpEntity<>(headers);

        ResponseEntity<Map> response = restTemplate.getForEntity(url, Map.class);

        if (response.getStatusCode() == HttpStatus.OK && response.getBody() != null) {
            Map<String, Object> body = response.getBody();
            @SuppressWarnings("unchecked")
            List<Map<String, Object>> results = (List<Map<String, Object>>) body.get("results");

            List<KnowledgeSearchResultDTO> searchResults = new ArrayList<>();
            if (results != null) {
                for (Map<String, Object> r : results) {
                    KnowledgeSearchResultDTO dto = new KnowledgeSearchResultDTO();
                    dto.setContent((String) r.get("content"));
                    dto.setSource((String) r.get("source"));
                    dto.setDocType((String) r.get("doc_type"));
                    Object similarity = r.get("similarity");
                    if (similarity instanceof Number) {
                        dto.setSimilarity(((Number) similarity).doubleValue());
                    }
                    searchResults.add(dto);
                }
            }
            return searchResults;
        }

        return Collections.emptyList();
    }
}