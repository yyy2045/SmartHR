package com.smarthr.controller;

import com.smarthr.dto.UnifiedResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/config")
public class SystemConfigController {

    @Value("${ai.service.url:http://localhost:8001}")
    private String aiServiceUrl;

    private static final Map<String, Object> llmConfig = new HashMap<>();
    private static boolean llmConfigInitialized = false;

    @GetMapping("/llm")
    public UnifiedResponse<Map<String, Object>> getLlmConfig() {
        if (!llmConfigInitialized) {
            llmConfig.put("baseUrl", "https://api.deepseek.com");
            llmConfig.put("modelName", "deepseek-chat");
            llmConfig.put("apiKey", "");
            llmConfigInitialized = true;
        }
        return UnifiedResponse.success(new HashMap<>(llmConfig));
    }

    @PostMapping("/llm")
    public UnifiedResponse<Map<String, Object>> saveLlmConfig(@RequestBody Map<String, Object> config) {
        llmConfig.putAll(config);
        return UnifiedResponse.success(new HashMap<>(llmConfig));
    }
}