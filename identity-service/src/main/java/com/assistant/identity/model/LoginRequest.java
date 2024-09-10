package com.assistant.identity.model;

import javax.validation.constraints.Size;
import javax.validation.constraints.Email;
import javax.validation.constraints.NotBlank;

import com.assistant.identity.constants.MessageConstants;

import lombok.Data;

@Data
public class LoginRequest {

    @NotBlank(message = MessageConstants.PASSWORD_BLANK_ERROR)
    @Size(min = 6, message = MessageConstants.PASSWORD_LENGTH_ERROR)
    private String password;

    @Email(message = MessageConstants.EMAIL_VALIDATION_ERROR)
    @NotBlank(message = MessageConstants.EMAIL_BLANK_ERROR)
    private String email;

    private String salt;

}