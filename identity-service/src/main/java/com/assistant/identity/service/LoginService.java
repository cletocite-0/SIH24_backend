package com.assistant.identity.service;


import javax.persistence.EntityNotFoundException;

import org.apache.commons.codec.binary.Hex;

import lombok.AllArgsConstructor;

import org.springframework.stereotype.Service;

import com.assistant.identity.constants.MessageConstants;
import com.assistant.identity.exceptions.AuthException;
import com.assistant.identity.model.LoginRequest;
import com.assistant.identity.model.LoginResponse;
import com.assistant.identity.model.ResetPasswordRequest;
import com.assistant.identity.model.ResetPasswordResponse;
import com.assistant.identity.model.User;
import com.assistant.identity.repository.UserRepository;
import com.assistant.identity.utils.AESUtils;
import com.assistant.identity.utils.PasswordUtils;

@Service
@AllArgsConstructor
public class LoginService {
    
    private UserRepository userRepository;
	private String decryptedPassword;

	/**
	 * Authenticates a user by performing a login operation.
	 *
	 * @param loginRequest The login request containing the user's email and password.
	 * @return The login response containing the user's information and a token.
	 * @throws AuthException If the user is not found or the credentials are invalid.
	 */
    public LoginResponse login(LoginRequest loginRequest) {

		User user = userRepository.findByEmail(loginRequest.getEmail())
		.orElseThrow(() -> new EntityNotFoundException("User not found"));

		try {
			decryptedPassword = AESUtils.decrypt(loginRequest.getPassword());
			System.out.println(decryptedPassword);
		}
		catch(Exception e) {
			System.out.println(e);
			e.printStackTrace();
			throw new AuthException(MessageConstants.AES_DECRYPTION_ERROR+e);
		}

		if(isPasswordValid(decryptedPassword, user, loginRequest.getSalt().getBytes())) {
			return new LoginResponse(user.getUser_id(),user.getPassword());
		}
		throw new AuthException(MessageConstants.INVALID_CREDENTIALS);

    }

	/**
	 * Checks if the provided password is valid for the given user.
	 *
	 * @param password The password to be validated.
	 * @param user The user for whom the password is being validated.
	 * @return {@code true} if the password is valid, {@code false} otherwise.
	 */
	private boolean isPasswordValid(String password, User user, byte[] salt) { 
		byte[] hashedBytes = PasswordUtils.hashPassword(password, salt); 
		String hashedPasswordString = Hex.encodeHexString(hashedBytes); 
		return hashedPasswordString.equals(user.getPassword()); 
		}

	public ResetPasswordResponse resetPassword(ResetPasswordRequest resetPasswordRequest) {
		ResetPasswordResponse resetPasswordResponse = new ResetPasswordResponse();

		if(resetPasswordRequest.getNewPassword().equals(resetPasswordRequest.getOldPassword())) {
			resetPasswordResponse.setStatusCode(400);
			resetPasswordResponse.setMessage("New password cannot be same as old password");
			return resetPasswordResponse;
		}
		
		User user = userRepository.findByPassword(resetPasswordRequest.getOldPassword())
		.orElseThrow(() -> new EntityNotFoundException(MessageConstants.OLD_PASSWORD_ERROR));

		try {
			userRepository.updatePassword(user.getUser_id(),resetPasswordRequest.getNewPassword());
			resetPasswordResponse.setStatusCode(200);
			resetPasswordResponse.setMessage(MessageConstants.PASSWORD_RESET_SUCCESS);
		} catch (Exception e) {
			resetPasswordResponse.setStatusCode(500);
			resetPasswordResponse.setMessage(MessageConstants.PASSWORD_RESET_SUCCESS + e.getMessage());
		}

		return	resetPasswordResponse;
	}

}