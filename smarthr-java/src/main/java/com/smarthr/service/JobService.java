package com.smarthr.service;

import com.smarthr.entity.Job;
import com.smarthr.exception.GlobalException;
import com.smarthr.repository.JobRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class JobService {

    @Autowired
    private JobRepository jobRepository;

    public Job create(Job job) {
        return jobRepository.save(job);
    }

    public Job findById(Long id) {
        return jobRepository.findById(id)
                .orElseThrow(() -> new GlobalException(404, "Job not found"));
    }

    public List<Job> findAll() {
        return jobRepository.findAll();
    }

    public List<Job> findByCompanyId(Long companyId) {
        return jobRepository.findByCompanyId(companyId);
    }

    public List<Job> findByStatus(String status) {
        return jobRepository.findByStatus(status);
    }

    public Job update(Long id, Job jobDetails) {
        Job job = findById(id);
        job.setTitle(jobDetails.getTitle());
        job.setDescription(jobDetails.getDescription());
        job.setRequirements(jobDetails.getRequirements());
        job.setSkills(jobDetails.getSkills());
        job.setExperienceYears(jobDetails.getExperienceYears());
        job.setEducationLevel(jobDetails.getEducationLevel());
        job.setStatus(jobDetails.getStatus());
        return jobRepository.save(job);
    }

    public void delete(Long id) {
        Job job = findById(id);
        jobRepository.delete(job);
    }
}