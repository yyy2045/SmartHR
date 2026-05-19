package com.smarthr.repository;

import com.smarthr.entity.Resume;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;
import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface ResumeRepository extends JpaRepository<Resume, Long> {
    Page<Resume> findByJobId(Long jobId, Pageable pageable);
    Page<Resume> findByUserId(Long userId, Pageable pageable);
    Page<Resume> findByCompanyId(Long companyId, Pageable pageable);
    List<Resume> findByCreatedAtAfter(LocalDateTime after);
}