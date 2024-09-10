package com.assistant.identity.utils;


import java.security.NoSuchAlgorithmException;
import java.security.spec.InvalidKeySpecException;
import java.util.Properties;

import javax.crypto.SecretKey;
import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.PBEKeySpec;

import com.assistant.identity.constants.MessageConstants;

public class PasswordUtils {
	
	private static final int iterationsCount;
    private static final int passwordKeyLength;
    static {
        Properties properties = new Properties();
        try {
            properties.load(PasswordUtils.class.getClassLoader().getResourceAsStream("application.properties"));
            iterationsCount = Integer.parseInt(properties.getProperty("iteration.count", "1000"));
            passwordKeyLength = Integer.parseInt(properties.getProperty("password.key.length", "512"));
        } catch (Exception e) {
            throw new RuntimeException(MessageConstants.CONFIGURATION_FAIL, e);
        }
    }

    /**
	 * Hashes the given password using PBKDF2 with HMAC SHA512 algorithm.
	 *
	 * @param password The password to be hashed.
	 * @param salt The salt value used for hashing.
	 * @return The hashed password as a byte array.
	 * @throws RuntimeException If password hashing fails due to NoSuchAlgorithmException or InvalidKeySpecException.
	 */
    public static byte[] hashPassword(String password, byte[] salt) {
		char[] passwordChars = password.toCharArray();
		try {
			SecretKeyFactory skf = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA512");
			PBEKeySpec spec = new PBEKeySpec(passwordChars, salt, iterationsCount, passwordKeyLength);
			SecretKey key = skf.generateSecret(spec);
			byte[] res = key.getEncoded();
			return res;
		} catch (NoSuchAlgorithmException | InvalidKeySpecException e) {
			throw new RuntimeException(MessageConstants.PASSWORD_HASHING_FAILED);
		}
	}
}