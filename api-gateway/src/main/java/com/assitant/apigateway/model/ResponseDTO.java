package com.assitant.apigateway.model;

import java.io.Serializable;

import org.springframework.http.HttpStatus;

import lombok.Data;

@Data
public class ResponseDTO implements Serializable{
	
	private HttpStatus status;
	
	private ErrorResponse errorObject;
	
	private Object dataObject;
	
}


