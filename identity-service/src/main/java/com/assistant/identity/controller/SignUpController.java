package com.assistant.identity.controller;

import javax.validation.Valid;

import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.PostMapping;

import com.assistant.identity.model.SignUpRequest;
import com.assistant.identity.model.SignUpResponse;
import com.assistant.identity.service.SignUpService;

@RestController
public class SignUpController {
    
    private SignUpService signUpService;;

    @PostMapping("/signup")
    public SignUpResponse signUp(@Valid @RequestBody SignUpRequest signUpRequest) {
        return signUpService.signUp(signUpRequest);
    }
}
