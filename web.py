import os

from flask import Flask, redirect, render_template, request, url_for
from models import engine, Session, Base, Game

app = Flask(__name__)

app.secret_key = os.getenv("FLASK_SECRET")

Base.metadata.create_all(engine)

HYPERLINK = '<a href="{}">{}</a>'


@app.route('/')
def games_route():
    return render_template('server_table.html')

@app.route('/api/data')
def api_data_route():
    session = Session()
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
    session.close()

    # response
    return result


if __name__ == "__main__":
    from waitress import serve

    serve(app, host='0.0.0.0', port=80)
