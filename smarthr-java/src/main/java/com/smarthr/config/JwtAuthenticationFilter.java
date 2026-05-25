package com.smarthr.config;

import com.smarthr.entity.User;
import com.smarthr.service.UserService;
import jakarta.servlet.http.Cookie;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.Collections;

@Component
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    @Autowired
    private JwtTokenProvider jwtTokenProvider;

    @Autowired
    private UserService userService;

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {

        // 优先从 Header 的 Authorization Bearer 获取
        String authHeader = request.getHeader("Authorization");
        String token = null;
        String email = null;
        String role = null;
        Long userId = null;
        Long companyId = null;

        if (authHeader != null && authHeader.startsWith("Bearer ")) {
            token = authHeader.substring(7);
            try {
                email = jwtTokenProvider.extractEmail(token);
                role = jwtTokenProvider.extractRole(token);
                userId = jwtTokenProvider.extractUserId(token);
                companyId = jwtTokenProvider.extractCompanyId(token);
            } catch (Exception e) {
                logger.error("Error extracting claims from token: " + e.getMessage());
            }
        }

        // 如果 Header 没有，尝试从 Cookie 获取
        if (email == null && token == null) {
            Cookie[] cookies = request.getCookies();
            if (cookies != null) {
                for (Cookie cookie : cookies) {
                    if ("jwt".equals(cookie.getName())) {
                        token = cookie.getValue();
                        try {
                            email = jwtTokenProvider.extractEmail(token);
                            role = jwtTokenProvider.extractRole(token);
                            userId = jwtTokenProvider.extractUserId(token);
                            companyId = jwtTokenProvider.extractCompanyId(token);
                        } catch (Exception e) {
                            logger.error("Error extracting claims from cookie token: " + e.getMessage());
                        }
                        break;
                    }
                }
            }
        }

        if (email != null && SecurityContextHolder.getContext().getAuthentication() == null) {
            // 先验证 token 签名有效性，再查数据库（避免 token 对应用户不存在时抛异常）
            if (jwtTokenProvider.validateToken(token, email)) {
                try {
                    UserDetails userDetails = userService.loadUserByUsername(email);
                    // 创建带角色的 authorities
                    SimpleGrantedAuthority authority = new SimpleGrantedAuthority("ROLE_" + (role != null ? role.toUpperCase() : "USER"));
                    UsernamePasswordAuthenticationToken authToken = new UsernamePasswordAuthenticationToken(
                            userDetails, null, Collections.singletonList(authority));
                    // 将 userId, companyId, role 存入 details
                    authToken.setDetails(new CustomAuthDetails(request, userId, companyId, role));
                    SecurityContextHolder.getContext().setAuthentication(authToken);
                } catch (UsernameNotFoundException e) {
                    // 用户 token 合法但账号不存在/被删除，应拒绝访问而非静默放行
                    logger.warn("Token valid but user not found: " + email);
                    response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
                    response.getWriter().write("{\"error\":\"User account not found\"}");
                    response.setContentType("application/json");
                    return;
                }
            }
        }

        filterChain.doFilter(request, response);
    }

    // 自定义 AuthDetails，携带额外信息
    public static class CustomAuthDetails {
        private final HttpServletRequest request;
        private final Long userId;
        private final Long companyId;
        private final String role;

        public CustomAuthDetails(HttpServletRequest request, Long userId, Long companyId, String role) {
            this.request = request;
            this.userId = userId;
            this.companyId = companyId;
            this.role = role;
        }

        public HttpServletRequest getRequest() { return request; }
        public Long getUserId() { return userId; }
        public Long getCompanyId() { return companyId; }
        public String getRole() { return role; }
    }
}