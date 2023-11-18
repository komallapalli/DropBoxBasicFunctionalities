from flask import Flask, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)

# SQLite database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database
db = SQLAlchemy(app)


class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    size = db.Column(db.Integer)
    file_type = db.Column(db.String(255))

    def as_dict(self):
        return {'file_id': self.id, 'file_name': self.file_name,
                'created_at': self.created_at.isoformat(), 'size': self.size, 'file_type': self.file_type}


# Error Handling to ensure valid extensions.
# Added this to make sure the client will not upload random things.
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}


@app.route('/files/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Save metadata to SQLite database
        new_file = File(file_name=filename, size=os.path.getsize(file_path), file_type=file.content_type)
        db.session.add(new_file)
        db.session.commit()

        return jsonify({'file_id': new_file.id}), 201

    return jsonify({'error': 'Invalid file type'}), 400


@app.route('/files/<int:file_id>', methods=['GET'])
def read_file(file_id):
    file = File.query.get(file_id)

    if file:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.file_name)
        return send_file(file_path, as_attachment=True)
    else:
        return jsonify({'error': 'File not found'}), 404


@app.route('/files/<int:file_id>', methods=['PUT'])
def update_file(file_id):
    file = File.query.get(file_id)

    if not file:
        return jsonify({'error': 'File not found'}), 404

    if 'file' in request.files:
        # Update file content
        new_file = request.files['file']
        if allowed_file(new_file.filename):
            filename = secure_filename(new_file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            new_file.save(file_path)
            file.file_name = filename
            file.size = os.path.getsize(file_path)
            file.file_type = new_file.content_type
            db.session.commit()
        else:
            return jsonify({'error': 'Invalid file type'}), 400
    else:
        # Update metadata
        new_metadata = request.json
        for key, value in new_metadata.items():
            setattr(file, key, value)
        db.session.commit()

    return jsonify(file.as_dict()), 200


@app.route('/files/<int:file_id>', methods=['DELETE'])
def delete_file(file_id):
    file = File.query.get(file_id)

    if not file:
        return jsonify({'error': 'File not found'}), 404

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.file_name)
    os.remove(file_path)

    db.session.delete(file)
    db.session.commit()

    return jsonify({'message': 'File deleted successfully'}), 200


@app.route('/files', methods=['GET'])
def list_files():
    files = File.query.all()
    return jsonify([file.as_dict() for file in files])


if __name__ == '__main__':
    # Create tables in the database
    db.create_all()
    app.run(debug=True)
