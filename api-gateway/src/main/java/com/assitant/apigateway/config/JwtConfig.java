package com.assitant.apigateway.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

@Configuration
@ConfigurationProperties("jwt")
public class JwtConfig {

    private String secret;
    private long accessValidity; // Validity for access token
    private long refreshValidity; // Validity for refresh token

    public void setSecret(String secret) {
        this.secret = secret;
    }

    public void setAccessValidity(long accessValidity) {
        this.accessValidity = accessValidity;
    }

    public void setRefreshValidity(long refreshValidity) {
        this.refreshValidity = refreshValidity;
    }

    public String getSecret() {
        return secret;
    }

    public long getAccessValidity() {
        return accessValidity;
    }

    public long getRefreshValidity() {
        return refreshValidity;
    }
}
