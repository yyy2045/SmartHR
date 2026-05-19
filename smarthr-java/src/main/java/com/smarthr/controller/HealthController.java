package com.smarthr.controller;

import com.smarthr.dto.UnifiedResponse;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import javax.sql.DataSource;
import java.sql.Connection;
import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api")
public class HealthController {

    @Autowired
    private DataSource dataSource;

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    @GetMapping("/health")
    public UnifiedResponse<Map<String, String>> health() {
        Map<String, String> status = new HashMap<>();
        status.put("status", "UP");
        status.put("service", "SmartHR Java Backend");
        return UnifiedResponse.success(status);
    }

    @GetMapping("/health/db-status")
    public UnifiedResponse<Map<String, Object>> dbStatus() {
        Map<String, Object> status = new HashMap<>();

        // MySQL
        try (Connection conn = dataSource.getConnection()) {
            status.put("mysql", conn.isValid(1));
        } catch (Exception e) {
            status.put("mysql", false);
            status.put("mysql_error", e.getMessage());
        }

        // Redis
        try {
            String pong = redisTemplate.getConnectionFactory().getConnection().ping();
            status.put("redis", "PONG".equalsIgnoreCase(pong));
        } catch (Exception e) {
            status.put("redis", false);
            status.put("redis_error", e.getMessage());
        }

        // Chroma - 通过Python服务检测
        status.put("chroma", true); // 默认true，由Python服务实际检测

        return UnifiedResponse.success(status);
    }
}