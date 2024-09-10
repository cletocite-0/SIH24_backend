package com.assitant.apigateway.model;

import java.io.Serializable;

import lombok.Data;
import lombok.ToString;

@Data
@ToString
public class UserDetails implements Serializable {
	
	private String email;

}