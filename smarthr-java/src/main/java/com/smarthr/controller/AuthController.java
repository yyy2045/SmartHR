package com.smarthr.controller;

import com.smarthr.config.JwtAuthenticationFilter.CustomAuthDetails;
import com.smarthr.dto.AuthResponse;
import com.smarthr.dto.LoginRequest;
import com.smarthr.dto.RegisterRequest;
import com.smarthr.dto.UnifiedResponse;
import com.smarthr.entity.User;
import com.smarthr.service.AuthService;
import com.smarthr.service.UserService;
import jakarta.servlet.http.Cookie;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    @Autowired
    private AuthService authService;

    @Autowired
    private UserService userService;

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

    @PostMapping("/logout")
    public UnifiedResponse<String> logout(HttpServletResponse response) {
        // Clear JWT cookie
        Cookie cookie = new Cookie("jwt", "");
        cookie.setHttpOnly(true);
        cookie.setSecure(false);
        cookie.setPath("/");
        cookie.setMaxAge(0);
        response.addCookie(cookie);
        return UnifiedResponse.success("Logged out successfully", null);
    }

    @GetMapping("/me")
    public UnifiedResponse<User> getCurrentUser() {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth == null || !auth.isAuthenticated() || "anonymousUser".equals(auth.getPrincipal())) {
            return UnifiedResponse.error("Not authenticated");
        }

        String email = auth.getName();
        User user = userService.findByEmail(email);
        if (user == null) {
            return UnifiedResponse.error("User not found");
        }

        // 不返回密码
        user.setPassword(null);
        return UnifiedResponse.success(user);
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