-- SmartHR Database Initialization Script
-- This script is automatically executed when MySQL container starts

-- Create database if not exists
CREATE DATABASE IF NOT EXISTS smarthr;
USE smarthr;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    name VARCHAR(100),
    role VARCHAR(50) DEFAULT 'HR',  -- HR, INTERVIEWER, ADMIN
    company_id BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_email (email),
    INDEX idx_company_id (company_id)
);

-- Companies table
CREATE TABLE IF NOT EXISTS companies (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    industry VARCHAR(100),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Jobs table
CREATE TABLE IF NOT EXISTS jobs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    requirements TEXT,
    skills JSON,  -- JSON array of required skills
    experience_years INT,
    education_level VARCHAR(100),
    salary_range VARCHAR(100),
    company_id BIGINT,
    status VARCHAR(50) DEFAULT 'OPEN',  -- OPEN, CLOSED, DRAFT
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_company_id (company_id),
    INDEX idx_status (status),
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE SET NULL
);

-- Resumes table
CREATE TABLE IF NOT EXISTS resumes (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    candidate_name VARCHAR(100),
    email VARCHAR(255),
    phone VARCHAR(50),
    file_path VARCHAR(500),
    raw_text TEXT,
    parsed_data JSON,  -- Structured parsed data
    match_score DECIMAL(5,2),
    job_id BIGINT,
    user_id BIGINT,  -- HR who uploaded
    status VARCHAR(50) DEFAULT 'UPLOADED',  -- UPLOADED, PARSED, MATCHED, REVIEWED
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_job_id (job_id),
    INDEX idx_user_id (user_id),
    INDEX idx_match_score (match_score),
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE SET NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Interview sessions table
CREATE TABLE IF NOT EXISTS interview_sessions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    session_id VARCHAR(100) UNIQUE NOT NULL,
    job_id BIGINT,
    resume_id BIGINT,
    user_id BIGINT,  -- Interviewer/HR conducting the interview
    status VARCHAR(50) DEFAULT 'IN_PROGRESS',  -- IN_PROGRESS, COMPLETED, ABANDONED
    current_question_index INT DEFAULT 0,
    interview_history JSON,  -- Array of Q&A pairs
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    INDEX idx_session_id (session_id),
    INDEX idx_job_id (job_id),
    INDEX idx_resume_id (resume_id),
    INDEX idx_status (status),
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE SET NULL,
    FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE SET NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Interview reports table
CREATE TABLE IF NOT EXISTS interview_reports (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    session_id BIGINT NOT NULL,
    overall_score DECIMAL(5,2),
    skill_score DECIMAL(5,2),
    behavior_score DECIMAL(5,2),
    experience_score DECIMAL(5,2),
    recommendation VARCHAR(50),  -- STRONG_HIRE, HIRE, NO_HIRE, WEAK_NO_HIRE
    report_data JSON,  -- Full structured report
    summary TEXT,  -- Executive summary
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session_id (session_id),
    FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE
);

-- Knowledge base documents table
CREATE TABLE IF NOT EXISTS knowledge_documents (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    document_id VARCHAR(100) UNIQUE NOT NULL,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500),
    file_type VARCHAR(50),  -- PDF, DOCX, TXT
    company_id BIGINT,
    total_chunks INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_document_id (document_id),
    INDEX idx_company_id (company_id),
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);

-- Insert sample data for testing
INSERT INTO companies (name, industry, description) VALUES
('TechCorp Inc.', 'Technology', 'Leading technology company specializing in AI and cloud solutions'),
('DataDriven LLC', 'Data Analytics', 'Data analytics and machine learning consulting firm');

INSERT INTO users (email, password, name, role, company_id) VALUES
('admin@smarthr.com', '$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZRGdjGj/n3.rsA0p5g8F5p5g5F5Ka', 'Admin User', 'ADMIN', 1),
('hr@smarthr.com', '$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZRGdjGj/n3.rsA0p5g8F5p5g5F5Ka', 'HR Manager', 'HR', 1);

-- Sample job postings
INSERT INTO jobs (title, description, requirements, skills, experience_years, education_level, company_id) VALUES
('Senior Python Developer', 'We are looking for a Senior Python Developer to join our team.', '5+ years of Python development experience', '["Python", "FastAPI", "LangChain", "PostgreSQL"]', 5, 'Bachelor', 1),
('Machine Learning Engineer', 'Join our ML team to build cutting-edge AI models.', 'Experience with ML frameworks and deployment', '["Python", "TensorFlow", "PyTorch", "MLOps"]', 3, 'Master', 1);

SELECT 'Database initialization completed successfully!' AS status;