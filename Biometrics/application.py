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

from .models import CameraDevice

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

# Dictionary to track running threads for each classroom
running_threads: dict[str, threading.Thread] = {}
stop_events: dict[str, threading.Event] = {}
thread_lock = threading.Lock()  # prevent races on dicts

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
    user = Student.objects.filter(regno=name).first() or Staff.objects.filter(regno=name).first()
    if not user:
        return Response({"error": "User not found!"})

    file = request.FILES.get('image')
    if not file:
        return Response({"error": "Image is required"}, status=400)

    image = face_recognition.load_image_file(file)
    locs = face_recognition.face_locations(image)
    encs = face_recognition.face_encodings(image, locs)

    if not encs:
        return Response({"error": "No face detected"}, status=400)

    known_face, _created = KnownFace.objects.get_or_create(regno=name)
    known_face.image = file
    known_face.save()
    known_face.save_encoding(encs[0])  # match your model’s API

    return Response({"success": f"Image encoding done successfully for {name}"})

def stop_cleanup(classroom_name):
    """This function is called when the recognition process is stopped."""
    # Perform any cleanup actions like releasing resources, stopping cameras, etc.
    print(f"Cleanup after stopping recognition for classroom {classroom_name}")
    
    # If you need to mark the classroom as inactive:
    cameras = CameraDevice.objects.filter(classroom__name = classroom_name)
    

# THREADS
def start_face_recognition_thread(key: str, timetable_id: int, camera_url: str):
    with thread_lock:
        if key in running_threads:
            print(f"[INFO] Thread for {key} already running")
            return False

        ev = threading.Event()
        stop_events[key] = ev

        t = threading.Thread(
            target=recognize_faces,
            args=(timetable_id, camera_url, key, ev),
            name=f"face-rec-{key}",
            daemon=True,
        )
        running_threads[key] = t
        t.start()
        print(f"[INFO] Started recognition thread for {key}")
        return True

def stop_face_recognition_thread(key: str):
    with thread_lock:
        ev = stop_events.get(key, None)
        t = running_threads.pop(key, None)

    if not ev or not t:
        print(f"[INFO] No running thread for {key}")
        return False

    ev.set()
    print(f"[INFO] Stop signal set for {key}")
    return True

# FACE RECOGNITION
def start_face_recognition(request, timetable_id):
    tt = Timetable.objects.filter(id=timetable_id).select_related("classroom").first()
    if not tt:
        messages.error(request, "Timetable not found")
        return redirect("view_attendance")

    classroom = tt.classroom
    key_front = f"{classroom.name}_Front"
    key_aux   = f"{classroom.name}_Aux"

    # Example: read camera URLs from classroom model fields
    cam_front = classroom.front_cam_url  # adapt to your field
    cam_aux   = classroom.aux_cam_url

    started_any = False
    if cam_front:
        started_any |= start_face_recognition_thread(key_front, tt.id, cam_front)
        classroom.front_activated = True
        classroom.state = "Active"
    if cam_aux:
        started_any |= start_face_recognition_thread(key_aux, tt.id, cam_aux)
        classroom.aux_activated = True
        classroom.state = "Active"

    classroom.save()

    if started_any:
        messages.success(request, "Recognition started")
    else:
        messages.info(request, "Recognition was already running")

    return redirect("view_attendance")

def stop_face_recognition(timetable_id):
    """Stops the face recognition process for a class."""
    tt = Timetable.objects.filter(id=timetable_id).select_related("classroom").first()
    if not tt:
        return {"error": "Classroom NOT found"}

    #Mark Absents
    classObject = tt.Class
    todate = datetime.today().date()
    currentTime = datetime.now().time() #strftime("%H:%M:%S")
    
    # Students Section
    student_count = 0
    studentObject = Allocate_Student.objects.filter(Class = classObject, term__year = Institution.objects.first().current_year, term__name = Institution.objects.first().current_intake)
    markedStudents = StudentRegister.objects.filter(lesson = tt, dor = todate)
    for student in studentObject:
        studentfound = False
        for markedStudent in markedStudents:
            if markedStudent.student == student.studentno:
                studentfound = True

        if studentfound == True:
            pass
        else:
            currentTime = datetime.now().time() #strftime("%H:%M:%S")
            registerObject = StudentRegister( lesson = tt, student = student.studentno, state = "Absent", dor = todate, tor = currentTime)
            registerObject.save()
            student_count += 1

    # Trainer's Section
    trainerObject = tt.unit.regno
    markedTrainer = StaffRegister.objects.filter(lesson = tt, dor = todate, lecturer=trainerObject)
    if not markedTrainer:
        currentTime = datetime.now().time() #strftime("%H:%M:%S")
        registerObject = StaffRegister(lesson = tt, lecturer = trainerObject, state = "Absent", dor = todate, tor = currentTime)
        registerObject.save()

    return {"info": f"Marked {student_count} Students Absent"}

