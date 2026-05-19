package com.smarthr.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.info.Contact;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class OpenApiConfig {

    @Bean
    public OpenAPI customOpenAPI() {
        return new OpenAPI()
                .info(new Info()
                        .title("SmartHR API")
                        .version("1.0.0")
                        .description("SmartHR 多智能体招聘平台后端 API 文档")
                        .contact(new Contact()
                                .name("SmartHR Team")
                                .email("support@smarthr.com")));
    }
}