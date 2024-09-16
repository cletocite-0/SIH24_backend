package com.assitant.apigateway.security;

import java.io.UnsupportedEncodingException;
import java.net.URI;
import java.net.URISyntaxException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.Date;
import java.util.function.Function;

import org.springframework.http.ResponseEntity;

import org.springframework.http.converter.json.Jackson2ObjectMapperBuilder;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import com.assitant.apigateway.config.AppConfig;
import com.assitant.apigateway.config.JwtConfig;
import com.assitant.apigateway.enums.CustomErrorMessage;
import com.assitant.apigateway.exceptions.JwtTokenIncorrectStructureException;
import com.assitant.apigateway.exceptions.JwtTokenMalformedException;
import com.assitant.apigateway.exceptions.JwtTokenMissingException;
import com.assitant.apigateway.model.ResponseDTO;
import com.assitant.apigateway.model.SessionEntity;
import com.assitant.apigateway.model.UserDetails;
import com.fasterxml.jackson.databind.ObjectMapper;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.ExpiredJwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.MalformedJwtException;
import io.jsonwebtoken.SignatureAlgorithm;
import io.jsonwebtoken.SignatureException;
import io.jsonwebtoken.UnsupportedJwtException;

import lombok.AllArgsConstructor;

@Component
@AllArgsConstructor
public class JwtTokenUtil {

	private final JwtConfig config;

	// private BlackListingService blackListingService;
	
	// private SessionRedisCacheService sessionRedisCacheService;

	private AppConfig appConfig;


	public String generateToken(String userId) throws URISyntaxException, UnsupportedEncodingException {
    // Fetch user details from user service
    final String baseUrl = appConfig.getIdentityServiceURL() + "/email?emailId=" + URLEncoder.encode(userId, StandardCharsets.UTF_8.toString());
    URI uri = new URI(baseUrl);
    RestTemplate restTemplate = new RestTemplate();
    ResponseEntity<ResponseDTO> responseEntity = restTemplate.getForEntity(uri, ResponseDTO.class);
    ResponseDTO responseDto = responseEntity.getBody();
    ObjectMapper mapper = Jackson2ObjectMapperBuilder.json().build();
    UserDetails userDetails = mapper.convertValue(responseDto.getDataObject(), UserDetails.class);

    // Create claims with user details
    Claims claims = Jwts.claims().setSubject(userId);
    claims.put("email", userDetails.getEmail());
    // Add any other relevant user details to claims

    long nowMillis = System.currentTimeMillis();
    long expMillis = nowMillis + config.getValidity() * 1000 * 60;
    Date exp = new Date(expMillis);

    // Generate JWT with claims
    return Jwts.builder()
            .setClaims(claims)
            .setIssuedAt(new Date(nowMillis))
            .setExpiration(exp)
            .signWith(SignatureAlgorithm.HS512, config.getSecret())
            .compact();
}

	// retrieve username from jwt token
	public String getUsernameFromToken(String token) {
		return getClaimFromToken(token, Claims::getSubject);
	}

	public <T> T getClaimFromToken(String token, Function<Claims, T> claimsResolver) {
		final Claims claims = getAllClaimsFromToken(token);
		return claimsResolver.apply(claims);
	}

	// for retrieveing any information from token we will need the secret key
	private Claims getAllClaimsFromToken(String token) {
		return Jwts.parser().setSigningKey(config.getSecret()).parseClaimsJws(token).getBody();
	}

	// check if the token has expired
	private Boolean isTokenExpired(String token) {
		final Date expiration = getExpirationDateFromToken(token);
		return expiration.before(new Date());
	}

	// retrieve expiration date from jwt token
	public Date getExpirationDateFromToken(String token) {
		return getClaimFromToken(token, Claims::getExpiration);
	}

	public void validateToken(final String header) throws JwtTokenMalformedException, JwtTokenMissingException {
		try {
			String[] parts = header.split(" ");
			if (parts.length != 2 || !"Bearer".equals(parts[0])) {
				throw new JwtTokenIncorrectStructureException(CustomErrorMessage.INCORRECT_AUTHENTICATION_STRUCTURE.name());
			}

			Jwts.parser().setSigningKey(config.getSecret()).parseClaimsJws(parts[1]);
			// String blackListedToken = blackListingService.getJwtBlackList(parts[1]);
			// if (blackListedToken != null) {
			// 	throw new JwtTokenMalformedException(CustomErrorMessage.INVALID_JWT_TOKEN.name());
			// }
		} catch (SignatureException ex) {
			throw new JwtTokenMalformedException(CustomErrorMessage.INVALID_JWT_SIGNATURE.name());
		} catch (MalformedJwtException ex) {
			throw new JwtTokenMalformedException(CustomErrorMessage.INVALID_JWT_TOKEN.name());
		} catch (ExpiredJwtException ex) {
			throw new JwtTokenMalformedException(CustomErrorMessage.EXPIRED_JWT_TOKEN.name());
		} catch (UnsupportedJwtException ex) {
			throw new JwtTokenMalformedException(CustomErrorMessage.UNSUPPORTED_JWT_TOKEN.name());
		} catch (IllegalArgumentException ex) {
			throw new JwtTokenMissingException(CustomErrorMessage.JWT_CLAIMS_STRING_IS_EMPTY.name());
		}
	}
}