# RECOGNIZE
def recognize_faces(timetable_id: int, camera_url: str, key: str, stop_event: threading.Event):
    cap = None
    classroom = None
    try:
        cap = cv2.VideoCapture(int(camera_url) if str(camera_url).isdigit() else camera_url)
        if not cap or not cap.isOpened():
            print(f"[ERROR] Camera stream {camera_url} closed unexpectedly", flush=True)
            return

        timetable = (Timetable.objects
                     .select_related("unit", "classroom", "unit__regno")
                     .filter(id=timetable_id)
                     .first())
        if not timetable:
            print(f"[ERROR] Timetable {timetable_id} not found", flush=True)
            return

        classroom = timetable.classroom
        trainer_regno = getattr(timetable.unit.regno, "regno", None)
        if not trainer_regno:
            print("[ERROR] Trainer not found for unit", flush=True)
            return

        # Preload known encodings
        students_qs = Allocate_Student.objects.select_related("studentno").filter(Class=timetable.Class, term = timetable.term)
        student_regnos = {s.studentno.regno for s in students_qs}

        known_faces_qs = KnownFace.objects.filter(regno__in=student_regnos.union({trainer_regno}))
        known_encodings, known_names = [], []
        for face in known_faces_qs:
            try:
                known_encodings.append(face.get_encoding())
                known_names.append(face.regno)
            except Exception as e:
                print(f"[WARN] Failed to decode encoding for {face.regno}: {e}", flush=True)

        if not known_encodings:
            print("[INFO] No known encodings available", flush=True)
            return

        print(f"[INFO] Recognition started for {classroom.name} ({key}) with {len(known_encodings)} faces")

        while not stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                print("[INFO] Camera stream ended", flush=True)
                break

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            locs = face_recognition.face_locations(rgb)
            encs = face_recognition.face_encodings(rgb, locs)

            print("[INFO]: ", encs, flush=True)

            for (top, right, bottom, left), enc in zip(locs, encs):
                matches = face_recognition.compare_faces(known_encodings, enc, tolerance=THRESHOLD)  # you can add tolerance=
                name = "Unknown"

                if True in matches:
                    idx = matches.index(True)
                    regno = known_names[idx]
                    name = regno

                    now = datetime.now()
                    today, time_now = now.date(), now.time()

                    student = Student.objects.filter(regno=regno).first()
                    if student:
                        obj, created = StudentRegister.objects.get_or_create(
                            student=student, lesson=timetable, dor=today,
                            defaults={"state": "Present", "tor": time_now},
                        )
                        if not created and obj.state != "Present":
                            obj.state = "Present"
                            obj.tor = time_now
                            obj.save()
                    else:
                        staff = Staff.objects.filter(regno=regno).first()
                        if staff:
                            obj, created = StaffRegister.objects.get_or_create(
                                lecturer=staff, lesson=timetable, dor=today,
                                defaults={"state": "Present", "tor": time_now},
                            )
                            if not created and obj.state != "Present":
                                obj.state = "Present"
                                obj.tor = time_now
                                obj.save()

                    async_to_sync(get_channel_layer().group_send)(
                        f"attendance_{classroom.name}",
                        {"type": "send_update", "message": f"{regno} marked as Present"}
                    )

                # Draw
                cv2.rectangle(frame, (left, top), (right, bottom), (0,255,0), 2)
                cv2.putText(frame, name, (left, top-10), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255,255,255), 2)

        print(f"[INFO] Stopping recognition thread: {key}", flush=True)

    except Exception as e:
        print(f"[EXCEPTION] in recognize_faces({key}): {e}", flush=True)
        traceback.print_exc()
    finally:
        try:
            if cap is not None:
                cap.release()
        except Exception:
            pass

        # cleanup flags on classroom if we have it
        if classroom:
            stop_cleanup(classroom.name)

        # remove from registries
        with thread_lock:
            running_threads.pop(key, None)
            stop_events.pop(key, None)

        channel_layer = get_channel_layer()
        if timetable_id:
            async_to_sync(channel_layer.group_send)(
                f"lesson_{timetable_id}",
                {"type": "recognition.stopped", "camera": key}
            )

# STREAM
def mjpeg_generator(camera_url: str):
    cap = cv2.VideoCapture(int(camera_url) if str(camera_url).isdigit() else camera_url)
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            ret, jpeg = cv2.imencode('.jpg', frame)
            if not ret:
                continue
            bytes_ = jpeg.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + bytes_ + b'\r\n')
    finally:
        cap.release()

def stream_video(request, camera_url):
    return StreamingHttpResponse(
        mjpeg_generator(camera_url),
        content_type='multipart/x-mixed-replace; boundary=frame'
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
    
    context = {
        "streams": [
            {"id": tt.id, "url": tt.classroom.front_cam_url}
            for tt in current_timetable_list if tt.classroom.front_cam_url
        ]
    }
    
    # Return a rendered page with 40 video elements, each corresponding to a camera
    return render(request, "Biometrics/FaceRecognition/live_feed.html", context)

# ================= END OF FACE RECOGNITION =========== #
