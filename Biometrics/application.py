import traceback
from rest_framework.response import Response #type: ignore
from django.shortcuts import render, redirect #type: ignore
from django.contrib import messages #type: ignore
from django.http import StreamingHttpResponse #type: ignore
from channels.layers import get_channel_layer #type: ignore
from asgiref.sync import async_to_sync #type: ignore
from datetime import datetime
from django.core.files.uploadedfile import InMemoryUploadedFile # type: ignore

# Face Recognition Modules
import threading
import cv2 #type: ignore
import numpy as np #type: ignore
import face_recognition #type: ignore
import os

# METHOD 2 MODULES
# from deepface.DeepFace import represent # type: ignore
# from scipy.spatial.distance import cosine # type: ignore

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

from .models import KnownFace #type: ignore
 
from Core.models import Institution, Class, Classroom, Department, Course, Term
from Students.models import Allocate_Student, Student 
from Staff.models import Staff
from Attendance.models import StudentRegister, StaffRegister 
from Timetable.models import Timetable, TableSetup

# Dictionary to track running threads for each class
running_threads = {}
stop_event = {}

context = {}

THRESHOLD = 0.6
 
# =================== FACE RECOGNITION ================= #
def handle_uploaded_file(file: InMemoryUploadedFile):
    # Read the image file as a NumPy array
    image_data = file.read()

    # Convert the binary data into a NumPy array
    nparr = np.frombuffer(image_data, np.uint8)

    # Decode the image to obtain the image in the correct format (BGR)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("The uploaded file is not a valid image")

    return img

def store_face_encoding(request, name):
    # Load image and encode face
    user = Student.objects.filter(regno = name)
    if not user:
        user = Staff.objects.filter(regno = name)
        if not user:
            return Response({"error": "User not found!"})
        else:
            user = Staff.objects.get(regno = name)
    else:
        user = Student.objects.get(regno = name)
    
    image_path = request.FILES.get('image')

    print("The Images is in this path", image_path)

    # Step 1: Open and process the image to extract embeddings
    try:
        image = face_recognition.load_image_file(image_path)
        face_loc = face_recognition.face_locations(image)
        encoding = face_recognition.face_encodings(image, face_loc)  # Extract the face encoding
        
        # Step 2: Save the image and embedding to the database
        known_face = KnownFace.objects.filter(regno=name)
        if known_face:
            known_face = KnownFace.objects.get(regno=name)
        known_face.image = image_path
        known_face.save()  # Save image to database
        known_face.save_encoding(encoding)  # Save the embedding to the database

        return Response({"success": f"Image encoding done succesfully for {name}"})
    except:
        return Response({"error": f"Image encoding wasn't successful!"})

def stop_cleanup(classroom_name):
    """This function is called when the recognition process is stopped."""
    # Perform any cleanup actions like releasing resources, stopping cameras, etc.
    print(f"Cleanup after stopping recognition for classroom {classroom_name}")
    
    # If you need to mark the classroom as inactive:
    current_classroom = Classroom.objects.get(name = classroom_name)
    current_classroom.front_activated = False
    current_classroom.aux_activated = False
    current_classroom.state = "Inactive"
    current_classroom.save()

