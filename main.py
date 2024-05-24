from datetime import datetime, timezone
import pytz, requests
from flask import Flask, render_template, jsonify, request
import json
import os

def import_calendar():
    urls = ["https://cytt.app/P1G2.ics", "https://cytt.app/P1G3.ics", "https://cytt.app/P2G1.ics", "https://cytt.app/P2G2.ics"]
    calendar = []
    for url in urls:
        response = requests.get(url)
        file_name = f'{url.split("/")[-1]}'
        with open(file_name, 'wb') as file:
            file.write(response.content)
        calendar.append(file_name)
    return calendar

def combine_calendar(calendar):
    combined_calendar = "all.ics"
    with open(combined_calendar, 'wb') as combined_file:
        for file_name in calendar:
            with open(file_name, 'rb') as file:
                combined_file.write(file.read())
    return combined_calendar

def build_Json(calendar_file, fixed_time=None):
    print("Build du CoursJson")
    paris_tz = pytz.timezone('Europe/Paris')
    
    if fixed_time:
        current_time = datetime.fromisoformat(fixed_time)
    else:
        current_time = datetime.now(tz=paris_tz)
    
    today = current_time.date()
    
    json_file = "cours_du_jour.json"
    courses_today = []

    with open(calendar_file, 'r') as file:
        inside_vevent = False
        event = {}
        for line in file:
            if line.startswith('BEGIN:VEVENT'):
                inside_vevent = True
                event = {}
            elif line.startswith('DTSTART:') and inside_vevent:
                value = line.strip().split(':', 1)[1]
                value = value.replace('TZ', '')
                dtstart = datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=pytz.utc)
                dtstart_paris = dtstart.astimezone(paris_tz)
                if dtstart_paris.date() == today:
                    event['start_time'] = dtstart_paris.strftime('%H:%M')
            elif line.startswith('DTEND:') and inside_vevent:
                value = line.strip().split(':', 1)[1]
                value = value.replace('TZ', '')
                dtend = datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=pytz.utc)
                dtend_paris = dtend.astimezone(paris_tz)
                if dtend_paris.date() == today:
                    event['end_time'] = dtend_paris.strftime('%H:%M')
            elif line.startswith('SUMMARY:') and inside_vevent:
                location = line.strip().split(':', 1)[1]
                event['summary'] = location.strip()
            elif line.startswith('LOCATION:') and inside_vevent:
                location = line.strip().split(':', 1)[1]
                event['location'] = location.strip()
            elif line.startswith('ORGANIZER:') and inside_vevent:
                organizer = line.strip().split(':', 1)[1]
                event['organizer'] = organizer.strip()
            elif line.startswith('END:VEVENT'):
                if 'start_time' in event and 'end_time' in event and 'location' in event and 'organizer' in event:
                    courses_today.append(event)
                inside_vevent = False

    with open(json_file, 'w') as outfile:
        json.dump(courses_today, outfile, indent=4)
        


def json1(fixed_time=None):
    toutes_salles = ["A001","E101", "E102", "E103", "E104", "E105", "E106", "E107", "E108", "E109", "E209", "E210", "E211", "E212", "E213", "E214", "E215", "E217", "E218"]

    # Lecture du fichier "cours_du_jour.json"
    with open('cours_du_jour.json', 'r') as f:
        cours_du_jour = json.load(f)

    # Obtenir l'heure actuelle en tenant compte du fuseau horaire Paris
    paris_tz = pytz.timezone('Europe/Paris')

    if fixed_time:
        current_time = datetime.fromisoformat(fixed_time).replace(tzinfo=paris_tz)
    else:
        current_time = datetime.now(tz=paris_tz)

    salles_remplies = []
    salles_vide_prochain_cours = []

    for salle in toutes_salles:
        location_data = verif_location("cours_du_jour.json", salle)
        current_courses = verif_time(location_data, fixed_time)

        if current_courses:
            for current_course in current_courses:
                course_info = {
                    "Début": current_course['start_time'],
                    "Fin": current_course['end_time'],
                    "Prof": current_course['organizer'],
                    "Résumé": current_course['summary']
                }
                
                # Vérifier les doublons dans salles_remplies
                already_exists = False
                for course in salles_remplies:
                    if course.get(salle) == course_info:
                        already_exists = True
                        break
                
                if not already_exists:
                    salles_remplies.append({salle: course_info})
        else:
            next_course_info = next_course("cours_du_jour.json", salle, fixed_time)
            if next_course_info:
                course_info = {
                    "Début": next_course_info['start_time'],
                    "Fin": next_course_info['end_time'],
                    "Prof": next_course_info['organizer'],
                    "Résumé": next_course_info['summary']
                }
                
                # Vérifier les doublons dans salles_vide_prochain_cours
                already_exists = False
                for course in salles_vide_prochain_cours:
                    if course.get(salle) == course_info:
                        already_exists = True
                        break
                
                if not already_exists:
                    salles_vide_prochain_cours.append({salle: course_info})


    salles_vide_journee = [salle for salle in toutes_salles if salle not in salles_remplies and salle not in salles_vide_prochain_cours and salle!="A001"]

    resultat = {
        "salles_vide_journee": {
            "locations": salles_vide_journee
        },
        "salle_remplis": salles_remplies,
        "salle_vide_prochain_cours": salles_vide_prochain_cours
    }

    # with open('cours_du_jour1.json', 'w') as f:
    #     json.dump(resultat, f, indent=4)
    return resultat


