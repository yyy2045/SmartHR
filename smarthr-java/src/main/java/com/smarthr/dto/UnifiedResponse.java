package com.smarthr.dto;

import lombok.Data;
import lombok.AllArgsConstructor;
import lombok.NoArgsConstructor;

@Data
@AllArgsConstructor
@NoArgsConstructor
public class UnifiedResponse<T> {
    private int code;
    private String message;
    private T data;

    public static <T> UnifiedResponse<T> success(T data) {
        return new UnifiedResponse<>(200, "Success", data);
    }

    public static <T> UnifiedResponse<T> success(String message, T data) {
        return new UnifiedResponse<>(200, message, data);
    }

    public static <T> UnifiedResponse<T> error(int code, String message) {
        return new UnifiedResponse<>(code, message, null);
    }

    public static <T> UnifiedResponse<T> error(String message) {
        return new UnifiedResponse<>(500, message, null);
    }
}