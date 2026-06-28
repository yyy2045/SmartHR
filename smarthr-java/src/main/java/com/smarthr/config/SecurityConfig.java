package com.smarthr.config;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.AuthenticationProvider;
import org.springframework.security.authentication.dao.DaoAuthenticationProvider;
import org.springframework.security.config.annotation.authentication.configuration.AuthenticationConfiguration;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

import java.util.Arrays;
import java.util.List;

@Configuration
@EnableWebSecurity
@EnableMethodSecurity
public class SecurityConfig {

    @Autowired
    private JwtAuthenticationFilter jwtAuthenticationFilter;

    @Autowired
    private UserDetailsService userDetailsService;

    // 接口文档（Swagger / Knife4j / OpenAPI）默认对外关闭，避免生产环境匿名枚举全部接口结构。
    // 仅当显式设置 app.api-docs.public=true（如本地开发）时才放行。
    @Value("${app.api-docs.public:false}")
    private boolean apiDocsPublic;

    // 接口文档相关路径，统一管控放行/拒绝。
    private static final String[] API_DOC_PATHS = {
            "/doc.html",               // 根路径下的 knife4j
            "/api/doc.html",           // api 前缀下的 knife4j
            "/swagger-ui.html",        // 根路径下的 swagger
            "/api/swagger-ui.html",    // api 前缀下的 swagger
            "/swagger-ui/**",          // 静态资源
            "/api/swagger-ui/**",
            "/v3/api-docs/**",         // 接口数据
            "/api/v3/api-docs/**",
            "/swagger-resources/**",
            "/webjars/**",
            "/swagger-ui/index.html",  // springdoc-openapi
            "/api/swagger-ui/index.html"
    };

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
                .cors(cors -> cors.configurationSource(corsConfigurationSource()))
                .csrf(csrf -> csrf.disable())
                .authorizeHttpRequests(auth -> {
                    // 1. 放行登录、注册、健康检查接口
                    auth.requestMatchers("/api/auth/**", "/health", "/api/health", "/api/health/db-status").permitAll();

                    // 2. 接口文档：默认拒绝，显式开启时才放行（生产保持关闭）
                    if (apiDocsPublic) {
                        auth.requestMatchers(API_DOC_PATHS).permitAll();
                    } else {
                        auth.requestMatchers(API_DOC_PATHS).denyAll();
                    }

                    // 3. 其他所有 /api/** 的业务接口必须登录认证
                    auth.requestMatchers("/api/**").authenticated();

                    // 4. 剩下的杂项请求（如静态资源等）直接放行
                    auth.anyRequest().permitAll();
                })
                .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authenticationProvider(authenticationProvider())
                .addFilterBefore(jwtAuthenticationFilter, UsernamePasswordAuthenticationFilter.class);

        return http.build();
    }

    @Bean
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration configuration = new CorsConfiguration();
        // 允许具体来源，不能用 * 当 withCredentials=true
        configuration.setAllowedOriginPatterns(corsAllowedOriginPatterns());
        configuration.setAllowedMethods(Arrays.asList("GET", "POST", "PUT", "DELETE", "OPTIONS"));
        configuration.setAllowedHeaders(Arrays.asList("*"));
        configuration.setAllowCredentials(true);  // 允许携带凭证
        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", configuration);
        return source;
    }

    private List<String> corsAllowedOriginPatterns() {
        String configured = System.getenv("CORS_ALLOWED_ORIGIN_PATTERNS");
        if (configured != null && !configured.isBlank()) {
            return Arrays.stream(configured.split(","))
                    .map(String::trim)
                    .filter(item -> !item.isEmpty())
                    .toList();
        }
        return Arrays.asList(
                "http://localhost:*",
                "http://127.0.0.1:*",
                "http://60.205.203.166",
                "https://smarthr.top",
                "https://www.smarthr.top"
        );
    }

    @Bean
    public AuthenticationProvider authenticationProvider() {
        DaoAuthenticationProvider authProvider = new DaoAuthenticationProvider();
        authProvider.setUserDetailsService(userDetailsService);
        authProvider.setPasswordEncoder(passwordEncoder());
        return authProvider;
    }

    @Bean
    public AuthenticationManager authenticationManager(AuthenticationConfiguration config) throws Exception {
        return config.getAuthenticationManager();
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }
}
