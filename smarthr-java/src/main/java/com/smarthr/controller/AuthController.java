package com.smarthr.controller;

import com.smarthr.dto.AuthResponse;
import com.smarthr.dto.LoginRequest;
import com.smarthr.dto.RegisterRequest;
import com.smarthr.dto.UnifiedResponse;
import com.smarthr.service.AuthService;
import jakarta.servlet.http.Cookie;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    @Autowired
    private AuthService authService;

    @PostMapping("/register")
    public UnifiedResponse<AuthResponse> register(@Valid @RequestBody RegisterRequest request, HttpServletResponse response) {
        AuthResponse authResponse = authService.register(request);
        setJwtCookie(response, authResponse.getToken());
        return UnifiedResponse.success(authResponse);
    }

    @PostMapping("/login")
    public UnifiedResponse<AuthResponse> login(@Valid @RequestBody LoginRequest request, HttpServletResponse response) {
        AuthResponse authResponse = authService.login(request);
        setJwtCookie(response, authResponse.getToken());
        return UnifiedResponse.success(authResponse);
    }

    private void setJwtCookie(HttpServletResponse response, String token) {
        Cookie cookie = new Cookie("jwt", token);
        cookie.setHttpOnly(true);
        cookie.setSecure(false);  // 开发环境 false，生产环境 true
        cookie.setPath("/");
        cookie.setMaxAge(86400);  // 24 小时
        response.addCookie(cookie);
    }
}