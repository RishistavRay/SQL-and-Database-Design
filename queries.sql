SET search_path to election;


--------- query 1 --------------------------------


REVOKE ALL ON
    PeopleType, ElectionCampaign, Debates, Donors, DonationsMade, 
    Workers, WorkerSchedule
    FROM dadooshr;

GRANT SELECT ON Donors, DonationsMade, ElectionCampaign TO dadooshr;

--organizational donations
CREATE TEMPORARY VIEW OrgDonations AS
SELECT donatedCampaign, SUM(donationAmount) AS organizationSum
FROM Donors JOIN DonationsMade ON DonationsMade.donorID=Donors.donorID
WHERE isOrganization =TRUE
GROUP BY donatedCampaign;

--individual donations
CREATE TEMPORARY VIEW IndDonations AS
SELECT donatedCampaign, SUM(donationAmount) AS individualSum
FROM Donors JOIN DonationsMade ON DonationsMade.donorID=Donors.donorID
WHERE isOrganization=FALSE
GROUP BY donatedCampaign;


-- first get all campaign ids, join with individual donations
-- and then the organizational. the empty values are 0
SELECT campaignID, individualSum, organizationSum
FROM (ElectionCampaign LEFT JOIN IndDonations ON 
	ElectionCampaign.campaignID=IndDonations.donatedCampaign) JOIN 
	OrgDonations ON ElectionCampaign.campaignID=OrgDonations.donatedCampaign
ORDER BY IndDonations.donatedCampaign ASC;

DROP VIEW IF EXISTS IndDonations, OrgDonations; 




--------- query 2 --------------------------------

REVOKE ALL ON
    PeopleType, ElectionCampaign, Debates, Donors, DonationsMade, 
    Workers, WorkerSchedule
    FROM dadooshr;

GRANT SELECT ON WorkerSchedule, Workers, ElectionCampaign TO dadooshr;

CREATE TEMPORARY VIEW AllPossibilities AS
SELECT workerID, ElectionCampaign.campaignID as campaignID
FROM ElectionCampaign, Workers;


CREATE TEMPORARY VIEW ActuallyWorking AS
SELECT workerID, campaignID
FROM WorkerSchedule;


CREATE TEMPORARY VIEW NotWorking AS
(SELECT * 
	FROM AllPossibilities)
EXCEPT
(SELECT * 
	FROM ActuallyWorking);

CREATE TEMPORARY VIEW EveryCampaignWorker AS
(SELECT workerID FROM Workers)
EXCEPT
(SELECT workerID FROM NotWorking);

SELECT workerID, email
FROM Workers NATURAL JOIN EveryCampaignWorker;

DROP VIEW IF EXISTS EveryCampaignWorker, NotWorking, ActuallyWorking, 
	AllPossibilities;


-------- query 3 --------------------------------


REVOKE ALL ON
    PeopleType, ElectionCampaign, Debates, Donors, DonationsMade, 
    Workers, WorkerSchedule
    FROM dadooshr;

GRANT SELECT ON ElectionCampaign, Debates, PeopleType TO dadooshr;

-- find all possible pairs
CREATE TEMPORARY VIEW AllPossibilities AS
SELECT ElectionCampaign.campaignID AS firstCandidate, EC2.campaignID AS secondCandidate
FROM ElectionCampaign, ElectionCampaign EC2
WHERE EC2.campaignID > ElectionCampaign.campaignID;

-- find actually existing pairs
CREATE TEMPORARY VIEW ActualPairs AS
SELECT firstCandidate, secondCandidate
FROM Debates;


-- find invalid candidates
CREATE TEMPORARY VIEW NotInAnyDebate AS
(SELECT * 
	FROM AllPossibilities)
EXCEPT
(SELECT * 
	FROM ActualPairs);

--find the ones not in every debate
CREATE TEMPORARY VIEW NotEvery AS
(SELECT firstCandidate AS campaignID
	FROM NotInAnyDebate)
UNION
(SELECT secondCandidate AS campaignID 
	FROM NotInAnyDebate);

-- subtract not in every from all to find every candidate
CREATE TEMPORARY VIEW EveryDebateAtendee AS
(SELECT campaignID 
	FROM ElectionCampaign)
EXCEPT
(SELECT * 
	FROM NotEvery);

SELECT id, name, email
FROM PeopleType JOIN EveryDebateAtendee ON campaignID= id;

DROP VIEW IF EXISTS EveryDebateAtendee, NotEvery, NotInAnyDebate, 
	ActualPairs, AllPossibilities;

-------------------------------------------



