from flask import Flask, request, jsonify, send_file
import os
from datetime import datetime
from werkzeug.utils import secure_filename


app = Flask(__name__)

# Storage directory for uploaded files. 
# Note: We need to create uploads folder before running the code.
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# In-memory database to store file metadata
file_database = []


# Error Handling to ensure valid extensions. 
# Added this to make sure client will not upload random things.
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}


@app.route('/files/upload', methods=['POST'])
def upload_file():
    # Check if the equest has the file part
    # If not send Bad Request Status Code.
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        # Save the file
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Metadata
        metadata = {
            'file_id': len(file_database) + 1,
            'file_name': filename,
            'created_at': datetime.utcnow().isoformat(),
            'size': os.path.getsize(file_path),
            'file_type': file.content_type
        }
        
        # Storing Metadata in in-memory database.
        file_database.append(metadata)

        return jsonify({'file_id': metadata['file_id']}), 201

    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/files/<int:file_id>', methods=['GET'])
def read_file(file_id):
    file_metadata = next((file for file in file_database if file['file_id'] == file_id), None)

    if file_metadata:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_metadata['file_name'])
        print(f"File path: {file_path}")
        return send_file(file_path, as_attachment=True)
    else:
        return jsonify({'error': 'File not found'}), 404


@app.route('/files/<int:file_id>', methods=['PUT'])
def update_file(file_id):
    file_metadata = next((file for file in file_database if file['file_id'] == file_id), None)

    if not file_metadata:
        return jsonify({'error': 'File not found'}), 404

    if 'file' in request.files:
        # Update file content
        new_file = request.files['file']
        if allowed_file(new_file.filename):
            filename = secure_filename(new_file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            new_file.save(file_path)
            file_metadata['file_name'] = filename
            file_metadata['size'] = os.path.getsize(file_path)
            file_metadata['file_type'] = new_file.content_type
        else:
            return jsonify({'error': 'Invalid file type'}), 400
    else:
        # Update metadata
        new_metadata = request.json
        file_metadata.update(new_metadata)

    return jsonify(file_metadata), 200

@app.route('/files/<int:file_id>', methods=['DELETE'])
def delete_file(file_id):
    global file_database

    file_metadata = next((file for file in file_database if file['file_id'] == file_id), None)

    if not file_metadata:
        return jsonify({'error': 'File not found'}), 404

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_metadata['file_name'])
    os.remove(file_path)

    file_database = [file for file in file_database if file['file_id'] != file_id]

    return jsonify({'message': 'File deleted successfully'}), 200


@app.route('/files', methods=['GET'])
def list_files():
    return jsonify(file_database)


if __name__ == '__main__':
    app.run(debug=True)
