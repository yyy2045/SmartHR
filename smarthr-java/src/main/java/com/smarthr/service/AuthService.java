package com.smarthr.service;

import com.smarthr.config.JwtTokenProvider;
import com.smarthr.dto.AuthResponse;
import com.smarthr.dto.LoginRequest;
import com.smarthr.dto.RegisterRequest;
import com.smarthr.entity.Company;
import com.smarthr.entity.User;
import com.smarthr.exception.GlobalException;
import com.smarthr.repository.CompanyRepository;
import com.smarthr.repository.UserRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

@Service
public class AuthService {

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private PasswordEncoder passwordEncoder;

    @Autowired
    private JwtTokenProvider jwtTokenProvider;

    @Autowired
    private CompanyRepository companyRepository;

    public AuthResponse register(RegisterRequest request) {
        if (userRepository.existsByEmail(request.getEmail())) {
            throw new GlobalException(400, "Email already exists");
        }

        // 根据公司名称查找或创建公司
        Long companyId = request.getCompanyId();
        if (companyId == null && request.getCompanyName() != null && !request.getCompanyName().isBlank()) {
            Company company = companyRepository.findByName(request.getCompanyName());
            if (company == null) {
                company = new Company();
                company.setName(request.getCompanyName());
                company = companyRepository.save(company);
            }
            companyId = company.getId();
        }

        User user = new User();
        user.setEmail(request.getEmail());
        user.setPassword(passwordEncoder.encode(request.getPassword()));
        user.setName(request.getName());
        user.setRole(request.getRole() != null ? request.getRole() : "HR");
        user.setCompanyId(companyId);

        user = userRepository.save(user);

        String token = jwtTokenProvider.generateToken(user.getEmail(), user.getId(), user.getRole(), user.getCompanyId());

        return new AuthResponse(token, user.getEmail(), user.getName(), user.getRole(), user.getId(), user.getCompanyId());
    }

    public AuthResponse login(LoginRequest request) {
        User user = userRepository.findByEmail(request.getEmail())
                .orElseThrow(() -> new GlobalException(401, "Invalid email or password"));

        if (!passwordEncoder.matches(request.getPassword(), user.getPassword())) {
            throw new GlobalException(401, "Invalid email or password");
        }

        String token = jwtTokenProvider.generateToken(user.getEmail(), user.getId(), user.getRole(), user.getCompanyId());

        return new AuthResponse(token, user.getEmail(), user.getName(), user.getRole(), user.getId(), user.getCompanyId());
    }
}