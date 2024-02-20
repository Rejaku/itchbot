import os

from flask import Flask, render_template, request
from sqlalchemy import func

from models import engine, Session, Base, Game, Review, Reviewer, GameVersion

app = Flask(__name__)

app.secret_key = os.getenv("FLASK_SECRET")

Base.metadata.create_all(engine)

HYPERLINK = '<a href="{}">{}</a>'


@app.route('/')
def games_route():
    return render_template('server_table.html')

@app.route('/reviews/all')
def reviews_all_route():
    return render_template('review_all_table.html')

@app.route('/reviews/allall')
def reviews_allall_route():
    return render_template('review_allall_table.html')

@app.route('/reviews/<int:game_id>')
def reviews_route(game_id):
    with Session() as session:
        game = session.query(Game).filter(Game.id == game_id).first()

    return render_template('review_table.html', game_id=game.id, game_name=game.name, game_url=game.url)


@app.route('/users/<int:reviewer_id>')
def users_route(reviewer_id):
    return render_template('user_table.html', reviewer_id=reviewer_id)


@app.route('/versions/<int:game_id>')
def versions_route(game_id):
    with Session() as session:
        game = session.query(Game).filter(Game.id == game_id).first()

    return render_template('version_table.html', game_id=game.id, game_name=game.name, game_url=game.url)

@app.route('/api/data')
def api_data_route():
    with Session() as session:
        games = session.query(Game)

        # search filter
        search = request.args.get('search')
        if search:
            games = games.filter(Game.hidden == False, Game.name.like(f'%{search}%'))
        else:
            games = games.filter(Game.hidden == False)
        total = games.count()

        # sorting
        sort = request.args.get('sort') or '-updated_at'
        if sort:
            order = []
            for s in sort.split(','):
                direction = s[0]
                name = s[1:]
                if name not in ['name', 'rating', 'created_at', 'updated_at', 'stats_menus', 'stats_words', 'game_engine', 'status', 'nsfw']:
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


@app.route('/api/reviews/<int:game_id>')
def api_reviews_route(game_id):
    with (Session() as session):
        reviews = session.query(Review).filter(Review.game_id == int(game_id), Review.hidden == False, Review.has_review == True)
        total = reviews.count()

        # sorting
        sort = request.args.get('sort') or '-updated_at'
        if sort:
            order = []
            for s in sort.split(','):
                direction = s[0]
                name = s[1:]
                if name not in ['updated_at', 'reviewer_id', 'rating']:
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

@app.route('/api/users/<reviewer_id>')
def api_users_route(reviewer_id):
    with Session() as session:
        if reviewer_id == 'all':
            reviews = session.query(Review, Game).join(
                Game, Review.game_id == Game.id
            ).filter(
                Review.hidden == False,
                Review.has_review == True,
                Game.hidden == False
            )
        elif reviewer_id == 'allall':
            reviews = session.query(Review, Game).join(
                Game, Review.game_id == Game.id
            ).filter(
                Review.hidden == False,
                Review.has_review == True
            )
        else:
            reviews = session.query(Review, Game).join(
                Game, Review.game_id == Game.id
            ).filter(
                Review.reviewer_id == int(reviewer_id),
                Review.hidden == False,
                Review.has_review == True
            )
        total = reviews.count()

        # sorting
        sort = request.args.get('sort') or '-updated_at'
        if sort:
            order = []
            for s in sort.split(','):
                direction = s[0]
                name = s[1:]
                if name in ['name']:
                    col = getattr(Game, name)
                else:
                    if name not in ['updated_at', 'rating', 'reviewer_id']:
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
            'data': [game.to_dict() | review.to_dict() for review, game in reviews],
            'total': total,
        }

    # response
    return result

@app.route('/api/versions/<int:game_id>')
def api_versions_route(game_id):
    with Session() as session:
        game_versions = session.query(GameVersion).filter(GameVersion.game_id == int(game_id))
        total = game_versions.count()

        # sorting
        sort = request.args.get('sort') or '-released_at'
        if sort:
            order = []
            for s in sort.split(','):
                direction = s[0]
                name = s[1:]
                if name not in ['released_at', 'stats_menus', 'stats_words']:
                    name = 'released_at'
                col = getattr(GameVersion, name)
                if direction == '-':
                    col = col.desc()
                order.append(col)
            if order:
                game_versions = game_versions.order_by(*order)

        # pagination
        start = request.args.get('start', type=int, default=-1)
        length = request.args.get('length', type=int, default=-1)
        if start != -1 and length != -1:
            game_versions = game_versions.offset(start).limit(length)

        result = {
            'data': [game_version.to_dict() for game_version in game_versions],
            'total': total,
        }

    # response
    return result


if __name__ == "__main__":
    from waitress import serve

    serve(app, host='0.0.0.0', port=80)
