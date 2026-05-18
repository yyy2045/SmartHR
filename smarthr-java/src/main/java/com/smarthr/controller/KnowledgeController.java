package com.smarthr.controller;

import com.smarthr.dto.*;
import com.smarthr.service.KnowledgeService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.web.PageableDefault;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

@RestController
@RequestMapping("/api/knowledge")
public class KnowledgeController {

    @Autowired
    private KnowledgeService knowledgeService;

    @PostMapping("/documents")
    public ResponseEntity<UnifiedResponse<KnowledgeDocumentDTO>> uploadDocument(
            @RequestParam("file") MultipartFile file,
            @RequestParam("docType") String docType,
            @RequestParam(value = "companyId", required = false) Long companyId,
            @AuthenticationPrincipal UserDetails user) {

        // Use user's company ID if not provided
        if (companyId == null) {
            companyId = getUserCompanyId(user);
        }

        KnowledgeDocumentDTO doc = knowledgeService.uploadDocument(file, docType, companyId);
        return ResponseEntity.ok(UnifiedResponse.success("Document uploaded", doc));
    }

    @GetMapping("/documents")
    public ResponseEntity<UnifiedResponse<Page<KnowledgeDocumentDTO>>> listDocuments(
            @RequestParam(required = false) Long companyId,
            @RequestParam(required = false) String docType,
            @PageableDefault(size = 20) Pageable pageable) {

        if (companyId == null) {
            companyId = 1L; // Default company
        }

        Page<KnowledgeDocumentDTO> documents = knowledgeService.listDocuments(companyId, docType, pageable);
        return ResponseEntity.ok(UnifiedResponse.success(documents));
    }

    @GetMapping("/documents/{id}")
    public ResponseEntity<UnifiedResponse<KnowledgeDocumentDTO>> getDocument(@PathVariable Long id) {
        KnowledgeDocumentDTO doc = knowledgeService.getDocument(id);
        if (doc == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(UnifiedResponse.success(doc));
    }

    @DeleteMapping("/documents/{id}")
    public ResponseEntity<UnifiedResponse<String>> deleteDocument(@PathVariable Long id) {
        knowledgeService.deleteDocument(id);
        return ResponseEntity.ok(UnifiedResponse.success("Document deleted", null));
    }

    @GetMapping("/search")
    public ResponseEntity<UnifiedResponse<List<KnowledgeSearchResultDTO>>> searchKnowledge(
            @RequestParam String query,
            @RequestParam(required = false) Long companyId,
            @RequestParam(defaultValue = "5") int topK) {

        if (companyId == null) {
            companyId = 1L;
        }

        List<KnowledgeSearchResultDTO> results = knowledgeService.searchKnowledge(query, companyId, topK);
        return ResponseEntity.ok(UnifiedResponse.success(results));
    }

    private Long getUserCompanyId(UserDetails user) {
        // In production, would query UserService to get company ID
        return 1L;
    }
}