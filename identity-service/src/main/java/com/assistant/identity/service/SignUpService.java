package com.assistant.identity.service;

import javax.validation.Valid;

import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.assistant.identity.model.SignUpRequest;
import com.assistant.identity.model.SignUpResponse;

@RestController
@RequestMapping("/api/auth")
public class SignUpService {

    private SignUpService signUpService;

    @PostMapping("/signup")
    public SignUpResponse signUp(@Valid @RequestBody SignUpRequest signUpRequest) {;
        return new SignUpResponse();
    }
    
}