def stop_face_recognition(request, timetable_id):
    """Stops the face recognition process for a class."""
    classroom_id = Timetable.objects.filter(id = timetable_id)
    if not classroom_id:
        messages.error(request, "Classroom NOT found....")
        return redirect('view_attendance')

    current_timetable = Timetable.objects.get(id = timetable_id)
    classroom_id = current_timetable.classroom.id
    current_classroom = Classroom.objects.get(id = classroom_id)
    classroom_name_A = str(current_classroom.name) + "_Front"
    classroom_name_B = str(current_classroom.name) + "_Aux"

    #Mark Absents
    classObject = current_timetable.Class
    todate = datetime.today().date()
    currentTime = datetime.now().time() #strftime("%H:%M:%S")
    
    # Students Section
    studentObject = Allocate_Student.objects.filter(Class = classObject, term__year = Institution.objects.first().current_year)
    markedStudents = StudentRegister.objects.filter(lesson = current_timetable, dor = todate)
    for student in studentObject:
        studentfound = False
        for markedStudent in markedStudents:
            if markedStudent.student == student.studentno:
                studentfound = True

        if studentfound == True:
            pass
        else:
            currentTime = datetime.now().time() #strftime("%H:%M:%S")
            registerObject = StudentRegister( lesson = current_timetable, student = student.studentno, state = "Absent", dor = todate, tor = currentTime)
            registerObject.save()

    # Trainer's Section
    trainerObject = current_timetable.unit.regno
    markedTrainer = StaffRegister.objects.filter(lesson = current_timetable, dor = todate, lecturer=trainerObject)
    if not markedTrainer:
        currentTime = datetime.now().time() #strftime("%H:%M:%S")
        registerObject = StaffRegister(lesson = current_timetable, lecturer = trainerObject, state = "Absent", dor = todate, tor = currentTime)
        registerObject.save()

    if classroom_name_A in running_threads:
        stop_event[classroom_name_A].set()

        del running_threads[classroom_name_A]
        print(running_threads)

        current_classroom.front_activated = False
        current_classroom.state = "Inactive"
        current_classroom.save()

        context["classRoom"] = current_classroom.state
        messages.info(request, 'Front Camera stopped..')
    else:
        messages.error(request, "Camera couldn't be found")

    if classroom_name_B in running_threads:
        stop_event[classroom_name_B].set()

        del running_threads[classroom_name_B]
        print(running_threads)

        current_classroom.aux_activated = False
        current_classroom.state = "Inactive"
        current_classroom.save()

        context["classRoom"] = current_classroom.state
        messages.info(request, 'Aux Camera stopped..')
    else:
        messages.error(request, "Camera couldn't be found")

    return redirect('view_attendance')

def recognize_faces(timetable_id, camera_url, threadname=None):
    """Runs the face recognition process for a class."""
    try:
        cap = cv2.VideoCapture(int(camera_url) if str(camera_url).isdigit() else camera_url)

        if not cap.isOpened():
            print(f"[ERROR] Could not open camera: {camera_url}", flush=True)
            return

        # Fetch timetable and related info
        timetable = Timetable.objects.select_related("unit", "classroom", "unit__regno").filter(id=timetable_id).first()
        if not timetable:
            print(f"[ERROR] Timetable ID {timetable_id} not found", flush=True)
            return

        classroom = timetable.classroom
        trainer_regno = getattr(timetable.unit.regno, "regno", None)
        if not trainer_regno:
            print("[ERROR] Trainer not found for unit", flush=True)
            return

        # Fetch allocated students
        students_qs = Allocate_Student.objects.select_related("studentno").filter(Class=timetable.Class)
        student_regnos = {s.studentno.regno for s in students_qs}

        # Load all relevant known faces once
        known_faces_qs = KnownFace.objects.filter(regno__in=student_regnos.union({trainer_regno}))
        known_encodings = []
        known_names = []

        for face in known_faces_qs:
            try:
                known_encodings.append(face.get_encoding())
                known_names.append(face.regno)
            except Exception as e:
                print(f"[WARN] Failed to decode encoding for {face.regno}: {e}", flush=True)

        if not known_encodings:
            print("[INFO] No known encodings available", flush=True)
            return

        print(f"[INFO] Recognition started for {classroom.name} with {len(known_encodings)} known faces")

        while threadname in running_threads:
            ret, frame = cap.read()
            if not ret:
                print("[INFO] Camera stream ended", flush=True)
                break

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_frame)
            unknown_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

            for (top, right, bottom, left), face_encoding in zip(face_locations, unknown_encodings):
                matches = face_recognition.compare_faces(known_encodings, face_encoding)
                name = "Unknown"

                if True in matches:
                    matched_index = matches.index(True)
                    regno = known_names[matched_index]
                    name = regno

                    # Attendance marking
                    now = datetime.now()
                    today = now.date()
                    time_now = now.time()

                    student = Student.objects.filter(regno=regno).first()
                    if student:
                        if not StudentRegister.objects.filter(student=student, lesson=timetable, dor=today).exists():
                            StudentRegister.objects.create(
                                student=student,
                                lesson=timetable,
                                state="Present",
                                dor=today,
                                tor=time_now
                            )
                    else:
                        staff = Staff.objects.filter(regno=regno).first()
                        if staff and not StaffRegister.objects.filter(lecturer=staff, lesson=timetable, dor=today).exists():
                            StaffRegister.objects.create(
                                lecturer=staff,
                                lesson=timetable,
                                state="Present",
                                dor=today,
                                tor=time_now
                            )

                    # Real-time feedback
                    async_to_sync(get_channel_layer().group_send)(
                        f"attendance_{classroom.name}",
                        {"type": "send_update", "message": f"{regno} marked as Present"}
                    )

                # Draw rectangle
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                cv2.putText(frame, name, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)

        print(f"[INFO] Stopping recognition thread: {threadname}", flush=True)

    except Exception as e:
        print(f"[EXCEPTION] in recognize_faces: {e}", flush=True)
        traceback.print_exc()
    finally:
        cap.release()
        stop_cleanup(classroom.name)

