package com.smarthr.repository;

import com.smarthr.entity.RagEvaluationRun;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface RagEvaluationRunRepository extends JpaRepository<RagEvaluationRun, Long> {
    Optional<RagEvaluationRun> findTopByOrderByCreatedAtDesc();
}
