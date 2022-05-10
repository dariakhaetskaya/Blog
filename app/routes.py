from sqlalchemy.exc import IntegrityError
from app import app, db
from app.forms import LoginForm, PostForm, RegistrationForm, EditProfileForm, TagForm, SearchFrom
from flask import render_template, flash, redirect, url_for, request
from flask_login import current_user, login_user, login_required, logout_user
from datetime import datetime
from app.models import User, Post, Tags
from werkzeug.urls import url_parse


@app.before_request
def before_request():
    print(f"curr user = {current_user}")
    if current_user.is_authenticated:
        # update last seen time any time user refresh page
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


@app.route('/login', methods=['GET', 'POST'])
def login():
    # redirect authenticated users to their feed page
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    # else show login form
    form = LoginForm()
    if form.validate_on_submit():
        # find submitted username in the db
        user = User.query.filter_by(username=form.username.data).first()
        # check user's password
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('index'))
        # if everything is ok, login
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)

    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    # create form for post upload
    form = PostForm()
    if form.validate_on_submit():
        post = Post(body=form.post.data, author=current_user, title=form.title.data, tag_id=form.tag.data)
        db.session.add(post)
        db.session.commit()
        flash('Your post is now live!')
        return redirect(url_for('index'))

    # load posts
    page = request.args.get('page', 1, type=int)
    posts = current_user.followed_posts().paginate(
        page, app.config['POSTS_PER_PAGE'], False
    )
    next_url = url_for('index', page=posts.next_num) if posts.has_next else None
    prev_url = url_for('index', page=posts.prev_num) if posts.has_prev else None

    return render_template(
        'index.html',
        title='Home Page',
        form=form,
        posts=posts.items,
        next_url=next_url,
        prev_url=prev_url)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    # create and handle registration form
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations! You are now a registered user!')
        return redirect(url_for('login'))

    return render_template('register.html', title="Register", form=form)


@app.route('/user/<username>')
@login_required
def user(username):
    # find the requested user in a db
    user = User.query.filter_by(username=username).first_or_404()

    # load pages with posts
    page = request.args.get('page', 1, type=int)
    posts = user.posts.order_by(Post.timestamp.desc()).paginate(page, app.config['POSTS_PER_PAGE'], False)

    next_url = url_for('user', username=user.username, page=posts.next_num) if posts.has_next else None
    prev_url = url_for('user', username=user.username, page=posts.prev_num) if posts.has_prev else None

    return render_template('user.html', user=user, posts=posts.items, next_url=next_url, prev_url=prev_url)


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)

    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.info = form.info.data
        db.session.commit()
        flash('Your changes have been saved')
        return user(current_user.username)
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.info.data = current_user.info

    return render_template('edit_profile.html', title="Edit Profile", form=form)


@app.route('/follow/<username>')
@login_required
def follow(username):

    user = User.query.filter_by(username=username).first()

    if user is None:
        flash('User {} not found'.format(username))
        return redirect(url_for('index'))
    if user == current_user:
        flash('You cannot follow yourself!')
        return redirect(url_for('user', username=username))

    current_user.follow(user)
    db.session.commit()
    flash('You are following {}!'.format(username))

    return redirect(url_for('user', username=username))


@app.route('/like/<post_id>')
@login_required
def like(post_id):

    post = Post.query.filter_by(id=post_id).first()

    if post is None:
        flash('Post not found')
        return redirect(url_for('index'))
    if post.user_id == current_user.id:
        flash('You cannot like your own posts!')
        return redirect(url_for('explore'))

    post.like(current_user)

    try:
        db.session.commit()
        flash('Success!')
    except IntegrityError:
        db.session.rollback()
        flash('You already liked this post')

    return redirect(url_for('explore'))

@app.route('/likes/<post_id>')
@login_required
def likes(post_id):

    post = Post.query.filter_by(id=post_id).first()

    if post is None:
        flash('Post not found')
        return redirect(url_for('index'))

    page = request.args.get('page', 1, type=int)

    users = Post.get_likes(post).paginate(
        page, app.config['USERS_PER_PAGE'], False
    )

    next_url = url_for('explore', page=users.next_num) if users.has_next else None
    prev_url = url_for('explore', page=users.prev_num) if users.has_prev else None

    return render_template(
        'likes.html',
        title='Explore',
        users=users.items,
        next_url=next_url,
        prev_url=prev_url)



@app.route('/unfollow/<username>')
@login_required
def unfollow(username):

    user = User.query.filter_by(username=username).first()

    if user is None:
        flash('User {} not found'.format(username))
        return redirect(url_for('index'))
    if user == current_user:
        flash('You cannot unfollow yourself!')
        return redirect(url_for('user', username=username))

    current_user.unfollow(user)
    db.session.commit()
    flash('You are no longer following {}!'.format(username))

    return redirect(url_for('user', username=username))


@app.route('/explore')
@login_required
def explore():

    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.timestamp.desc()).paginate(
        page, app.config['POSTS_PER_PAGE'], False
    )

    next_url = url_for('explore', page=posts.next_num) if posts.has_next else None
    prev_url = url_for('explore', page=posts.prev_num) if posts.has_prev else None

    return render_template(
        'index.html',
        title='Explore',
        posts=posts.items,
        next_url=next_url,
        prev_url=prev_url)


@app.route('/tag/<tag_id>')
@login_required
def tag(tag_id):

    page = request.args.get('page', 1, type=int)
    posts = Post.query.filter_by(tag_id=tag_id).paginate(
        page, app.config['POSTS_PER_PAGE'], False
    )

    next_url = url_for('tag', page=posts.next_num) if posts.has_next else None
    prev_url = url_for('tag', page=posts.prev_num) if posts.has_prev else None

    return render_template(
        'index.html',
        title='Explore',
        posts=posts.items,
        next_url=next_url,
        prev_url=prev_url)


@app.route('/search', methods=['POST'])
@login_required
def search():

    search_form = SearchFrom()
    page = request.args.get('page', 1, type=int)
    posts = Post.query.filter(Post.title.like('%' + search_form.query.data + '%')).paginate(
        page, app.config['POSTS_PER_PAGE'], False
    )

    next_url = url_for('tag', page=posts.next_num) if posts.has_next else None
    prev_url = url_for('tag', page=posts.prev_num) if posts.has_prev else None

    return render_template(
        'index.html',
        title='Explore',
        posts=posts.items,
        next_url=next_url,
        prev_url=prev_url)