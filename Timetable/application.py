from datetime import timedelta
from .models import TableSetup, Timetable, Days
from Core.models import Class, Classroom
from Staff.models import StaffWorkload

def to_internal_value(data):
    duration_str = data
    if duration_str and isinstance(duration_str, str) and len(duration_str.split(":")) == 2:
        h, m = map(int, duration_str.split(":"))
    return timedelta(hours=h, minutes=m)

def parse_duration_string(duration_str):
    hours, minutes, seconds = map(int, duration_str.split(':'))
    return timedelta(hours=hours, minutes=minutes, seconds=seconds)
 
def checkTableSlot(data):
    response = {}
    for lesson in TableSetup.objects.all():
        available = "Free"
        #Check whether the Lesson is already booked
        Table = Timetable.objects.filter(term = data["currentTerm"], Class = Class.objects.get(id = data["Class"]), day = data["day"], lesson = lesson)
        if Table:
            available = "Booked"
        myCheck = {lesson:available}
        response.update(myCheck)
    return response

def checkTrainerSlot(data):
    response = {}
    lessonCount = 0
    for lsn in TableSetup.objects.all():
        for lesson in data["lesson"]:
            if lsn.id == int(lesson):
                lessonCount += 1
                workloadCount = 0
                for workload in data["workload"]:
                    workloadCount += 1
                    if lessonCount == workloadCount:
                        TrainerTables = [] #Timetable Data Structure for the trainer
                        if workload != "":
                            workload = StaffWorkload.objects.get(id = int(workload))
                            #Get trainer
                            trainer = getattr(workload, "regno")

                            #Generate all workloads of the trainer
                            trainer_workloads = StaffWorkload.objects.filter(regno = trainer)
                            
                            # Generate all Schedules of the trainer
                            for trainer_workload in trainer_workloads:
                                trainer_tables = Timetable.objects.filter(term = data["currentTerm"], unit = trainer_workload)
                                if trainer_tables:
                                    for trainer_table in trainer_tables:
                                        if trainer_table not in TrainerTables:
                                            TrainerTables.append(trainer_table)
                            print(TrainerTables)
                            
                            #Check whether trainer has been booked
                            temp = {}
                            trainer_table_ = Timetable.objects.filter(term = data["currentTerm"], lesson = lsn, day = data["day"])
                            for tble in trainer_table_:
                                if tble.unit.regno == trainer:
                                    temp = {lesson: "Booked"}

                            for trainer_table in TrainerTables:
                                if trainer_table.day == data["day"] and trainer_table.lesson == TableSetup.objects.get(id = int(lesson)):
                                    if lesson not in temp:
                                        temp = {lesson:"Booked"}
                                else:
                                    if lesson not in temp:
                                        temp = {lesson:"Free"}
                            
                            response.update(temp)
    return response

def checkHoursLeft(data):
    Tables = Timetable.objects.filter(term = data["currentTerm"], Class = Class.objects.get(id = data["Class"]), unit = data["workload"])
    if Tables:
        totalHours = 0
        for table in Tables:
            duration = table.lesson.duration
            hours = duration.hour
            minutes = duration.minute
            seconds = duration.second
            total_seconds = (hours * 3600) + (minutes * 60) + seconds
            totalHours += total_seconds
            print(f"There are {totalHours} seconds for {data["workload"]}")
        currentUnit = getattr(data["workload"], "unit")
        totalDuration = int(currentUnit.weekly_hours) * 3600
        print(f"There are {totalDuration} seconds for {currentUnit}")
        if totalHours < totalDuration:
            return "continue"
        else:
            return "limited"        
    else:
        return "continue"

def getStaffHours(lecturer, currentTerm):
    # Get workload for the lecturer

    new_object_list = [lecturer, 0, 0]
    workload = StaffWorkload.objects.filter(term = currentTerm, regno = lecturer)
    if workload:
        totalHours = 0
        for work in workload:
            Tables = Timetable.objects.filter(term = currentTerm, Class = work.Class, unit = work)
            if Tables:
                for table in Tables:
                    duration = table.lesson.duration
                    hours = duration.hour
                    minutes = duration.minute
                    seconds = duration.second
                    total_seconds = (hours * 3600) + (minutes * 60) + seconds
                    totalHours += total_seconds/3600

        print(f"There are {totalHours} Hours for {lecturer} used already")
        # Calculate %ge used
        percentage = round(totalHours/int(lecturer.weekly_hours) * 100, 2)
        # Store them in a dictionary
        new_object_list = [lecturer, totalHours, percentage]

    return new_object_list

