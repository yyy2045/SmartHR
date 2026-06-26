package com.smarthr.config;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import jakarta.annotation.PostConstruct;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;
import java.util.function.Function;

@Component
public class JwtTokenProvider {

    @Value("${jwt.secret}")
    private String jwtSecret;

    @Value("${jwt.expiration}")
    private long jwtExpiration;

    // HS256 要求密钥至少 256 bit = 32 字节。
    private static final int MIN_SECRET_BYTES = 32;

    // 仓库/模板中出现过的已知占位/默认密钥，禁止在任何环境直接使用，避免“默认密钥=任何人可签发合法 token”。
    private static final Set<String> KNOWN_WEAK_SECRETS = Set.of(
            "k9L3x8NpQ2rT6vYwZ7aBcDeFgHiJkLmNoPqRsTuVwXyZ",
            "smarthr-secret-key-change-in-production",
            "YOUR_JWT_SECRET_KEY_CHANGE_THIS_TO_A_LONG_RANDOM_STRING",
            "your_secure_jwt_secret_key_min_32_chars"
    );

    /**
     * 启动时强校验 JWT 密钥强度。任何不满足条件的密钥都会让应用启动失败（fail-closed），
     * 阻止使用空密钥、过短密钥或仓库里泄露过的默认密钥上线。
     */
    @PostConstruct
    public void validateSecret() {
        if (jwtSecret == null || jwtSecret.isBlank()) {
            throw new IllegalStateException(
                    "JWT 密钥未配置：请通过环境变量 JWT_SECRET 设置一个至少 32 字节的随机字符串。");
        }
        if (KNOWN_WEAK_SECRETS.contains(jwtSecret.trim())) {
            throw new IllegalStateException(
                    "检测到使用了已知默认/占位 JWT 密钥，禁止上线：请将 JWT_SECRET 改为独有的随机字符串。");
        }
        int byteLength = jwtSecret.getBytes(StandardCharsets.UTF_8).length;
        if (byteLength < MIN_SECRET_BYTES) {
            throw new IllegalStateException(
                    "JWT 密钥过短（当前 " + byteLength + " 字节，至少需要 " + MIN_SECRET_BYTES
                            + " 字节）：请将 JWT_SECRET 设置为更长的随机字符串。");
        }
    }

    private SecretKey getSigningKey() {
        byte[] keyBytes = jwtSecret.getBytes(StandardCharsets.UTF_8);
        return Keys.hmacShaKeyFor(keyBytes);
    }

    public String extractEmail(String token) {
        return extractClaim(token, Claims::getSubject);
    }

    public String extractRole(String token) {
        return extractClaim(token, claims -> claims.get("role", String.class));
    }

    public Long extractUserId(String token) {
        return extractClaim(token, claims -> {
            Object userId = claims.get("userId");
            if (userId instanceof Integer) {
                return ((Integer) userId).longValue();
            } else if (userId instanceof Long) {
                return (Long) userId;
            }
            return 0L;
        });
    }

    public Long extractCompanyId(String token) {
        return extractClaim(token, claims -> {
            Object companyId = claims.get("companyId");
            if (companyId instanceof Integer) {
                return ((Integer) companyId).longValue();
            } else if (companyId instanceof Long) {
                return (Long) companyId;
            }
            return null;
        });
    }

    public Date extractExpiration(String token) {
        return extractClaim(token, Claims::getExpiration);
    }

    public <T> T extractClaim(String token, Function<Claims, T> claimsResolver) {
        final Claims claims = extractAllClaims(token);
        return claimsResolver.apply(claims);
    }

    private Claims extractAllClaims(String token) {
        return Jwts.parser()
                .verifyWith(getSigningKey())
                .build()
                .parseSignedClaims(token)
                .getPayload();
    }

    private Boolean isTokenExpired(String token) {
        return extractExpiration(token).before(new Date());
    }

    public String generateToken(String email, Long userId, String role, Long companyId) {
        Map<String, Object> claims = new HashMap<>();
        claims.put("userId", userId);
        claims.put("role", role);
        claims.put("companyId", companyId);
        return createToken(claims, email);
    }

    private String createToken(Map<String, Object> claims, String subject) {
        return Jwts.builder()
                .claims(claims)
                .subject(subject)
                .issuedAt(new Date(System.currentTimeMillis()))
                .expiration(new Date(System.currentTimeMillis() + jwtExpiration))
                .signWith(getSigningKey())
                .compact();
    }

    public Boolean validateToken(String token, String email) {
        final String extractedEmail = extractEmail(token);
        return (email != null && email.equals(extractedEmail) && !isTokenExpired(token));
    }

    public Boolean validateToken(String token) {
        try {
            extractAllClaims(token);
            return !isTokenExpired(token);
        } catch (Exception e) {
            return false;
        }
    }
}