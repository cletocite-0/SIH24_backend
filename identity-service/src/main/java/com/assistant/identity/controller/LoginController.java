package com.assistant.identity.controller;

import javax.validation.Valid;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RestController;



import com.assistant.identity.model.LoginRequest;
import com.assistant.identity.model.LoginResponse;
import com.assistant.identity.model.ResetPasswordRequest;
import com.assistant.identity.model.ResetPasswordResponse;
import com.assistant.identity.service.LoginService;

@RestController
@RequestMapping("/api/auth")
public class LoginController {
    @Autowired
    private LoginService authService;

	/**
	 * Authenticates the user and returns a token.
	 *
	 * @param loginRequest The login request object containing the user's credentials.
	 * @return The login response DTO containing the token.
	 */

    @PostMapping("/login")
    public LoginResponse login(@Valid @RequestBody LoginRequest loginRequest) {
        return authService.login(loginRequest);
    }

    @PostMapping("/reset-password")
    public ResetPasswordResponse resetPassword(@Valid @RequestBody ResetPasswordRequest resetPasswordRequest) {
        return authService.resetPassword(resetPasswordRequest);
    }

}