def schedule_table(request, class_, day, lesson, load, classroom):
    try:
        # Get Objects
        class_object = Class.objects.get(id = class_)
        day_object = Days.objects.get(id = day)
        lesson_object = TableSetup.objects.get(id = lesson)
        workload_object = StaffWorkload.objects.get(id = load)
        classroom_object = Classroom.objects.get(id = classroom)

        Table = Timetable(term = class_object.intake, Class = class_object, classroom = classroom_object, day = day_object, lesson = lesson_object, unit = workload_object)
        Table.save()

        return {"success": "Table Added Successfully"}
    
    except Class.DoesNotExist:
        return {"error": "Class is not found!"}

    except Days.DoesNotExist:
        return {"error": "Day is not found!"}
    
    except StaffWorkload.DoesNotExist:
        return {"error": "Staff Workload is not found!"}
    
    except TableSetup.DoesNotExist:
        return {"error": "Lesson is not found!"}
    
    except Classroom.DoesNotExist:
        return {"error": "Classroom is not found!"}

    workloads = StaffWorkload.objects.filter(term = class_object.intake, Class = class_object )
    
    selectedTable = ''
    module = Module.objects.get(id = module)
    classRooms = Classroom.objects.all()
    
    #Check existance of Day
    incorrectDay = True
    for key, value in WEEKDAY_CHOICES:
        if day == key or day == value:
            incorrectDay = False
    if incorrectDay:
        messages.error(request, "The Day is not a valid day...")
        course = getattr(getattr(Class.objects.get(id = int(Classes)),"course"), "id")
        return redirect("add_table_class", branch.id, course, module.id)
    
    myData = {"year":year, "currentTerm":currentTerm, "Classes":Classes, "branch":branch, "module":module, "day":day}

    if mode == "Edit":
        selectedTable = Timetable.objects.get(id = int(tableid))

    #=================GENERATE CLASS FREE LESSON SLOTS FOR THAT DAY================#
    mySlots = checkTableSlot(data = myData)
    freeTable = TableSetup.objects.all()
    freeSlots = []
    for less in freeTable:
        for slot in mySlots:
            if less == slot:
                if mySlots[slot] == "Free":
                    freeSlots.append(less)
                else:
                    global checked
                    if checked == False:
                        messages.error(request, f"{slot} Record is {mySlots[slot]}!")
    checked = True
    # print(f"FREE SLOTS FOR LESSON(S) FOR THAT DAY: {freeSlots}\n\n")
    #======================END OF GENERATING FREE LESSON SLOTS=====================#
    
    if request.method == "POST":
        data = dict(request.POST)
        print(data)

        #================CHECK WHETHER THE LESSON SELECTED IS AMONG THE FREE SLOTS===============#
        if mode == "Edit":
            matchedLesson = False
            lessn = ''
            for lessns in data["lesson"]:
                lessn = int(lessns)
            for freeslot in freeSlots:
                if lessn == freeslot.id:
                    matchedLesson = True
            if not matchedLesson:
                lessn = int(lessn)
                messages.warning(request, f"{TableSetup.objects.get(id = lessn)} is already scheduled for another lesson. Kindly choose another slot.")
                return redirect("schedule_table", Classes, module.id, branch.name, day, "Edit", tableid)
        #==================END OF COMPARISON BETWEEN FREE SLOTS AND THE SELECTION================#

        #===============CHECK WHETHER THE TRAINER IS OCCUPIED FOR THAT DAY THAT LESSON===========#
        emptyWorkload = True
        key_found = False
        for key in data:
            if key == "workload":
                key_found = True
        if not key_found:
            messages.error(request, "All slots are booked!")
            return redirect('view_tables')
        
        for load in data["workload"]:
            if load != "":
                emptyWorkload = False
            else:
                emptyWorkload = True
        if emptyWorkload:
            pass
            # messages.error(request, "You have not assigned any workload to any of the lessons..")
            # return redirect("schedule_table", Classes, module.id, branch, day, "New",  0)
        
        trainerSlots = checkTrainerSlot(data, year, currentTerm, day)
        print("Trainer slots: ", trainerSlots)

        bookedFound = False
        bookedWorkloads = []
        if trainerSlots:
            count = 0
            for trainerslot in trainerSlots:
                if trainerSlots[trainerslot] == "Booked":
                    for load in data["workload"]:
                        bookedWorkloads.append(data["workload"][count])
                    bookedFound = True
                count += 1

        if bookedFound:
            print("Booked Workload: ", bookedWorkloads)
            for bookedworkload in bookedWorkloads:
                trainer = ""
                for workload in StaffWorkload.objects.all():
                    if workload.id == int(bookedworkload):
                        trainer = workload.regno
                if trainer != "":
                    messages.error(request, f"{trainer} is already Scheduled for another class!")
        #================END OF CHECKING AND AVAILABILITY IS TRUE BEYOND THIS POINT===============#

        #=====================CHECK WHETHER THE CLASS/ CLASSROOM HAS ANOTHER LESSON==========================#
        else:
            for lesson in TableSetup.objects.all():
                count = 0
                for less_temp in data["lesson"]:
                    if lesson.id == int(less_temp):
                        # CLASROOM AVAILABILITY
                        classroom = data["classroom"][count]
                        if classroom == "":
                            pass
                            # messages.error(request, f"You have not selected the classroom for {lesson.name}!")
                        else:
                            classroom_feed = Classroom.objects.get(id = classroom)
                            Table = Timetable.objects.filter(year = year, intake = currentTerm, branch = branch, module=module, day = day, classroom = classroom_feed, lesson = lesson)
                            if Table:
                                messages.error(request, f"{classroom_feed.name} Classroom already in use..!")
                            else:
                                # CLASS AVAILABILITY
                                workload = data["workload"][count]
                                if workload == "":
                                    messages.error(request, f"You have not selected a workload for {lesson.name}!")
                                else:
                                    workload = StaffWorkload.objects.get(id = workload)
                                    
                                    #Check whether the Record Already Exists
                                    Table = Timetable.objects.filter(year = year, intake = currentTerm, course = getattr(Class.objects.get(id = Classes), "course"), branch = branch, module = module, Class = Class.objects.get(id = Classes), day = day, lesson = lesson, unit = workload)
                                    
                                    if Table:
                                        messages.error(request, f"{workload} Record already exists..!")
                                    else:

                                        # Check Hours allocation
                                        myData = {"year":year, "currentTerm":currentTerm, "Classes":Classes, "branch":branch, "module":module, "day":day, "unit": workload}
                                        hoursLeft = checkHoursLeft(data = myData)
                                        if hoursLeft == "limited":
                                            messages.error(request, f"{workload.unit}'s duration has been exhausted..!")
                                        else:

                                            # Check Lecturer's Hours Left
                                            myResult = getStaffHours(workload.regno)
                                            if workload.regno.weekly_hours == int(myResult[1]):
                                                pronoun = "his" if workload.regno.gender == "MALE" else "her"
                                                messages.error(request, f"{workload.regno} has exhausted {pronoun} weekly hours..")
                                            else:
                                                try:
                                                    Table = Timetable(year = year, intake = currentTerm, course = getattr(Class.objects.get(id = Classes), "course"), branch = branch , module=module, Class = Class.objects.get(id = Classes), classroom = classroom_feed, day = day, lesson = lesson, unit = workload)
                                                    Table.save()
                                                    messages.info(request, "Lesson Plan saved successfully...")
                                                    # return redirect("view_tables")
                                                except Exception as e:
                                                    messages.error(request, "Error occured while saving timetable's plan..!")
                                                    print("ERROR: ",e)
                    count += 1
            return redirect("view_tables")
        #=======================END OF CHECKING AVAILABILITY OF TRAINER===========================#

    context = {"Institution":Inst, "Lessons": freeSlots, "Workloads":workloads, "selectedTable":selectedTable, "Mode":mode, "Classrooms": classRooms}
    return render(request, "timetable/table/add_table_final.html", context)

    