from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from app import app, db, login
from hashlib import md5


@login.user_loader
def load_user(uid):
    print(f"user query = {User.query.get(int(uid))}")
    return User.query.get(int(uid))


followers = db.Table('followers',
                     db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
                     db.Column('followed_id', db.Integer, db.ForeignKey('user.id')),
                     db.UniqueConstraint('follower_id', 'followed_id')
                     )

likes = db.Table('likes',
                 db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
                 db.Column('post_id', db.Integer, db.ForeignKey('post.id')),
                 db.UniqueConstraint('user_id', 'post_id')
                 )


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    tags = db.relationship('Tags', backref='author', lazy='dynamic')
    info = db.Column(db.String(140))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

    followed = db.relationship(
        'User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')

    # liked = db.relationship(
    #     'User', secondary=likes,
    #     primaryjoin=(likes.c.user_id == id),
    #     backref=db.backref('likes', lazy='dynamic'), lazy='dynamic')

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(digest, size)

    def is_following(self, user):
        return self.followed.filter(followers.c.followed_id == user.id).count() > 0

    def follow(self, user_to_follow):
        if not self.is_following(user_to_follow):
            self.followed.append(user_to_follow)

    def unfollow(self, user_to_follow):
        if self.is_following(user_to_follow):
            self.followed.remove(user_to_follow)

    def followed_posts(self):
        followed = Post.query.join(followers, (followers.c.followed_id == Post.user_id)).filter(
            followers.c.follower_id == self.id)
        own = Post.query.filter_by(user_id=self.id)
        return followed.union(own).order_by(Post.timestamp.desc())


class Tags(db.Model):
    tag_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(30))
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return '{}'.format(self.title)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    body = db.Column(db.String(app.config['POST_LENGTH_LIMIT']))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    tag_id = db.Column(db.Integer, db.ForeignKey('tags.tag_id'))
    post_likes = db.relationship(
        'User', secondary=likes,
        primaryjoin=(likes.c.post_id == id),
        backref=db.backref('likes', lazy='dynamic'), lazy='dynamic')

    def get_tag(self):
        return Tags.query.get(self.tag_id)

    def count_likes(self):
        return self.post_likes.filter(likes.c.post_id == self.id).count()

    def get_likes(self):
        return self.post_likes.filter(likes.c.post_id == self.id)

    def is_liked(self, user):
        return self.post_likes.filter(likes.c.user_id == user.id).count() > 0

    def like(self, from_who):
        self.post_likes.append(from_who)

    def unlike(self, user_to_follow):
        if self.is_liked(user_to_follow):
            self.post_likes.remove(user_to_follow)

    def __repr__(self):
        return '<Post {}>'.format(self.body)
