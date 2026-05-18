package com.smarthr.service;

import com.smarthr.entity.Company;
import com.smarthr.exception.GlobalException;
import com.smarthr.repository.CompanyRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class CompanyService {

    @Autowired
    private CompanyRepository companyRepository;

    public Company create(Company company) {
        return companyRepository.save(company);
    }

    public Company findById(Long id) {
        return companyRepository.findById(id)
                .orElseThrow(() -> new GlobalException(404, "Company not found"));
    }

    public List<Company> findAll() {
        return companyRepository.findAll();
    }

    public Company update(Long id, Company companyDetails) {
        Company company = findById(id);
        company.setName(companyDetails.getName());
        company.setIndustry(companyDetails.getIndustry());
        company.setDescription(companyDetails.getDescription());
        return companyRepository.save(company);
    }

    public void delete(Long id) {
        Company company = findById(id);
        companyRepository.delete(company);
    }
}