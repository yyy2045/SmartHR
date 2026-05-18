package com.smarthr.controller;

import com.smarthr.dto.JobRequest;
import com.smarthr.dto.UnifiedResponse;
import com.smarthr.entity.Job;
import com.smarthr.service.JobService;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/jobs")
public class JobController {

    @Autowired
    private JobService jobService;

    @PostMapping
    public UnifiedResponse<Job> create(@Valid @RequestBody JobRequest request) {
        Job job = new Job();
        job.setTitle(request.getTitle());
        job.setDescription(request.getDescription());
        job.setRequirements(request.getRequirements());
        job.setCompanyId(request.getCompanyId());
        job.setSkills(request.getSkills());
        job.setExperienceYears(request.getExperienceYears());
        job.setEducationLevel(request.getEducationLevel());
        return UnifiedResponse.success(jobService.create(job));
    }

    @GetMapping("/{id}")
    public UnifiedResponse<Job> getById(@PathVariable Long id) {
        return UnifiedResponse.success(jobService.findById(id));
    }

    @GetMapping
    public UnifiedResponse<List<Job>> getAll(
            @RequestParam(required = false) Long companyId,
            @RequestParam(required = false) String status) {
        List<Job> jobs;
        if (companyId != null) {
            jobs = jobService.findByCompanyId(companyId);
        } else if (status != null) {
            jobs = jobService.findByStatus(status);
        } else {
            jobs = jobService.findAll();
        }
        return UnifiedResponse.success(jobs);
    }

    @PutMapping("/{id}")
    public UnifiedResponse<Job> update(@PathVariable Long id, @RequestBody JobRequest request) {
        Job job = new Job();
        job.setTitle(request.getTitle());
        job.setDescription(request.getDescription());
        job.setRequirements(request.getRequirements());
        job.setSkills(request.getSkills());
        job.setExperienceYears(request.getExperienceYears());
        job.setEducationLevel(request.getEducationLevel());
        job.setStatus(request.getStatus());
        return UnifiedResponse.success(jobService.update(id, job));
    }

    @DeleteMapping("/{id}")
    public UnifiedResponse<Void> delete(@PathVariable Long id) {
        jobService.delete(id);
        return UnifiedResponse.success("Job deleted successfully", null);
    }
}