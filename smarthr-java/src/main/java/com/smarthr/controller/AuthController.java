package com.smarthr.controller;

import com.smarthr.dto.AuthResponse;
import com.smarthr.dto.LoginRequest;
import com.smarthr.dto.RegisterRequest;
import com.smarthr.dto.UnifiedResponse;
import com.smarthr.service.AuthService;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    @Autowired
    private AuthService authService;

    @PostMapping("/register")
    public UnifiedResponse<AuthResponse> register(@Valid @RequestBody RegisterRequest request) {
        return UnifiedResponse.success(authService.register(request));
    }

    @PostMapping("/login")
    public UnifiedResponse<AuthResponse> login(@Valid @RequestBody LoginRequest request) {
        return UnifiedResponse.success(authService.login(request));
    }
}