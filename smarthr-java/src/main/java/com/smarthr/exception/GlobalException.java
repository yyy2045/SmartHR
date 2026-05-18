package com.smarthr.exception;

import lombok.Getter;

@Getter
public class GlobalException extends RuntimeException {
    private final int code;
    private final String message;

    public GlobalException(int code, String message) {
        super(message);
        this.code = code;
        this.message = message;
    }

    public GlobalException(String message) {
        this(500, message);
    }
}