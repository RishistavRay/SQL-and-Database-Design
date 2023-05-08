"""CSC343 Assignment 2

=== CSC343 Winter 2023 ===
Department of Computer Science,
University of Toronto

This code is provided solely for the personal and private use of
students taking the CSC343 course at the University of Toronto.
Copying for purposes other than this use is expressly prohibited.
All forms of distribution of this code, whether as given or with
any changes, are expressly prohibited.

Authors: Danny Heap, Marina Tawfik, and Jacqueline Smith

All of the files in this directory and all subdirectories are:
Copyright (c) 2023 Danny Heap and Jacqueline Smith

=== Module Description ===

This file contains the WasteWrangler class and some simple testing functions.
"""

import datetime as dt
import psycopg2 as pg
import psycopg2.extensions as pg_ext
import psycopg2.extras as pg_extras
from typing import Optional, TextIO


class WasteWrangler:
    """A class that can work with data conforming to the schema in
    waste_wrangler_schema.ddl.

    === Instance Attributes ===
    connection: connection to a PostgreSQL database of a waste management
    service.

    Representation invariants:
    - The database to which connection is established conforms to the schema
      in waste_wrangler_schema.ddl.
    """
    connection: Optional[pg_ext.connection]

    def __init__(self) -> None:
        """Initialize this WasteWrangler instance, with no database connection
        yet.
        """
        self.connection = None

    def connect(self, dbname: str, username: str, password: str) -> bool:
        """Establish a connection to the database <dbname> using the
        username <username> and password <password>, and assign it to the
        instance attribute <connection>. In addition, set the search path
        to waste_wrangler.

        Return True if the connection was made successfully, False otherwise.
        I.e., do NOT throw an error if making the connection fails.

        >>> ww = WasteWrangler()
        >>> ww.connect("csc343h-marinat", "marinat", "")
        True
        >>> # In this example, the connection cannot be made.
        >>> ww.connect("invalid", "nonsense", "incorrect")
        False
        """
        try:
            self.connection = pg.connect(
                dbname=dbname, user=username, password=password,
                options="-c search_path=waste_wrangler"
            )
            return True
        except pg.Error:
            return False

    def disconnect(self) -> bool:
        """Close this WasteWrangler's connection to the database.

        Return True if closing the connection was successful, False otherwise.
        I.e., do NOT throw an error if closing the connection failed.

        >>> ww = WasteWrangler()
        >>> ww.connect("csc343h-marinat", "marinat", "")
        True
        >>> ww.disconnect()
        True
        """
        try:
            if self.connection and not self.connection.closed:
                self.connection.close()
            return True
        except pg.Error:
            return False

    def schedule_trip(self, rid: int, time: dt.datetime) -> bool:
        """Schedule a truck and two employees to the route identified
        with <rid> at the given time stamp <time> to pick up an
        unknown volume of waste, and deliver it to the appropriate facility.

        The employees and truck selected for this trip must be available:
            * They can NOT be scheduled for a different trip from 30 minutes
              of the expected start until 30 minutes after the end time of this
              trip.
            * The truck can NOT be scheduled for maintenance on the same day.

        The end time of a trip can be computed by assuming that all trucks
        travel at an average of 5 kph.

        From the available trucks, pick a truck that can carry the same
        waste type as <rid> and give priority based on larger capacity and
        use the ascending order of ids to break ties.

        From the available employees, give preference based on hireDate
        (employees who have the most experience get priority), and order by
        ascending order of ids in case of ties, such that at least one
        employee can drive the truck type of the selected truck.

        Pick a facility that has the same waste type a <rid> and select the one
        with the lowest fID.

        Return True iff a trip has been scheduled successfully for the given
            route.
        This method should NOT throw an error i.e. if scheduling fails, the
        method should simply return False.

        No changes should be made to the database if scheduling the trip fails.

        Scheduling fails i.e., the method returns False, if any of the following
        is true:
            * If rid is an invalid route ID.
            * If no appropriate truck, drivers or facility can be found.
            * If a trip has already been scheduled for <rid> on the same day
              as <time> (that encompasses the exact same time as <time>).
            * If the trip can't be scheduled within working hours i.e., between
              8:00-16:00.

        While a realistic use case will provide a <time> in the near future, our
        tests could use any valid value for <time>.
        """
        try:
            # TODO: implement this method
            cur = self.connection.cursor()

            # ---------- seeing if the given rid is valid
            cur.execute("""
                SELECT *
                FROM Route
                WHERE rID = %s 
                """, (rid,))
            
            reqRoute = cur.fetchone()
            if reqRoute is None:
                self.connection.rollback()
                cur.close()
                return False
            
            ridCur, waste_t, length = reqRoute #if valid, assign variables

            #--------- check if the required distance and time will be withing the working hours
            beginTime = time
            totalTripTime = int(3600*(length/5))
            endingTime = beginTime + dt.timedelta(seconds = totalTripTime)
            if endingTime.time() > dt.time(hour=16) or beginTime.time() < dt.time(hour = 8):
                self.connection.rollback()
                cur.close()
                return False
            
            #------------------ finding the requirement of the range of time
            max_time = endingTime + dt.timedelta(minutes = 30)
            min_time = beginTime - dt.timedelta(minutes =30)

            
            # ------ check if the route has already happened or will happen today
            cur.execute("SELECT rID FROM Trip WHERE rID = %s AND date(tTIME) = %s", (ridCur, time.date()))

            alreadyExists = cur.fetchone()
            #print(" check if it exists:", alreadyExists)
            if alreadyExists is not None:
                self.connection.rollback()
                cur.close()
                return False 
            
            #------- Finding all Possible Trucks
            cur.execute("""
                CREATE VIEW AvailableTrucks AS
                SELECT tID, capacity, truckType
                FROM TruckType NATURAL JOIN Truck
                WHERE wasteType = %s
                ORDER BY capacity DESC, tID ASC
                """, (waste_t,))
            
            # ----------- Finding Trucks that have the a maintanence scheduled on the same day
            cur.execute("""
                CREATE VIEW OnMain AS
                SELECT AT.tID, AT.capacity, AT.truckType
                FROM AvailableTrucks AT NATURAL JOIN Maintenance Main
                WHERE Main.mDATE = %s
                ORDER BY capacity DESC, tID ASC
                """, (beginTime.date(),))
            
            #-------- Finding Trucks that have the a trip scheduled in the not allowed range time
            cur.execute("""
                CREATE VIEW OnTrip AS
                SELECT AT.tID, AT.capacity, AT.truckType
                FROM AvailableTrucks AT NATURAL JOIN Trip
                WHERE Trip.tTIME BETWEEN %s AND %s
                ORDER BY capacity DESC, tID ASC
                """, (min_time, max_time))
            
            #-------- Now to find all the trucks that are actuall free, we do AvailableTrucks - OnTrip - OnMain
            cur.execute("""
                CREATE VIEW FreeTrucks AS
                (SELECT *
                FROM AvailableTrucks) 
                EXCEPT
                (SELECT *
                FROM OnMain)
                EXCEPT
                (SELECT *
                FROM OnTrip)
                """) 
            
            #----------------------------------------------------
            #---------- Now finding the driver details that can drive the truck of specified trucktypes
            cur.execute("""
                CREATE VIEW CanDrive AS
                SELECT FT.tID as tID, FT.capacity as capacity, FT.truckType as truckType, Employee.eID as eID, Employee.hireDate as hireDate
                FROM Employee NATURAL JOIN Driver NATURAL JOIN FreeTrucks FT
                WHERE Employee.hireDate <= %s
                """, (beginTime.date(),))
            
            #------ Find drivers that have another trip schedule in the +- 30 minute time frame
            cur.execute("""
                CREATE VIEW HaveTrip AS
                SELECT CanDrive.eID as eID
                FROM CanDrive, Trip
                WHERE (Trip.eID1 = CanDrive.eID OR Trip.eID2 = CanDrive.eID) AND Trip.tTIME BETWEEN %s AND %s
                """, (min_time, max_time))
            
            #------ To find all free drivers, we do similar operations for truck: Allpossibledrivers - ones who have trips
            cur.execute("""
                CREATE VIEW FreeDrivers AS
                (SELECT eID
                FROM CanDrive)
                EXCEPT
                (SELECT *
                FROM HaveTrip)
                """)

            #----------------------------------------------------
            #----------- Add the free drivers and Trucks together
            cur.execute("""
                CREATE VIEW AllTDPairs AS
                SELECT eID, tID
                FROM CanDrive NATURAL JOIN FreeDrivers
                ORDER BY capacity DESC, tID, hireDate, eID
                """)

            cur.execute("SELECT * FROM AllTDPairs")
            allpairs = cur.fetchone()
            if allpairs is None: #------- if there are no pairs avaiable
                #print("no pairs exist")
                self.connection.rollback()
                cur.close()
                return False
            
            firsteid, tid = allpairs



            #----------- find next driver to go on trip (if there is no one, then return false)
            #-- First find the drivers that can be on the trip but can't drive the car (assume the first  driver can)

            cur.execute("""
                CREATE VIEW SecondDriversOnTrip AS
                SELECT Driver.eID as eID
                FROM Driver, Trip
                WHERE (Trip.eID1 = Driver.eID OR Trip.eID2 = Driver.eID) AND Trip.tTIME BETWEEN %s AND %s
            """, (min_time, max_time))
            cur.execute("""
                CREATE VIEW FinalDrivers AS
                (SELECT eID
                FROM Driver)
                EXCEPT
                (SELECT *
                FROM SecondDriversOnTrip)
                """) 
            

            #------ now actually finding the next driver
            cur.execute("""
                SELECT eID
                FROM Employee NATURAL JOIN FinalDrivers 
                WHERE hireDate<= %s AND eID != %s
                ORDER BY hireDate, eID
                """, (beginTime.date(), firsteid))

            nextdriver = cur.fetchone()

            if nextdriver is None: # if there is no driver, then return false
                #print("next driver is none")
                self.connection.rollback()
                cur.close()
                return False
            
            secondeid = nextdriver[0]

            #---------------------- FIND FACILITY WTIH LOWEST FID AND MATCHING WASTETYPE
            cur.execute(""" 
                SELECT fID
                FROM Facility 
                WHERE wasteType = %s
                ORDER BY fID
            """, (waste_t,))

            bestfacility = cur.fetchone()

            #error check again
            if bestfacility is None:
                #print("facility is none")
                self.connection.rollback()
                cur.close()
                return False
            
            facility = bestfacility[0]

            #---------------- create the trip in the table
            if(secondeid >firsteid): #putting the largest eid as number one
                inserttrip = tuple([ridCur, tid, beginTime, None, secondeid, firsteid, facility])
            else:
                inserttrip = tuple([ridCur, tid, beginTime, None, firsteid, secondeid, facility]) 

            #insert into the table
            cur.execute("INSERT INTO Trip VALUES (%s, %s, %s, %s, %s, %s, %s)", (inserttrip))


            #cleanup all views

            cur.execute("DROP VIEW FinalDrivers, SecondDriversOnTrip, AllTDPairs")
            
            cur.execute("DROP VIEW FreeDrivers, HaveTrip, CanDrive")
        

            cur.execute("DROP VIEW FreeTrucks, OnTrip, OnMain, AvailableTrucks")
            

            cur.close()
            self.connection.commit()

            return True
            
        except pg.Error as ex:
            # You may find it helpful to uncomment this line while debugging,
            # as it will show you all the details of the error that occurred:
            raise ex
            return False

    def schedule_trips(self, tid: int, date: dt.date) -> int:
        """Schedule the truck identified with <tid> for trips on <date> using
        the following approach:

            1. Find routes not already scheduled for <date>, for which <tid>
               is able to carry the waste type. Schedule these by ascending
               order of rIDs.

            2. Starting from 8 a.m., find the earliest available pair
               of drivers who are available all day. Give preference
               based on hireDate (employees who have the most
               experience get priority), and break ties by choosing
               the lower eID, such that at least one employee can
               drive the truck type of <tid>.

               The facility for the trip is the one with the lowest fID that can
               handle the waste type of the route.

               The volume for the scheduled trip should be null.

            3. Continue scheduling, making sure to leave 30 minutes between
               the end of one trip and the start of the next, using the
               assumption that <tid> will travel an average of 5 kph.
               Make sure that the last trip will not end after 4 p.m.

        Return the number of trips that were scheduled successfully.

        Your method should NOT raise an error.

        While a realistic use case will provide a <date> in the near future, our
        tests could use any valid value for <date>.
        """
        num_changed = 0

        try: 
            # TODO: implement this method
            cur = self.connection.cursor()

            #------ finding routes that do not have a trip
            cur.execute("""
                CREATE VIEW NoRoutes AS
                (select rID from Route)
                EXCEPT
                (select rID FROM Trip WHERE date(tTIME) = %s)
                """, (date,))

            cur.execute("""
                CREATE VIEW ScheduleList AS
                SELECT rID
                FROM TruckType NATURAL JOIN NoRoutes NATURAL JOIN Route NATURAL JOIN Truck
                WHERE tID = %s
                ORDER BY rID
                """,(tid,))


            #----saving the list
            cur.execute("select * from ScheduleList")
            routeList = cur.fetchall()

            #if no routes exist then return 0 (yayy)
            if routeList is None: 
                #cur.execute("DROP VIEW ScheduleList")
                #cur.execute("DROP VIEW NoRoutes")
                
                self.connection.rollback()
                cur.close()
                return 0
            
            #-------defining the initial timing variables
            beginTime = dt.datetime(date.year, date.month, date.day, 8, 0, 0, 0)
            lastTime = dt.datetime(date.year, date.month, date.day, 16, 0, 0, 0)
            endingTime = None

            for routes in routeList:

                rid = routes[0]

                #starting current time
                if endingTime is not None:
                    currentTime = dt.timedelta(minutes=30) + endingTime
                else:
                    currentTime = beginTime

                cur.execute("select length from Route where rID = %s", (rid,))
                rLength = cur.fetchone()

                totalTime = int(3600* (rLength/5))
                #got to convert into seconds
                totalTime = dt.timedelta(seconds=totalTime)

                #---------- if the trip exeeds the max time, then we skip the iteratoin
                if(lastTime < totalTime + beginTime): 
                    self.connection.rollback()
                    #cur.close()
                    continue

                #--------- can drive the truck before the trip and are able to drive that truck type
                cur.execute("""
                    CREATE VIEW CanDrive AS
                    select eID 
                    FROM Driver NATURAL JOIN Truck NATURAL JOIN Employee
                    where hireDate<= %s AND tID = %s
                    """, (date, tid))
                
                #-------- finding the drivers who are on a trip
                cur.execute("""
                    CREATE VIEW OnTrip AS
                    SELECT eID1, eID2
                    from Trip
                    where date(tTIME) = %s
                """, (date,))

                #------finding all the available drivers by subtracting the OnTrip drivers
                cur.execute("""
                    CREATE VIEW AvailableDrivers AS
                    (SELECT *
                    FROM CanDrive)
                    EXCEPT
                    ((SELECT eID2 as eID from OnTrip)
                    UNION
                    (SELECT eID1 as eID from OnTrip))
                """)

                cur.execute("select * from Employee NATURAL JOIN AvailableDrivers ORDER BY hireDate, eID")

                driver= cur.fetchone()

                #--------error checking to see if drivers are even there
                if driver is None:
                    self.connection.rollback()
                    cur.close()
                    return num_changed
                
                firsteid = driver[0]

                #----- now create a list of all other drivers that can be on the truck
                #------ does not have to be able to drive the truck, rather just be free
                cur.execute("""
                    CREATE VIEW SecondList AS
                    (SELECT eID 
                    from Driver 
                    where eID != %s
                    order by eID)
                    EXCEPT
                    ((SELECT eID2 as eID from OnTrip)
                    UNION
                    (SELECT eID1 as eID from OnTrip))
                """, (firsteid))

                cur.execute(" select * from Employee NATURAL JOIN SecondList ORDER BY hireDate, eID")
                secondeid = cur.fetchone()

                #---- error checking for no drivers
                if secondeid is None:
                    self.connection.rollback()
                    cur.close()
                    return num_changed
                
                #----- find the facility in ascending order and take the smallest value of fID
                cur.execute(""" 
                    SELECT fID 
                    FROM Facility NATURAL JOIN Route NATURAL JOIN ScheduleList
                    ORDER BY fID
                    """)
                
                fid = cur.fetchone()

                #-----error check for no facilities available
                if fid is None:
                    self.connection.rollback()
                    cur.close()
                    return num_changed
                
                tupleFID = fid[0]

                if(secondeid >firsteid): #putting the largest eid as number one
                    inserttrip = tuple([rid, tid, currentTime, None, secondeid, firsteid, tupleFID])
                else:
                    inserttrip = tuple([rid, tid, currentTime, None, firsteid, secondeid, tupleFID]) 
                
                #------updating tables
                cur.execute(""" 
                    INSERT INTO Trip
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, inserttrip)
                
                #----- cleanup timee
                cur.execute("DROP VIEW SecondList, AvailableDrivers, OnTrip, CanDrive")
                num_changed +=1
                self.connection.commit()
            

            #--cleanup other views
            cur.execute("DROP VIEW ScheduleList, NoRoutes")
            
            cur.close()
            return num_changed
        except:
            #raise ex
            return num_changed
    

    def update_technicians(self, qualifications_file: TextIO) -> int:
        """Given the open file <qualifications_file> that follows the format
        described on the handout, update the database to reflect that the
        recorded technicians can now work on the corresponding given truck type.
        """
        try:
            # TODO: implement this method
            cur = self.connection.cursor()

            #use helper function to read file
            qualified = self._read_qualifications_file(qualifications_file)

            #number of techs changed
            num_changed = 0

            #for every entry, check if employee and truck type are valid, if the tech is not a driver and not already
            #qualified
            for q in qualified:
                techName = q[0] + ' ' + q[1]
                #print(techName)
                truck_type = q[2]

                #technician ID is employee
                cur.execute("SELECT eID FROM Employee WHERE name = %s ", (techName,))
                validEID = cur.fetchone()

                if validEID is not None:
                    
                    cur.execute("SELECT truckType FROM TruckType WHERE truckType = %s ", (truck_type,)) # see if the trucktype exists
                    validTruckType = cur.fetchone()

                    if validTruckType is not None:

                        cur.execute("SELECT eID FROM Driver WHERE eID = %s", (validEID[0],)) #see if the employee is a driver
                        isDriver = cur.fetchone()

                        if isDriver is None:
                            cur.execute("SELECT eID, truckType FROM Technician WHERE eID = %s AND truckType = %s", (validEID[0], truck_type)) #see if already a technician for the same type
                            isAlreadyTech = cur.fetchone()

                            if isAlreadyTech is None:
                                #print("about to insert")
                                cur.execute("INSERT INTO Technician (eID, truckType) VALUES (%s, %s)", (validEID[0], truck_type))
                                num_changed += 1
                            else:
                                continue #skip because already exists
                        
                        else:
                            continue #was a driver, skip
                    else:
                        continue #skip because was not a valid truck type



                else:
                    continue #skip because was not a valid employee 

                



            cur.close()
            self.connection.commit()
            return num_changed    

            
        except pg.Error as ex:
            # You may find it helpful to uncomment this line while debugging,
            # as it will show you all the details of the error that occurred:
            raise ex
            return 0

    def workmate_sphere(self, eid: int) -> list[int]:
        """Return the workmate sphere of the driver identified by <eid>, as a
        list of eIDs.

        The workmate sphere of <eid> is:
            * Any employee who has been on a trip with <eid>.
            * Recursively, any employee who has been on a trip with an employee
              in <eid>'s workmate sphere is also in <eid>'s workmate sphere.
        """
        try:
            # TODO: implement this method
            
            new_cursor = self.connection.cursor()

            new_cursor.execute("select eid from driver") #getting eIDs of all drivers

            allDrivers = new_cursor.fetchall()
           
           
            found = False

            for driver in allDrivers:
                if(driver[0] == eid): #checking if eid belongs to a driver otherwise return []
                    found = True               
        
            
            if (found == False): 
                return []

            new_cursor.execute("select distinct eid1,eid2 from trip") #get workmates
            pair_extract = new_cursor.fetchall()
           
            pairs = []
            
            for row in pair_extract:
                pairs.append((row[0],row[1]))   #store in pairs array after integer conversion             

            sphere_list = []
            populate = self.partner(self,eid,pairs,sphere_list) # call recursive helper function to get workmate_sphere

            
            for x in range(len(sphere_list)): #remove the initial eid argument
                if(sphere_list[x] == eid):
                    del sphere_list[x]
                    break #stop iteration to prevent going out of bounds
            
            new_cursor.close()            
            return sphere_list          
            
        except pg.Error as ex:
            # You may find it helpful to uncomment this line while debugging,
            # as it will show you all the details of the error that occurred:
            raise ex
            return []

    def schedule_maintenance(self, date: dt.date) -> int:
        """For each truck whose most recent maintenance before <date> happened
        over 90 days before <date>, and for which there is no scheduled
        maintenance up to 10 days following date, schedule maintenance with
        a technician qualified to work on that truck in ascending order of tIDs.
        """
        try:
            # TODO: implement this method
            cur = self.connection.cursor()
            
            #finding the date to check the truck maintenance
            maintenanceDate = date - dt.timedelta(days=90)
            tenDays = date + dt.timedelta(days=10)

            #Trucks that need maintenance
            cur.execute("""
                CREATE TEMPORARY VIEW MainRequired AS 
                (SELECT DISTINCT tID FROM Truck ORDER BY tID) 
                EXCEPT 
                (SELECT DISTINCT tID FROM Maintenance WHERE mDATE BETWEEN %s AND %s)
                """, (maintenanceDate, tenDays))
            
            # ----- Storing all the maintenance requiring trucks in a var ----
            cur.execute("SELECT tID, truckType FROM MainRequired NATURAL JOIN Truck ORDER BY tID")
            maintenanceRequiredTrucks = cur.fetchall()

            if maintenanceRequiredTrucks is None:
                cur.close()
                self.connection.commit()
                return 0
            

            #FIND ALL TRUCKS GETTING MAINTAINED IN THE NEXT 10 DAYS
            # 
            #Finding all the available techs for every truck type and then schedule the maintenance
            number_schedule = 0 
            
            

            for eachTruck in maintenanceRequiredTrucks:

                tid, truck_t = eachTruck


                #------ finding the allowed technicians
                cur.execute(""" 
                    CREATE VIEW techAllowed AS
                    SELECT eID 
                    FROM Technician 
                    WHERE truckType = %s 
                    ORDER BY eID """, (truck_t))
                
                cur.execute("SELECT * FROM techAllowed")
                tech_allowed = cur.fetchall()

                if tech_allowed is None: #skip if not allowed
                    continue


                curr_date = date + dt.timedelta(days=1)
                can_schedule = False

                while can_schedule is False:

                    # ----- Find if the tID is going on a trip today
                    cur.execute ( """
                        SELECT * 
                        FROM Trip 
                        WHERE tID = %s AND date(tTIME) = %s
                    
                    """, (tid, curr_date))
                    TruckOnTrip = cur.fetchone()
                    #print("truck is going on trip: ", TruckOnTrip)

                    if TruckOnTrip is not None: #if it went on a trip go to the next day and skip iteration
                        #print("Going here")
                        self.connection.rollback()
                        curr_date = curr_date + dt.timedelta(days=1)
                        continue



                        # -------------------- -------------------- --------------------
                    # -------- get free technicians on the day w the same type -----


                    ##get all the technicians that are busy
                    cur.execute("""
                        CREATE TEMPORARY VIEW NotAvail AS
                        SELECT eID
                        FROM Maintenance NATURAL JOIN techAllowed NATURAL JOIN Employee
                        WHERE mDATE = %s OR hireDate >= %s
                        ORDER BY eID
                    
                    """, (curr_date, curr_date))


                    #----- subtract all allowed from the ones who are busy
                    cur.execute("""
                        CREATE TEMPORARY VIEW FinalList AS 
                        (SELECT eID
                        FROM techAllowed
                        ORDER BY eID)
                        EXCEPT
                        (SELECT *
                        FROM NotAvail)
                    """)

                    cur.execute(" SELECT * FROM FinalList ORDER BY eID")

                    availableTechEID = cur.fetchone()
                    #print(availableTechEID)

                    #----- if no available techs today, go to the next day and skip iteration
                    if availableTechEID is None:
                        self.connection.rollback()
                        curr_date = curr_date + dt.timedelta(days=1)
                        continue
                    
                   
                    #===== everything is good, we can insert and update
                    cur.execute(" INSERT INTO Maintenance (tID, eID, mDATE) VALUES (%s, %s, %s)", (tid, availableTechEID, curr_date))
                    number_schedule += 1
                    can_schedule = True
                    cur.execute("DROP VIEW FinalList, NotAvail")
                    
                    
                    
                    self.connection.commit()
                
                #other cleanup
                cur.execute("DROP VIEW techAllowed")


            
            cur.close()
            self.connection.commit()
            return number_schedule
        
        except pg.Error as ex:
            # You may find it helpful to uncomment this line while debugging,
            # as it will show you all the details of the error that occurred:
            raise ex
            return 0

    def reroute_waste(self, fid: int, date: dt.date) -> int:
        """Reroute the trips to <fid> on day <date> to another facility that
        takes the same type of waste. If there are many such facilities, pick
        the one with the smallest fID (that is not <fid>).
        """
        
        try:
            # TODO: implement this method
            cur = self.connection.cursor()

            #find the waste type of the facility which is shut down
            cur.execute("SELECT wasteType FROM Facility WHERE fID =%s", (fid,))
            result = cur.fetchone()
            #print("waste type:", result)

            #invalid wastetype
            if result is None:
                return 0

            WasteType = result[0]

            #find facilities where the waste type is the same
            cur.execute("SELECT fID FROM Facility WHERE fID != %s AND wasteType = %s ORDER BY fID", (fid, WasteType))
            availableFacilities = cur.fetchall()
            
            #print("available facilities:", availableFacilities)
            newFID = availableFacilities[0]

            if not availableFacilities: #if there aren't any facilities available then dip
                return 0

            #cursor.execute("SELECT *  FROM Trip WHERE date(tTime) = %s AND fID != %s", (date, fid))
            
            #print("the new fid", newFID)
            #tripsOnDate = cursor.fetchall()
            #if not tripsOnDate:
            #    return 0
           
            # update the trip table to change all the rows
            cur.execute("UPDATE Trip SET fID = %s WHERE fID = %s AND date(tTIME) = %s ", (newFID, fid, date ))

            num_changed = cur.rowcount
            
            cur.close()
            self.connection.commit()
            
            return num_changed
        except pg.Error as ex:
            # You may find it helpful to uncomment this line while debugging,
            # as it will show you all the details of the error that occurred:
            #raise ex
            self.connection.rollback()
            return 0

    # =========================== Helper methods ============================= #

    @staticmethod
    def _read_qualifications_file(file: TextIO) -> list[list[str, str, str]]:
        """Helper for update_technicians. Accept an open file <file> that
        follows the format described on the A2 handout and return a list
        representing the information in the file, where each item in the list
        includes the following 3 elements in this order:
            * The first name of the technician.
            * The last name of the technician.
            * The truck type that the technician is currently qualified to work
              on.

        Pre-condition:
            <file> follows the format given on the A2 handout.
        """
        result = []
        employee_info = []
        for idx, line in enumerate(file):
            if idx % 2 == 0:
                info = line.strip().split(' ')[-2:]
                fname, lname = info
                employee_info.extend([fname, lname])
            else:
                employee_info.append(line.strip())
                result.append(employee_info)
                employee_info = []

        return result
    
    @staticmethod
    def partner(self,eid:int,driver_pairs:list,final_list:list):
        
        if not driver_pairs: #if empty
            return []

        for pair in driver_pairs:
            if eid not in pair: #exclude the pair if familiar eid not present
                continue
            else:
                if eid in pair:
                    #identify which element of the pair is 1st and 2nd, switch if needed 
                    if pair[1] == eid:
                        other_eid = pair[0]
                    else: 
                        other_eid = pair[1]

                    if other_eid not in final_list: #check final_list before adding an eid to avoid repition and repititive recurive calls for same eid
                        final_list.append(other_eid)
                        self.partner(self,other_eid,driver_pairs,final_list) #make recursive call on 2nd element of pair that was decided earlier

def setup(dbname: str, username: str, password: str, file_path: str) -> None:
    """Set up the testing environment for the database <dbname> using the
    username <username> and password <password> by importing the schema file
    and the file containing the data at <file_path>.
    """
    connection, cursor, schema_file, data_file = None, None, None, None
    try:
        # Change this to connect to your own database
        connection = pg.connect(
            dbname=dbname, user=username, password=password,
            options="-c search_path=waste_wrangler"
        )
        cursor = connection.cursor()

        schema_file = open("./waste_wrangler_schema.sql", "r")
        cursor.execute(schema_file.read())

        data_file = open(file_path, "r")
        cursor.execute(data_file.read())

        connection.commit()
    except Exception as ex:
        connection.rollback()
        raise Exception(f"Couldn't set up environment for tests: \n{ex}")
    finally:
        if cursor and not cursor.closed:
            cursor.close()
        if connection and not connection.closed:
            connection.close()
        if schema_file:
            schema_file.close()
        if data_file:
            data_file.close()


def test_preliminary() -> None:
    """Test preliminary aspects of the A2 methods."""
    ww = WasteWrangler()
    qf = None
    try:
        # TODO: Change the values of the following variables to connect to your
        #  own database:
        dbname = 'csc343h-dadooshr'
        user = 'dadooshr'
        password = ''

        connected = ww.connect(dbname, user, password)

        # The following is an assert statement. It checks that the value for
        # connected is True. The message after the comma will be printed if
        # that is not the case (connected is False).
        # Use the same notation to thoroughly test the methods we have provided
        assert connected, f"[Connected] Expected True | Got {connected}."

        # TODO: Test one or more methods here, or better yet, make more testing
        #   functions, with each testing a different aspect of the code.

        # The following function will set up the testing environment by loading
        # the sample data we have provided into your database. You can create
        # more sample data files and use the same function to load them into
        # your database.
        # Note: make sure that the schema and data files are in the same
        # directory (folder) as your a2.py file.
        setup(dbname, user, password, './waste_wrangler_data.sql')

        # --------------------- Testing schedule_trip  ------------------------#

        # You will need to check that data in the Trip relation has been
        # changed accordingly. The following row would now be added:
        # (1, 1, '2023-05-04 08:00', null, 2, 1, 1)
        scheduled_trip = ww.schedule_trip(1, dt.datetime(2023, 5, 4, 8, 0))
        assert scheduled_trip, \
            f"[Schedule Trip] Expected True, Got {scheduled_trip}"

        # Can't schedule the same route of the same day.
        scheduled_trip = ww.schedule_trip(1, dt.datetime(2023, 5, 4, 13, 0))
        assert not scheduled_trip, \
            f"[Schedule Trip] Expected False, Got {scheduled_trip}"

        # # -------------------- Testing schedule_trips  ------------------------#

        # All routes for truck tid are scheduled on that day
        scheduled_trips = ww.schedule_trips(1, dt.datetime(2023, 5, 3))
        assert scheduled_trips == 0, \
            f"[Schedule Trips] Expected 0, Got {scheduled_trips}"

        # ----------------- Testing update_technicians  -----------------------#

        # This uses the provided file. We recommend you make up your custom
        # file to thoroughly test your implementation.
        # You will need to check that data in the Technician relation has been
        # changed accordingly
        qf = open('qualifications.txt', 'r')
        updated_technicians = ww.update_technicians(qf)
        assert updated_technicians == 2, \
            f"[Update Technicians] Expected 2, Got {updated_technicians}"

        # ----------------- Testing workmate_sphere ---------------------------#

        # This employee doesn't exist in our instance
        workmate_sphere = ww.workmate_sphere(2023)
        assert len(workmate_sphere) == 0, \
            f"[Workmate Sphere] Expected [], Got {workmate_sphere}"

        workmate_sphere = ww.workmate_sphere(3)
        # Use set for comparing the results of workmate_sphere since
        # order doesn't matter.
        # Notice that 2 is added to 1's work sphere because of the trip we
        # added earlier.
        assert set(workmate_sphere) == {1, 2}, \
            f"[Workmate Sphere] Expected {{1, 2}}, Got {workmate_sphere}"

        # ----------------- Testing schedule_maintenance ----------------------#

        # You will need to check the data in the Maintenance relation
        scheduled_maintenance = ww.schedule_maintenance(dt.date(2023, 5, 5))
        assert scheduled_maintenance == 7, \
            f"[Schedule Maintenance] Expected 7, Got {scheduled_maintenance}"

        # ------------------ Testing reroute_waste  ---------------------------#

        # There is no trips to facility 1 on that day
        reroute_waste = ww.reroute_waste(1, dt.date(2023, 5, 10))
        assert reroute_waste == 0, \
            f"[Reroute Waste] Expected 0. Got {reroute_waste}"

        # You will need to check that data in the Trip relation has been
        # changed accordingly
        reroute_waste = ww.reroute_waste(1, dt.date(2023, 5, 3))
        assert reroute_waste == 1, \
            f"[Reroute Waste] Expected 1. Got {reroute_waste}"
    finally:
        if qf and not qf.closed:
            qf.close()
        ww.disconnect()


if __name__ == '__main__':
    # Un comment-out the next two lines if you would like to run the doctest
    # examples (see ">>>" in the methods connect and disconnect)
    # import doctest
    # doctest.testmod()

    # TODO: Put your testing code here, or call testing functions such as
    #   this one:
    test_preliminary()
    