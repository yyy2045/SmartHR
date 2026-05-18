package com.smarthr.exception;

import com.smarthr.dto.UnifiedResponse;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.util.HashMap;
import java.util.Map;

@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(GlobalException.class)
    public ResponseEntity<UnifiedResponse<Void>> handleGlobalException(GlobalException ex) {
        UnifiedResponse<Void> response = UnifiedResponse.error(ex.getCode(), ex.getMessage());
        return ResponseEntity.status(ex.getCode()).body(response);
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<UnifiedResponse<Map<String, String>>> handleValidationExceptions(
            MethodArgumentNotValidException ex) {
        Map<String, String> errors = new HashMap<>();
        ex.getBindingResult().getAllErrors().forEach((error) -> {
            String fieldName = ((FieldError) error).getField();
            String errorMessage = error.getDefaultMessage();
            errors.put(fieldName, errorMessage);
        });
        UnifiedResponse<Map<String, String>> response = UnifiedResponse.error(400, "Validation failed");
        response.setData(errors);
        return ResponseEntity.badRequest().body(response);
    }

    @ExceptionHandler(BadCredentialsException.class)
    public ResponseEntity<UnifiedResponse<Void>> handleBadCredentialsException(BadCredentialsException ex) {
        UnifiedResponse<Void> response = UnifiedResponse.error(401, "Invalid credentials");
        return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(response);
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<UnifiedResponse<Void>> handleGenericException(Exception ex) {
        UnifiedResponse<Void> response = UnifiedResponse.error(500, "Internal server error: " + ex.getMessage());
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(response);
    }
}