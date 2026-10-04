-- Hackathon Management System - MySQL 8+
DROP DATABASE IF EXISTS hackathon_db;
CREATE DATABASE hackathon_db;
USE hackathon_db;

CREATE TABLE participants (
    participant_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name      VARCHAR(100) NOT NULL,
    email          VARCHAR(120) NOT NULL UNIQUE,
    college        VARCHAR(120) NOT NULL
);

CREATE TABLE hackathons (
    hackathon_id  INT AUTO_INCREMENT PRIMARY KEY,
    title         VARCHAR(150) NOT NULL,
    start_date    DATE NOT NULL,
    end_date      DATE NOT NULL,
    max_team_size TINYINT NOT NULL DEFAULT 4,
    CONSTRAINT chk_dates CHECK (end_date >= start_date),
    CONSTRAINT chk_size  CHECK (max_team_size BETWEEN 1 AND 6)
);

CREATE TABLE teams (
    team_id      INT AUTO_INCREMENT PRIMARY KEY,
    hackathon_id INT NOT NULL,
    team_name    VARCHAR(80) NOT NULL,
    UNIQUE (hackathon_id, team_name),
    FOREIGN KEY (hackathon_id) REFERENCES hackathons(hackathon_id) ON DELETE CASCADE
);

CREATE TABLE team_members (
    team_id        INT NOT NULL,
    participant_id INT NOT NULL,
    role           ENUM('leader','member') NOT NULL DEFAULT 'member',
    PRIMARY KEY (team_id, participant_id),
    FOREIGN KEY (team_id)        REFERENCES teams(team_id) ON DELETE CASCADE,
    FOREIGN KEY (participant_id) REFERENCES participants(participant_id) ON DELETE CASCADE
);

CREATE TABLE submissions (
    submission_id INT AUTO_INCREMENT PRIMARY KEY,
    team_id       INT NOT NULL UNIQUE,              -- one submission per team
    project_title VARCHAR(150) NOT NULL,
    repo_url      VARCHAR(255) NOT NULL,
    FOREIGN KEY (team_id) REFERENCES teams(team_id) ON DELETE CASCADE
);

CREATE TABLE judges (
    judge_id   INT AUTO_INCREMENT PRIMARY KEY,
    judge_name VARCHAR(100) NOT NULL,
    email      VARCHAR(120) NOT NULL UNIQUE,
    expertise  VARCHAR(100)
);

CREATE TABLE scores (
    score_id      INT AUTO_INCREMENT PRIMARY KEY,
    submission_id INT NOT NULL,
    judge_id      INT NOT NULL,
    innovation    TINYINT NOT NULL CHECK (innovation   BETWEEN 0 AND 10),
    technical     TINYINT NOT NULL CHECK (technical    BETWEEN 0 AND 10),
    presentation  TINYINT NOT NULL CHECK (presentation BETWEEN 0 AND 10),
    UNIQUE (submission_id, judge_id),            -- a judge scores a project once
    FOREIGN KEY (submission_id) REFERENCES submissions(submission_id) ON DELETE CASCADE,
    FOREIGN KEY (judge_id)      REFERENCES judges(judge_id) ON DELETE CASCADE
);

-- ---------- VIEWS ----------
CREATE VIEW v_team_sizes AS
SELECT t.team_id, t.team_name, h.title AS hackathon, COUNT(tm.participant_id) AS members
FROM teams t
JOIN hackathons h ON h.hackathon_id = t.hackathon_id
LEFT JOIN team_members tm ON tm.team_id = t.team_id
GROUP BY t.team_id, t.team_name, h.title;

CREATE VIEW v_leaderboard AS
SELECT t.hackathon_id, t.team_name, s.project_title,
       COUNT(sc.score_id) AS judges_count,
       ROUND(AVG(sc.innovation + sc.technical + sc.presentation), 2) AS avg_total,   -- out of 30
       RANK() OVER (PARTITION BY t.hackathon_id
                    ORDER BY AVG(sc.innovation + sc.technical + sc.presentation) DESC) AS team_rank
FROM submissions s
JOIN teams t   ON t.team_id = s.team_id
JOIN scores sc ON sc.submission_id = s.submission_id
GROUP BY t.hackathon_id, t.team_name, s.project_title;

-- ---------- TRIGGERS ----------
DELIMITER //
CREATE TRIGGER trg_team_full
BEFORE INSERT ON team_members
FOR EACH ROW
BEGIN
    DECLARE v_max INT;
    DECLARE v_cnt INT;
    SELECT h.max_team_size INTO v_max
    FROM teams t JOIN hackathons h ON h.hackathon_id = t.hackathon_id
    WHERE t.team_id = NEW.team_id;
    SELECT COUNT(*) INTO v_cnt FROM team_members WHERE team_id = NEW.team_id;
    IF v_cnt >= v_max THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Team is full';
    END IF;
END//

CREATE TRIGGER trg_one_team_per_hackathon
BEFORE INSERT ON team_members
FOR EACH ROW
BEGIN
    DECLARE v_dup INT;
    SELECT COUNT(*) INTO v_dup
    FROM team_members tm
    JOIN teams t1 ON t1.team_id = tm.team_id
    JOIN teams t2 ON t2.team_id = NEW.team_id AND t2.hackathon_id = t1.hackathon_id
    WHERE tm.participant_id = NEW.participant_id;
    IF v_dup > 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Participant already in a team for this hackathon';
    END IF;
END//

-- ---------- STORED PROCEDURE (transaction) ----------
CREATE PROCEDURE register_team(
    IN p_hackathon INT, IN p_team_name VARCHAR(80), IN p_leader INT)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;
    START TRANSACTION;
        INSERT INTO teams (hackathon_id, team_name) VALUES (p_hackathon, p_team_name);
        INSERT INTO team_members (team_id, participant_id, role)
        VALUES (LAST_INSERT_ID(), p_leader, 'leader');
    COMMIT;
END//
DELIMITER ;