def verif_location(json_file, location):
    verif_location = []

    with open(json_file, 'r') as file:
        data = json.load(file)

        for course in data:
            if course['location'] == location:
                verif_location.append(course)

    return verif_location

def next_course(json_file, location, fixed_time=None):
    paris_tz = pytz.timezone('Europe/Paris')
    
    if fixed_time:
        current_time = datetime.fromisoformat(fixed_time).astimezone(paris_tz).strftime('%H:%M')
    else:
        current_time = datetime.now(tz=paris_tz).strftime('%H:%M')

    with open(json_file, 'r') as f:
        data = json.load(f)
    
    courses_in_location = [course for course in data if course.get('location') == location]

    if not courses_in_location:
        return None  # Aucun cours

    # Trier les cours par ordre croissant de leur heure de début
    sorted_courses = sorted(courses_in_location, key=lambda x: x.get('start_time'))

    for course in sorted_courses:
        start_time = datetime.strptime(course['start_time'], '%H:%M').replace(tzinfo=paris_tz).strftime('%H:%M')
        if start_time > current_time:
            return course

    return None

def verif_time(courses, fixed_time=None):
    paris_tz = pytz.timezone('Europe/Paris')
    
    if fixed_time:
        current_time = datetime.fromisoformat(fixed_time).astimezone(paris_tz).strftime('%H:%M')
    else:
        current_time = datetime.now(tz=paris_tz).strftime('%H:%M')
    
    current_courses = []

    for course in courses:
        start_time = datetime.strptime(course['start_time'], '%H:%M').replace(tzinfo=paris_tz).strftime('%H:%M')
        end_time = datetime.strptime(course['end_time'], '%H:%M').replace(tzinfo=paris_tz).strftime('%H:%M')
        if start_time <= current_time <= end_time:
            current_courses.append(course)
            
    return current_courses

app = Flask(__name__)


# # GET pour récupérer les données
# @app.route('/inh_web', methods=['GET'])
# def index():
#     if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
#         location = request.args.get('location')
        
#         # A utiliser pour importer nv json et ics (deja utilisé dans html)
#         #build_Json(combine_calendar(import_calendar()))
        
#         #all_calendar = "all.ics"
#         #fixed_time = "2024-05-17T11:36:42.972298+02:00"
#         fixed_time=None
#         #build_Json(all_calendar, fixed_time)
        
#         location_data = verif_location("cours_du_jour.json", location)
        
#         current_courses = verif_time(location_data, fixed_time)
        
#         if current_courses:
#             messages = [{"Cours en cours": "true", "Début": course['start_time'], "Fin": course['end_time'], "Prof": course['organizer']} for course in current_courses]
#         else:
#             next_course_info = next_course("cours_du_jour.json", location, fixed_time)
#             if next_course_info:
#                 messages = [{"Prochain cours": next_course_info['start_time'], "Prof1": next_course_info['organizer']}]
#             else:
#                 messages = [{"message": "Aucun cours prévu aujourd'hui dans cette salle pour le reste de la journée."}]
        
#         return jsonify(messages)
#     else:
        # return render_template('index.html')
    
# # POST pour générer les données
# @app.route('/build_json', methods=['POST'])
# def build_json_route():
#     build_Json(combine_calendar(import_calendar()))
#     fixed_time = None
#     json1(fixed_time)
#     return jsonify({"status": "success"})

@app.route('/inh_api', methods=['POST'])
def build_response_api():
    
    paris_tz = pytz.timezone('Europe/Paris')
    #fixed_time = "2024-05-24T08:36:42.972298+02:00"
    fixed_time = None

    
    global oldTime
    
    newtime = datetime.now(paris_tz).timestamp()

    if oldTime is None:
        oldTime = newtime
    
    old_datetime = datetime.fromtimestamp(oldTime, paris_tz)
    new_datetime = datetime.fromtimestamp(newtime, paris_tz)
    
    if (newtime - oldTime) > (3600*6) or old_datetime.date() != new_datetime.date():
        build_Json(combine_calendar(import_calendar()),fixed_time)
        oldTime = newtime
    
    #verification de cbn temps j'ai télécharger les fichier et plus de 30min je retelecharge
  

    response = json1(fixed_time)
    return jsonify(response)


paris_tz = pytz.timezone('Europe/Paris')
oldTime = datetime.now(paris_tz).timestamp()

if __name__ == '__main__':
     app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))