package com.assitant.apigateway.enums;

import java.util.HashMap;
import java.util.Map;

public enum CustomErrorMessage {
	
	INVALID_CREDENTIALS("Invalid Credentials."),
	LOGOUT_SUCCESS("Logged out Successfully."),
	INCORRECT_AUTHENTICATION_STRUCTURE("Incorrect Authentication Structure"),
	INVALID_JWT_TOKEN("Invalid JWT token"),
	INVALID_JWT_SIGNATURE("Invalid JWT signature"),
	EXPIRED_JWT_TOKEN("Expired JWT token"),
	UNSUPPORTED_JWT_TOKEN("Unsupported JWT token"),
	JWT_CLAIMS_STRING_IS_EMPTY("JWT claims string is empty"),
	MISSING_AUTHORISATION_HEADER("Missing Authorisation Header");
	
	
	private String message;
	
	CustomErrorMessage(String message) {
		this.message=message;;
	}
	
	private static Map<String, CustomErrorMessage> _map = new HashMap<>();
	static {
		for (CustomErrorMessage errorMsg : CustomErrorMessage.values()) {
			_map.put(errorMsg.name(),errorMsg );
		}
	}
	
	public static CustomErrorMessage getCustomErrorMessage(String name) {
	  return _map.get(name);
	}
	
	public String getMessage() {
		return message;
	}

}
