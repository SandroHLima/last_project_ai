-- School Grades Database Schema
-- MySQL compatible

-- Drop tables if exist (for clean setup)
DROP TABLE IF EXISTS avaliacoes;
DROP TABLE IF EXISTS alunos_turmas;
DROP TABLE IF EXISTS turmas;
DROP TABLE IF EXISTS disciplinas;
DROP TABLE IF EXISTS users;

-- Users table (students and teachers)
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    role ENUM('student', 'teacher') NOT NULL,
    INDEX idx_users_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Disciplinas (subjects) table
CREATE TABLE disciplinas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Turmas (classes) table  
CREATE TABLE turmas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Alunos_Turmas association table (students in classes)
CREATE TABLE alunos_turmas (
    user_id INT NOT NULL,
    turma_id INT NOT NULL,
    PRIMARY KEY (user_id, turma_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (turma_id) REFERENCES turmas(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Avaliacoes (evaluations/grades) table
CREATE TABLE avaliacoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    disciplina_id INT NOT NULL,
    turma_id INT NOT NULL,
    modulo VARCHAR(100) NOT NULL,
    descricao VARCHAR(255) NOT NULL,
    valor FLOAT NOT NULL,
    date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by INT,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (disciplina_id) REFERENCES disciplinas(id) ON DELETE CASCADE,
    FOREIGN KEY (turma_id) REFERENCES turmas(id) ON DELETE CASCADE,
    FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_avaliacoes_user (user_id),
    INDEX idx_avaliacoes_disciplina (disciplina_id),
    INDEX idx_avaliacoes_turma (turma_id),
    INDEX idx_avaliacoes_modulo (modulo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
