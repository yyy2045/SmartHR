package com.smarthr.repository;

import com.smarthr.entity.InterviewSession;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.Optional;

@Repository
public interface InterviewSessionRepository extends JpaRepository<InterviewSession, Long> {
    Optional<InterviewSession> findBySessionId(String sessionId);
    java.util.List<InterviewSession> findByStatus(String status);
}