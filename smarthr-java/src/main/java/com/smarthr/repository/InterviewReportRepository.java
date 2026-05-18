package com.smarthr.repository;

import com.smarthr.entity.InterviewReport;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.Optional;

@Repository
public interface InterviewReportRepository extends JpaRepository<InterviewReport, Long> {
    Optional<InterviewReport> findBySessionId(Long sessionId);
}