package com.smarthr.controller;

import com.smarthr.dto.CompanyRequest;
import com.smarthr.dto.UnifiedResponse;
import com.smarthr.config.JwtAuthenticationFilter.CustomAuthDetails;
import com.smarthr.entity.Company;
import com.smarthr.exception.GlobalException;
import com.smarthr.service.CompanyService;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/companies")
public class CompanyController {

    @Autowired
    private CompanyService companyService;

    @PostMapping
    @PreAuthorize("hasRole('ADMIN')")
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
    @PreAuthorize("isAuthenticated()")
    public UnifiedResponse<Company> update(@PathVariable Long id, @RequestBody CompanyRequest request) {
        assertCanUpdateCompany(id);
        Company company = new Company();
        company.setName(request.getName());
        company.setIndustry(request.getIndustry());
        company.setDescription(request.getDescription());
        return UnifiedResponse.success(companyService.update(id, company));
    }

    @DeleteMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public UnifiedResponse<Void> delete(@PathVariable Long id) {
        companyService.delete(id);
        return UnifiedResponse.success("Company deleted successfully", null);
    }

    private void assertCanUpdateCompany(Long companyId) {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        Object details = auth != null ? auth.getDetails() : null;
        if (!(details instanceof CustomAuthDetails authDetails)) {
            throw new GlobalException(403, "无权修改企业信息");
        }

        String role = authDetails.getRole();
        if ("ADMIN".equalsIgnoreCase(role)) {
            return;
        }

        Long userCompanyId = authDetails.getCompanyId();
        if (userCompanyId == null || !userCompanyId.equals(companyId)) {
            throw new GlobalException(403, "只能修改自己所属企业的信息");
        }
    }
}
