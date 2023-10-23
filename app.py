from flask import Flask, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
import boto3
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
bcrypt = Bcrypt(app)

app.config['JWT_SECRET_KEY'] = os.getenv("JWT_SECRET_KEY")
app.config["JWT_ALGORITHM"] = os.getenv("JWT_ALGORITHM")

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DB_LOCAL_URI')
db = SQLAlchemy(app)

s3_bucket_name = os.getenv('S3_BUCKET_NAME')
aws_access_key = os.getenv('AWS_ACCESS_KEY')
aws_access_secret = os.getenv('AWS_ACCESS_SECRET')

app.config['S3_BUCKET'] = s3_bucket_name
app.config['S3_KEY'] = aws_access_key
app.config['S3_SECRET'] = aws_access_secret
app.config['S3_LOCATION'] = 'http://{}.s3.amazonaws.com/'.format(s3_bucket_name)

s3 = boto3.client(
   "s3",
   aws_access_key_id=app.config['S3_KEY'],
   aws_secret_access_key=app.config['S3_SECRET']
)

jwt = JWTManager(app)

class GalleryImages(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_file = db.Column(db.String)
    name = db.Column(db.String(150))

class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password_hash = db.Column(db.String(20))

@app.route('/images', methods=['GET'])
def get_all_images():
    images = GalleryImages.query.all()
    image_list = []
    for image in images:        
        image_info = {
            'id': image.id,
            'user_file': image.user_file,
            'name': image.name,
        }
        image_list.append(image_info)
    return jsonify(image_list)    

@app.route("/insert", methods=["POST"])
def upload_file():
    if "user_file" not in request.files:
        return "No user_file key in request.files"

    file = request.files["user_file"]

    if file.filename == "":
        return "Please select a file"

    if file:
        file.filename = secure_filename(file.filename)
        s3_url = upload_file_to_s3(file, app.config["S3_BUCKET"])

        new_image = GalleryImages(user_file=s3_url, name=file.filename)
        db.session.add(new_image)
        db.session.commit()

        return jsonify({'s3_url': s3_url})

    else:
        return redirect("/")
    
def upload_file_to_s3(file, bucket_name, acl="public-read"):
  try:
      s3.upload_fileobj(
          file,
          bucket_name,
          file.filename,
          ExtraArgs={
              "ACL": acl,
              "ContentType": file.content_type
          }
      )
  except Exception as e:
      print("An error has occurred: ", e)
      return e
  return "{}{}".format(app.config["S3_LOCATION"], file.filename)

@app.route('/update/<int:image_id>', methods=['PUT'])
def update_image(image_id):
    if request.method == 'PUT':
        data = request.get_json()
        name = data.get('name')

        image = GalleryImages.query.get(image_id)

        if image:
            image.name = name

            db.session.commit()

            return jsonify({'message': 'Image updated successfully'}), 200
        else:
            return jsonify({'message': 'Image not found'}), 404
        
@app.route('/delete_selected', methods=['DELETE'])
def delete_selected_images():
    if request.method == 'DELETE':
        selected_image_ids = request.get_json().get('imageIds')

        if not selected_image_ids:
            return jsonify({'message': 'No images selected'}), 400

        # Loop through the list of selected image IDs and delete them from the database
        for image_id in selected_image_ids:
            image = GalleryImages.query.get(image_id)
            if image:
                db.session.delete(image)
                db.session.commit()

        return jsonify({'message': 'Selected images deleted successfully'}), 200
        
    return jsonify({'message': 'Image not found'}), 400

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"message": "Username and password are required"}), 400
    
    user = Users.query.filter_by(username=username).first()
    if not user or not bcrypt.check_password_hash(user.password_hash, password):
        return jsonify({"message": "Invalid username or password"}), 401
    
    access_token = create_access_token(identity=user.id)
    
    return jsonify({"message": "Login successful!", "access token": access_token}), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
