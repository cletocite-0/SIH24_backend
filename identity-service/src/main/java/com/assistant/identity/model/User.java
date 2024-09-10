package com.assistant.identity.model;

import lombok.Data;
import lombok.AllArgsConstructor;

@Data
@AllArgsConstructor
public class User {

    private String user_id;
    private String email;
    private String password;
    private boolean isGoogleAuthenticated;
    
}
