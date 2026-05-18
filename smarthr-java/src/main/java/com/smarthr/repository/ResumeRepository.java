package com.smarthr.repository;

import com.smarthr.entity.Resume;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface ResumeRepository extends JpaRepository<Resume, Long> {
    List<Resume> findByJobId(Long jobId);
    List<Resume> findByUserId(Long userId);
}