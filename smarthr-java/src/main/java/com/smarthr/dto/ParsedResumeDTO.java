package com.smarthr.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;
import java.util.List;
import java.util.Map;

@Data
public class ParsedResumeDTO {
    @JsonProperty("candidate_name")
    private String candidateName;

    private String email;

    private String phone;

    private List<String> skills;

    private List<Map<String, Object>> experience;

    private List<Map<String, Object>> education;

    private String summary;
}