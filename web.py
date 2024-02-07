import os

from flask import Flask, render_template, request
from models import engine, Session, Base, Game, Review

app = Flask(__name__)

app.secret_key = os.getenv("FLASK_SECRET")

Base.metadata.create_all(engine)

HYPERLINK = '<a href="{}">{}</a>'


@app.route('/')
def games_route():
    return render_template('server_table.html')

@app.route('/reviews/<int:game_id>')
def reviews_route(game_id):
    with Session() as session:
        game = session.query(Game).filter(Game.game_id == game_id).first()
        game_name = None
        if game:
            game_name = game.name
        else:
            review = session.query(Review).filter(Review.game_id == game_id).order_by(Review.created_at.desc()).first()
            if review:
                game_name = review.game_name

    return render_template('review_table.html', game_id=game_id, game_name=game_name)

@app.route('/users/<int:user_id>')
def users_route(user_id):
    return render_template('user_table.html', user_id=user_id)

@app.route('/api/data')
def api_data_route():
    with Session() as session:
        games = session.query(Game)

        # search filter
        search = request.args.get('search')
        if search:
            games = games.filter(Game.name.like(f'%{search}%'))
        total = games.count()

        # sorting
        sort = request.args.get('sort') or '-updated_at'
        if sort:
            order = []
            for s in sort.split(','):
                direction = s[0]
                name = s[1:]
                if name not in ['name', 'rating', 'created_at', 'updated_at', 'stats_menus', 'stats_words', 'game_engine', 'status']:
                    name = 'name'
                col = getattr(Game, name)
                if direction == '-':
                    col = col.desc()
                order.append(col)
            if order:
                games = games.order_by(*order)

        # pagination
        start = request.args.get('start', type=int, default=-1)
        length = request.args.get('length', type=int, default=-1)
        if start != -1 and length != -1:
            games = games.offset(start).limit(length)

        result = {
            'data': [game.to_dict() for game in games],
            'total': total,
        }

    # response
    return result

@app.route('/api/reviews/<game_id>')
def api_reviews_route(game_id):
    with Session() as session:
        reviews = session.query(Review).filter(Review.game_id == int(game_id), Review.review != '').group_by(Review.user_id)
        total = reviews.count()

        # sorting
        sort = request.args.get('sort') or '-updated_at'
        if sort:
            order = []
            for s in sort.split(','):
                direction = s[0]
                name = s[1:]
                if name not in ['updated_at', 'user_id', 'rating', 'review']:
                    name = 'updated_at'
                col = getattr(Review, name)
                if direction == '-':
                    col = col.desc()
                order.append(col)
            if order:
                reviews = reviews.order_by(*order)

        # pagination
        start = request.args.get('start', type=int, default=-1)
        length = request.args.get('length', type=int, default=-1)
        if start != -1 and length != -1:
            reviews = reviews.offset(start).limit(length)

        result = {
            'data': [review.to_dict() for review in reviews],
            'total': total,
        }

    # response
    return result

@app.route('/api/users/<user_id>')
def api_users_route(user_id):
    with Session() as session:
        reviews = session.query(Review).filter(Review.user_id == int(user_id), Review.review != '')
        total = reviews.count()

        # sorting
        sort = request.args.get('sort') or '-updated_at'
        if sort:
            order = []
            for s in sort.split(','):
                direction = s[0]
                name = s[1:]
                if name not in ['updated_at', 'rating', 'review']:
                    name = 'updated_at'
                col = getattr(Review, name)
                if direction == '-':
                    col = col.desc()
                order.append(col)
            if order:
                reviews = reviews.order_by(*order)

        # pagination
        start = request.args.get('start', type=int, default=-1)
        length = request.args.get('length', type=int, default=-1)
        if start != -1 and length != -1:
            reviews = reviews.offset(start).limit(length)

        result = {
            'data': [review.to_dict() for review in reviews],
            'total': total,
        }

    # response
    return result

if __name__ == "__main__":
    from waitress import serve

    serve(app, host='0.0.0.0', port=80)
