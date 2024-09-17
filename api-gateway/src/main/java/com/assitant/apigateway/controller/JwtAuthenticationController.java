package com.assitant.apigateway.controller;

import java.io.UnsupportedEncodingException;
import java.net.URI;
import java.net.URISyntaxException;
import java.util.ArrayList;
import java.util.List;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.server.ServerHttpRequest;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestTemplate;

import com.assitant.apigateway.config.AppConfig;
import com.assitant.apigateway.enums.CustomErrorMessage;
import com.assitant.apigateway.model.AuthenticationStatus;
import com.assitant.apigateway.model.ErrorResponse;
import com.assitant.apigateway.model.JwtRequest;
import com.assitant.apigateway.model.JwtResponse;
import com.assitant.apigateway.model.ResponseDTO;
import com.assitant.apigateway.security.JwtTokenUtil;
import com.assitant.apigateway.constants.MessageConstants;




@RestController(MessageConstants.API_GATEWAY_PREDICATE)
public class JwtAuthenticationController {

	@Autowired
	private final JwtTokenUtil jwtTokenUtil;

	@Autowired
	private AppConfig appConfig;

	public JwtAuthenticationController(JwtTokenUtil jwtTokenUtil) {
		this.jwtTokenUtil = jwtTokenUtil;
	}

	/**
	 * @throws URISyntaxException
	 * @throws UnsupportedEncodingException 
	 */
	@PostMapping(value = "/authenticate")
	public ResponseEntity<ResponseDTO> createAuthenticationToken(@RequestBody JwtRequest authenticationRequest)
			throws URISyntaxException, UnsupportedEncodingException {
		AuthenticationStatus status = authenticate(authenticationRequest);
		ResponseDTO responseDto = new ResponseDTO();
		if (!status.getIsAuthenticated()) {
			List<String> details = new ArrayList<>();	
			details.add(status.getMessage());
			responseDto.setStatus(HttpStatus.UNAUTHORIZED);
			responseDto.setErrorObject(new ErrorResponse(CustomErrorMessage.INVALID_CREDENTIALS.name(), 
					CustomErrorMessage.INVALID_CREDENTIALS.getMessage()));
			return new ResponseEntity<ResponseDTO>(responseDto, HttpStatus.UNAUTHORIZED);
		}
		final String token = jwtTokenUtil.generateToken(authenticationRequest.getUsername());
		responseDto.setStatus(HttpStatus.OK);
		responseDto.setDataObject(new JwtResponse(token));
		return new ResponseEntity<>(responseDto, HttpStatus.OK);
	}

	@PostMapping(value = "/logout")
	public ResponseEntity<ResponseDTO> logout(ServerHttpRequest request) throws URISyntaxException {
		String jwtToken = request.getHeaders().get(HttpHeaders.AUTHORIZATION).get(0).split(" ")[1];
		// blackListingService.blackListJwt(jwtToken);
		final String baseUrl = appConfig.getIdentityServiceURL() + "/update-fcmToken";
		JwtRequest jwtRequest = new JwtRequest();
		jwtRequest.setUsername(jwtTokenUtil.getUsernameFromToken(jwtToken));
		RestTemplate restTemplate = new RestTemplate();
		URI uri = new URI(baseUrl);
		restTemplate.postForEntity(uri, jwtRequest, null);
		ResponseDTO responseDto = new ResponseDTO();
		responseDto.setStatus(HttpStatus.OK);
		responseDto.setDataObject(CustomErrorMessage.LOGOUT_SUCCESS.name());
		return new ResponseEntity<ResponseDTO>(responseDto, HttpStatus.OK);
	}

	private AuthenticationStatus authenticate(JwtRequest jwtRequest) throws URISyntaxException {
		AuthenticationStatus status;
		final String baseUrl = appConfig.getIdentityServiceURL() + "/userAuthentication";
		URI uri = new URI(baseUrl);
		RestTemplate restTemplate = new RestTemplate();

		try {
			ResponseEntity<String> result = restTemplate.postForEntity(uri, jwtRequest, String.class);
			if (result.getStatusCode().equals(HttpStatus.OK)) {
				status = new AuthenticationStatus(true, "Authentication Successful");
			} else {
				status = new AuthenticationStatus(false, "Error occuring while login. Please retry.");
			}
		} catch (HttpClientErrorException ex) {
			if (HttpStatus.UNAUTHORIZED.equals(ex.getStatusCode())) {
				status = new AuthenticationStatus(false, "Invalid Username/Password");
			} else {
				throw ex;
			}
		}

		return status;
	}
}