package com.smarthr.repository;

import com.smarthr.entity.KnowledgeDocument;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.Optional;

@Repository
public interface KnowledgeDocumentRepository extends JpaRepository<KnowledgeDocument, Long> {
    Page<KnowledgeDocument> findByCompanyId(Long companyId, Pageable pageable);
    Page<KnowledgeDocument> findByCompanyIdAndDocType(Long companyId, String docType, Pageable pageable);
    Optional<KnowledgeDocument> findByDocumentId(String documentId);
}