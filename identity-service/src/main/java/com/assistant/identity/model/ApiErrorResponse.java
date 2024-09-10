package com.assistant.identity.model;

import lombok.AllArgsConstructor;
import lombok.Data;

@Data
@AllArgsConstructor
public class ApiErrorResponse {

    
    int errorCode;

    private String errorDescription;

}