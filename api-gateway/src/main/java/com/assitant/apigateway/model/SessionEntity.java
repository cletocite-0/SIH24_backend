package com.assitant.apigateway.model;

import java.io.Serializable;
import java.util.UUID;

import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.ToString;

@Data
@NoArgsConstructor
@ToString
public class SessionEntity implements Serializable{
	
	private UUID userId;
	
	private UUID parentId;
	
	private UserDetails userRoleDetails;
	
	private long duration;
	
}