def stream_video(timetable_id, camera_url):
    return StreamingHttpResponse(
        recognize_faces(timetable_id, camera_url), 
        content_type="multipart/x-mixed-replace; boundary=frame"
    )

def stream_multiple_videos(request, department):
    # Get all timetables for that day, that time
    currentIntake = Term.objects.filter(year = Institution.objects.first().current_year, name = Institution.objects.first().current_intake)
    today = str(datetime.today().strftime('%A')).upper() #isoweekday()
    currentTime = datetime.now().time() #strftime("%H:%M:%S")
    
    # messages.info(request, todate) 
    currentLesson = TableSetup.objects.filter(start__lte=currentTime, end__gte=currentTime).first()
    if currentLesson is None:
        messages.error(request, "No lesson is currently active.")
        return redirect('index')
    
    timetable = Timetable.objects.filter(term = currentIntake, day = today, lesson = currentLesson)
    if not timetable:
        messages.error(request, "Oops, Unfortunately today this hour there is no lesson for classes")
        return redirect('index')
    
    # Get current Department
    current_department = Department.objects.filter(id = department).first()
    if current_department:
        current_department = Department.objects.get(id = department)
    else:
        messages.error(request, "Department NOT found..")
        return redirect('index')
    
    # Get all the Courses of the department
    current_courses = Course.objects.filter(department = current_department)
    if not current_courses:
        messages.error(request, "Oops, Unfortunately there are no courses in this department")
        return redirect('index')
    
    # Get All the classes that are in respective courses
    current_class_list = []
    for course in current_courses:
        current_class = Class.objects.filter(course = course)
        if current_class:
            current_class_list.extend(current_class)

    if not current_class_list:
        messages.error(request, "Unfortunately, there are classes yet in this department...")
        return redirect('index')
    
    # Get Current Timetable for every class
    current_timetable_list = []
    for current_class_datum in current_class_list:
        current_timetable_class = Timetable.objects.filter(term =  Term.objects.filter(year = Institution.objects.first().current_year, name = Institution.objects.first().current_intake), Class = current_class_datum, day = today, lesson = currentLesson)
        if current_timetable_class:
            current_timetable_list.extend(current_timetable_class)
    
    # Get the timetable ID, camera url
    # Generate multiple camera streams
    # camera_urls = [f"camera_url_{i}" for i in range(1, 41)]  # Dummy URLs for 40 cameras
        
    # Return a rendered page with 40 video elements, each corresponding to a camera
    return render(request, "Biometrics/FaceRecognition/live_feed.html", context)

# ================= END OF FACE RECOGNITION =========== #
