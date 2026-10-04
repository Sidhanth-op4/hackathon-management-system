USE hackathon_db;

INSERT INTO participants (full_name, email, college) VALUES
('Aarav Sharma','aarav@mail.com','ABC Institute'),
('Riya Patil','riya@mail.com','ABC Institute'),
('Kunal Deshmukh','kunal@mail.com','XYZ College'),
('Sneha Joshi','sneha@mail.com','XYZ College'),
('Omkar More','omkar@mail.com','PQR University'),
('Isha Kulkarni','isha@mail.com','PQR University'),
('Tanmay Rao','tanmay@mail.com','ABC Institute'),
('Neha Singh','neha@mail.com','LMN Tech');

INSERT INTO hackathons (title, start_date, end_date, max_team_size) VALUES
('CodeStorm 2026', '2026-10-01', '2026-12-31', 4);

CALL register_team(1, 'Neural Ninjas', 1);
CALL register_team(1, 'Byte Builders', 3);
CALL register_team(1, 'Green Coders', 5);

INSERT INTO team_members (team_id, participant_id) VALUES
(1,2),(1,7),(2,4),(3,6),(3,8);

INSERT INTO submissions (team_id, project_title, repo_url) VALUES
(1,'Crop Disease Detector','https://github.com/example/crop-detector'),
(2,'Campus Event Hub','https://github.com/example/event-hub'),
(3,'Waste Pickup Tracker','https://github.com/example/waste-tracker');

INSERT INTO judges (judge_name, email, expertise) VALUES
('Dr. Mehta','mehta@mail.com','AI'),
('Prof. Iyer','iyer@mail.com','Databases');

INSERT INTO scores (submission_id, judge_id, innovation, technical, presentation) VALUES
(1,1,9,8,8),(1,2,8,9,7),
(2,1,7,7,8),(2,2,8,8,7),
(3,1,8,6,7),(3,2,7,7,8);

SELECT * FROM v_team_sizes;
SELECT * FROM v_leaderboard ORDER BY team_rank;
