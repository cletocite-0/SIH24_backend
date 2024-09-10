package com.assistant.identity.utils;

import javax.crypto.Cipher;
import javax.crypto.SecretKey;
import javax.crypto.spec.SecretKeySpec;

import com.assistant.identity.constants.MessageConstants;

import java.util.Base64;
import java.util.Properties;

public class AESUtils {

    private final static String secretString;

    static {
        Properties properties = new Properties();
        try {
            properties.load(PasswordUtils.class.getClassLoader().getResourceAsStream("application.properties"));
            secretString = properties.getProperty("secret.string");
        } catch (Exception e) {
            throw new RuntimeException(MessageConstants.CONFIGURATION_FAIL, e);
        }
    }

    private static final SecretKey key = getKeyFromString(secretString);

    // Method to decrypt data using AES
    public static String decrypt(String encryptedData) throws Exception {
        Cipher cipher = Cipher.getInstance("AES");
        cipher.init(Cipher.DECRYPT_MODE, key);
        byte[] decodedData = Base64.getDecoder().decode(encryptedData);
        System.out.println(decodedData);
        System.out.println(key.toString());
        byte[] decryptedData = cipher.doFinal(decodedData);
        return new String(decryptedData);
    }

    // Method to get SecretKey from a string
    public static SecretKey getKeyFromString(String keyStr) {
        byte[] decodedKey = Base64.getDecoder().decode(keyStr);
        return new SecretKeySpec(decodedKey, 0, decodedKey.length, "AES");
    }
}
