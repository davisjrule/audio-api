import json
import os
import math
from flask import Flask
from flask import jsonify
from flask import request, redirect, url_for, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from tinytag import TinyTag

UPLOAD_FOLDER = '/Users/davisrule/src/deepgram-audio-api/uploads'

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db = SQLAlchemy(app)

class AudioFiles(db.Model):
    id = db.Column("id", db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    duration = db.Column(db.Float)
    size = db.Column(db.Integer)

    def __init__(self, name, duration, size):
        self.name = name
        self.duration = duration
        self.size = size


# Build database before first request
@app.before_first_request
def create_tables():
    db.create_all()


@app.route('/')
def index():
    return "Hello world!"


# POST audio files to uploads
# Example usage: curl -X POST -F file=@"/Users/davisrule/Desktop/audio_files/cantina.wav" http://127.0.0.1:5000/upload
#                curl -X POST -F file=@"/Users/davisrule/Desktop/audio_files/starwars.wav" http://127.0.0.1:5000/upload
#                curl -X POST -F file=@"/Users/davisrule/Desktop/audio_files/preamble.wav" http://127.0.0.1:5000/upload
@app.route('/upload', methods=['POST', 'PUT'])
def upload():
    if request.method == 'POST':
        file = request.files['file']
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        # add to DB
        filepath = str(UPLOAD_FOLDER + '/' + filename)
        tinytag_audio = TinyTag.get(filepath) 
        audio = AudioFiles(filename, round(tinytag_audio.duration, 3), tinytag_audio.filesize)
        db.session.add(audio)
        db.session.commit()

        return str(filename + " succesfully uploaded!")


# GET an audio file from uploads
# Example usage: http://127.0.0.1:5000/download/name=preamble.wav
@app.route('/download/name=<filename>')
def download(filename):

    found_audio = AudioFiles.query.filter_by(name=filename).first()
    if(found_audio):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    return "Requested file not in database."


# GET a list of audio files in uploads
# RETURNS: JSON with the file names
# Example usage: http://127.0.0.1:5000/list
# Example usage (with query): http://127.0.0.1:5000/maxduration=10
@app.route('/list', methods=['GET'])
@app.route('/list/maxduration=<maxduration>', methods = ['GET'])
def list(maxduration=math.inf):
    list = AudioFiles.query.filter(AudioFiles.duration < maxduration).all()
    output = {}
    for file in list:
        output[file.name] = file.duration

    return jsonify(output)


# GET the metadata for an individual audio file
# RETURNS: JSON with the file name, duration (in seconds), and filesize (in bytes)
# Example usage: http://127.0.0.1:5000/info/preamble.wav
@app.route('/info/name=<filename>')
def info(filename):
    # if file in database
    found_audio = AudioFiles.query.filter_by(name=filename).first()
    if(found_audio):
        audio_data = {'name': found_audio.name, 
                      'duration': round(found_audio.duration, 3), 
                      'size': found_audio.size} 
        return jsonify(audio_data)

    return "Requested file not in database."


if __name__ == '__main__':
    if not os.path.exists('db.sqlite'):
        db.create_all()
    app.run(debug=True)
