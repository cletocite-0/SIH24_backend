package com.assitant.apigateway.security;

import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.function.Predicate;

@Component
public class RouterValidator {

	public static final List<String> openApiEndpoints = List.of("/api/users/register",
			"/authenticate","/identity/resetPassword",
			"/identity/forgetPassword","/identity/otpValidation", "/api/users/validateInviteCode");

	public Predicate<ServerHttpRequest> isSecured = request -> openApiEndpoints.stream()
			.noneMatch(uri -> request.getURI().getPath().equals(uri));

}
	 