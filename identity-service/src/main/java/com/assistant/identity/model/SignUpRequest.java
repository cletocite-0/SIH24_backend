package com.assistant.identity.model;

import javax.validation.constraints.Email;
import javax.validation.constraints.NotBlank;
import javax.validation.constraints.Size;

import com.assistant.identity.constants.MessageConstants;

public class SignUpRequest {

    @Email(message = MessageConstants.EMAIL_VALIDATION_ERROR)
    @NotBlank(message = MessageConstants.EMAIL_BLANK_ERROR)
    private String email;

    @NotBlank(message = MessageConstants.PASSWORD_BLANK_ERROR)
    @Size(min = 6, message = MessageConstants.PASSWORD_LENGTH_ERROR)
    private String password;
    
}
