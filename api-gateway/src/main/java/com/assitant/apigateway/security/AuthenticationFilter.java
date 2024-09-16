package com.assitant.apigateway.security;

import java.util.Objects;
import org.apache.commons.lang3.StringUtils;
import org.springframework.cloud.context.config.annotation.RefreshScope;
import org.springframework.cloud.gateway.filter.GatewayFilter;
import org.springframework.cloud.gateway.filter.factory.AbstractGatewayFilterFactory;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;

import com.assitant.apigateway.config.*;
import com.assitant.apigateway.enums.CustomErrorMessage;
import com.assitant.apigateway.exceptions.JwtTokenMissingException;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.ObjectWriter;

import lombok.extern.slf4j.Slf4j;
import reactor.core.publisher.Mono;

import com.assitant.apigateway.model.ErrorResponse;
import com.assitant.apigateway.model.ResponseDTO;

@RefreshScope
@Component
@Slf4j
public class AuthenticationFilter extends AbstractGatewayFilterFactory<AuthenticationFilter.Config> {

	private final RouterValidator routerValidator;
	private final JwtTokenUtil jwtTokenUtil;
	private final JwtConfig jwtConfig;

	public AuthenticationFilter(RouterValidator routerValidator, JwtTokenUtil jwtTokenUtil, JwtConfig config) {
		super(Config.class);
		this.routerValidator = routerValidator;
		this.jwtTokenUtil = jwtTokenUtil;
		this.jwtConfig = config;
	}

	@Override
	public GatewayFilter apply(Config config) {
		return ((exchange, chain) -> {
			ServerWebExchange exchangeNew = exchange;
			if (routerValidator.isSecured.test(exchange.getRequest())) {
				try {

					if (!exchange.getRequest().getHeaders().containsKey(HttpHeaders.AUTHORIZATION)) {
						throw new JwtTokenMissingException(CustomErrorMessage.MISSING_AUTHORISATION_HEADER.name());
					}

					String authHeader = Objects
							.requireNonNull(exchange.getRequest().getHeaders().get(HttpHeaders.AUTHORIZATION)).get(0);
					jwtTokenUtil.validateToken(authHeader);

                    SessionEntity sessionEntity = jwtTokenUtil.getUserSession(authHeader);
					ObjectMapper mapper = new ObjectMapper();
					String sessionString = mapper.writeValueAsString(sessionEntity);
					ServerHttpRequest request = exchange.getRequest().mutate()
							.header("X-Request-user-session", sessionString).build();
					exchangeNew = exchange.mutate().request(request).build();

				} catch (Exception ex) {
					String jsonString = StringUtils.EMPTY;
					ServerHttpResponse response = exchange.getResponse();
					ResponseDTO errorResponse = new ResponseDTO();
					if(ex instanceof JwtTokenMissingException) {
						response.setStatusCode(HttpStatus.BAD_REQUEST);
						errorResponse.setStatus(HttpStatus.BAD_REQUEST);
					}
					else {
						response.setStatusCode(HttpStatus.UNAUTHORIZED);
						errorResponse.setStatus(HttpStatus.UNAUTHORIZED);
					}
					CustomErrorMessage customErrorMessage = CustomErrorMessage.getCustomErrorMessage(ex.getMessage());
					ObjectWriter ow = new ObjectMapper().writer().withDefaultPrettyPrinter();
					errorResponse.setErrorObject(new ErrorResponse(customErrorMessage.name(), customErrorMessage.getMessage()));
					try {
						jsonString = ow.writeValueAsString(errorResponse);
					} catch (JsonProcessingException e) {
						e.printStackTrace();
					}
					DataBuffer buffer = response.bufferFactory().wrap(jsonString.getBytes());
                    return response.writeWith(Mono.just(buffer));
				}
			}
			return chain.filter(exchangeNew);

		});
	}

	public static class Config {
	}
}