from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
  __tablename__ = 'users'
  userID =        db.Column(db.Integer, primary_key=True, autoincrement=True)
  name =          db.Column(db.String(64), nullable=False)
  email =         db.Column(db.String(64), nullable=False)
  linkedinURL =   db.Column(db.String(130), nullable=False)
  timezone =      db.Column(db.String(64), nullable=False)
  optedIn =       db.Column(db.Boolean, nullable=False)
