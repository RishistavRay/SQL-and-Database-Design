-- assumptions: 
--  1) spending limit and donations are in integer values only
--  2) Not all candidates will have debates
--  3) each candidate has one election only
--  4) moderator 
--  5) non-random and valid values are inputted for names, emails, addresses
--  6) Anyone can donate to the campaign, even the candidate themselves
--  7) Only those who run a campaign have a debate (not all candidates
--     have a election campaign)
--  8) only 2 candidates have a debate at a time
--  9) all other assumptions will be mentioned throughout the schema. 

-- could not enforce such constraints:
-- 1) Time for activities and debates were set so that they are in
--    one hour block slots, explained later, but cannot check for schedule
--    conflicts thouroughly
-- 2) having more than 2 candidates in a debate

--  did not enforce some constraints:
--  1) people can have any values for emails, address, names 
--     such as error, Not Available, random characters, etc. 
--     We assume that these checks are done by someone else
--  2) we did not enforce the constraint that the moderator cannot be 
--     a candidate, donor, volunteer or staff. As long as its anyone but
--     the candidates in that debate its okay.



DROP SCHEMA IF EXISTS election cascade;
CREATE SCHEMA election;
SET search_path TO election;
-------------------------------------------------

CREATE TABLE PeopleType (
    id SERIAL PRIMARY KEY, -- id will be automaticall generated
    email VARCHAR(100) NOT NULL,
    name VARCHAR(100) NOT NULL, -- extra string

    category VARCHAR(100) NOT NULL,

    unique(id, category),
    unique(email), -- unique emails
    -- only these people can be included in this table
    check(category IN ('candidate', 'volunteer', 'staff', 'moderator'))


);

-- All the candidates that have an election.
-- Generally, only one election is allowed per candidate
CREATE TABLE ElectionCampaign (
    campaignID INTEGER PRIMARY KEY,
    spendingLimit INTEGER NOT NULL,
    category VARCHAR(100),

    
    check(spendingLimit >0), -- checking that the allowed budget exists
    FOREIGN KEY (campaignID, category) REFERENCES PeopleType(id, category),
    check(category IN ('candidate') )
);

-- maximizing the number of candidates in a debate to 2
CREATE TABLE Debates (
    debateID SERIAL NOT NULL PRIMARY KEY,

    firstCandidate INTEGER NOT NULL REFERENCES ElectionCampaign(campaignID),
    secondCandidate INTEGER NOT NULL REFERENCES ElectionCampaign(campaignID),
    modID INTEGER NOT NULL REFERENCES PeopleType(id),

    timeDebate TIMESTAMP NOT NULL,

    -- regular checks
    check(secondCandidate > firstCandidate),
    check(modID != firstCandidate),
    check(modID != secondCandidate),

    -- only allowed between these hours and should start at integer time
    check(timeDebate::time BETWEEN '8:00' and '20:00'),
    check( (EXTRACT(second FROM timeDebate) =0) AND 
        (EXTRACT(minute FROM timeDebate)= 0) )

);

-- donor information is stored here, anyone can donate to anyone
CREATE TABLE Donors (
    donorID INTEGER PRIMARY KEY,
    email VARCHAR(100) NOT NULL,
    name VARCHAR(100) NOT NULL,
    address VARCHAR(100) NOT NULL,
    isOrganization BOOLEAN NOT NULL,

    unique(email),
    check(donorID >=0)
);

-- another table to store all the donations made with a transaction id
CREATE TABLE DonationsMade(
    transactionID SERIAL PRIMARY KEY,

    donorID INTEGER REFERENCES Donors(donorID),

    donatedCampaign INTEGER REFERENCES ElectionCampaign(campaignID),
    donationAmount INTEGER NOT NULL,

    check(donationAmount >0)

);


-- list of workers, has to be entered in PeopleType first. 
CREATE TABLE Workers (
    workerID INTEGER PRIMARY KEY REFERENCES PeopleType(id),
    email VARCHAR(100) NOT NULL REFERENCES PeopleType(email),

    category VARCHAR(100) NOT NULL,
    check(category IN ('volunteer', 'staff')),
    unique(email)
    
);

-- schedule for the workers in time slots of 1 hour. a worker can have
-- continuous shifts but has to start the last one at 18:00.
CREATE TABLE WorkerSchedule(
    workerID INTEGER NOT NULL REFERENCES Workers(workerID),
    campaignID INTEGER NOT NULL REFERENCES ElectionCampaign(campaignID),
    shiftTime TIMESTAMP NOT NULL,
    activityType VARCHAR(100) NOT NULL,

    PRIMARY KEY (workerID, shiftTime, campaignID),

    -- only allowed between these hours and should start at integer time
    check(activityType IN ('door-to-door canvassing', 'phone banks')),
    check(shiftTime::time BETWEEN '8:00' AND '18:00'),
    check( (EXTRACT(second FROM shiftTime) =0) AND 
        (EXTRACT(minute FROM shiftTime)= 0) )


);