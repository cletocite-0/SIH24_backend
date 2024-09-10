package com.assitant.apigateway.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;

import lombok.Data;

@Configuration
@Data
public class AppConfig {

	@Value("${app.identity-service.url}")
	private String identityServiceURL;

	@Value("${app.user-service.url}")
	private String userServiceURL;

}