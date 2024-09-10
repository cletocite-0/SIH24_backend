package com.assistant.identity.repository;

import java.util.Optional;

import com.assistant.identity.model.User;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface UserRepository extends JpaRepository<User, Long> {

  Optional<User> findByEmail(String email);
  Optional<User> findByPassword(String password);
  void updatePassword(String user_id,String password);
}
