package com.smarthr.controller;

import com.smarthr.dto.CompanyRequest;
import com.smarthr.dto.UnifiedResponse;
import com.smarthr.entity.Company;
import com.smarthr.service.CompanyService;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/companies")
public class CompanyController {

    @Autowired
    private CompanyService companyService;

    @PostMapping
    public UnifiedResponse<Company> create(@Valid @RequestBody CompanyRequest request) {
        Company company = new Company();
        company.setName(request.getName());
        company.setIndustry(request.getIndustry());
        company.setDescription(request.getDescription());
        return UnifiedResponse.success(companyService.create(company));
    }

    @GetMapping("/{id}")
    public UnifiedResponse<Company> getById(@PathVariable Long id) {
        return UnifiedResponse.success(companyService.findById(id));
    }

    @GetMapping
    public UnifiedResponse<List<Company>> getAll() {
        return UnifiedResponse.success(companyService.findAll());
    }

    @PutMapping("/{id}")
    public UnifiedResponse<Company> update(@PathVariable Long id, @RequestBody CompanyRequest request) {
        Company company = new Company();
        company.setName(request.getName());
        company.setIndustry(request.getIndustry());
        company.setDescription(request.getDescription());
        return UnifiedResponse.success(companyService.update(id, company));
    }

    @DeleteMapping("/{id}")
    public UnifiedResponse<Void> delete(@PathVariable Long id) {
        companyService.delete(id);
        return UnifiedResponse.success("Company deleted successfully", null);
    }
}