SET search_path TO election;

-- inserting people into one table
INSERT INTO PeopleType(email, name, category) VALUES
    ('1@google.com', 'Brad Smith',  'volunteer'),
    ('2@google.com', 'Torn Smith', 'staff'),
    ('3@google.com', 'Brad Torn', 'volunteer'),
    ('4@google.com', 'Tom Cruise', 'staff'),
    ('5@google.com', 'Led Zep', 'candidate'),
    ('6@google.com', 'Lex Luther', 'candidate'),
    ('7@google.com', 'Max Vers', 'candidate'),
    ('8@google.com', 'Okay Man', 'candidate');

-- every candidate has the same budget
INSERT INTO ElectionCampaign(campaignID, spendingLimit, category) VALUES
    (5, 500000, 'candidate'),
    (6, 500000, 'candidate'),
    (7, 500000, 'candidate');

-- info for all the donors
INSERT INTO Donors(donorID, email, name, address, isOrganization) VALUES
    (1, 'bruh@google.com', 'Col Smith', 'University of Toronto', TRUE),
    (2, 'lol@google.com', 'Stan Brown', 'Dupont Station', FALSE),
    (3, 'smh@google.com','Bradlye Cooper',  'Sanford Fleming', FALSE),
    (4, 'haha@google.com', 'Random People', 'On the Street 55', TRUE);



-- Sample transactions
INSERT INTO DonationsMade(donorID, donatedCampaign, donationAmount) VALUES
    (1, 5, 50),
    (1, 5, 50),
    (2, 5, 100),
    (3, 6, 50),
    (3, 6, 100),
    (4, 6, 50),
    (4, 7, 100);


-- The staff and volunteers in the system
INSERT INTO Workers(workerID, email, category) VALUES
    (1, '1@google.com',  'volunteer'),
    (3, '3@google.com', 'volunteer'),
    (2, '2@google.com', 'staff'),
    (4, '4@google.com', 'staff');


-- Entering some debates
INSERT INTO
    Debates(firstCandidate, secondCandidate, modID, timeDebate) VALUES
        (5, 7, 8, '2023-04-04 10:00:00'),
        (6, 7, 8, '2023-04-06 10:00:00');

-- sample schedules for workers
INSERT INTO WorkerSchedule VALUES
    (1, 5, '2023-04-04 9:00:00', 'door-to-door canvassing'),
    (1, 6, '2023-04-04 10:00:00', 'phone banks'),
    --
    (2, 5, '2023-04-10 14:00:00', 'door-to-door canvassing'),
    (2, 6, '2023-04-10 15:00:00', 'phone banks'),
    --
    (3, 5, '2023-04-09 8:00:00', 'phone banks'),
    (3, 6, '2023-04-09 9:00:00', 'phone banks'),
    (3, 7, '2023-04-09 10:00:00', 'phone banks'),
    (3, 7, '2023-04-09 11:00:00', 'door-to-door canvassing'),
    --
    (4, 6, '2023-04-20 9:00:00', 'phone banks'),
    (4, 7, '2023-04-20 17:00:00', 'phone banks');

       