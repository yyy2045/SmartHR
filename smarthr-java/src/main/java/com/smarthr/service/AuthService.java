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

import java.util.Set;

@Service
public class AuthService {

    // 允许自助注册的角色白名单。ADMIN 等特权角色禁止由注册接口自助获取，
    // 只能由管理员后台分配，避免任意访客注册即提权（垂直越权）。
    private static final Set<String> SELF_SERVICE_ROLES = Set.of("HR", "INTERVIEWER");
    private static final String DEFAULT_ROLE = "HR";

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
        user.setRole(resolveSelfServiceRole(request.getRole()));
        user.setCompanyId(companyId);

        user = userRepository.save(user);

        String token = jwtTokenProvider.generateToken(user.getEmail(), user.getId(), user.getRole(), user.getCompanyId());

        return new AuthResponse(token, user.getEmail(), user.getName(), user.getRole(), user.getId(), user.getCompanyId());
    }

    /**
     * 将注册请求中的角色规范化为安全角色。
     * 只接受白名单内的自助注册角色（大小写不敏感），其余（含 ADMIN、空值、未知值）一律降级为默认 HR。
     * 这样即使前端/攻击者在注册体里传 role=ADMIN，也无法获得管理员权限。
     */
    private String resolveSelfServiceRole(String requestedRole) {
        if (requestedRole == null) {
            return DEFAULT_ROLE;
        }
        String normalized = requestedRole.trim().toUpperCase();
        return SELF_SERVICE_ROLES.contains(normalized) ? normalized : DEFAULT_ROLE;
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