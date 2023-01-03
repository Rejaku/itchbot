import os

from flask import Flask, redirect, render_template, request, url_for
from flask_discord import DiscordOAuth2Session, requires_authorization
from models import engine, Session, Base, VisualNovel

app = Flask(__name__)

app.secret_key = os.getenv("FLASK_SECRET")
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "true"  # !! Only in development environment.

app.config["DISCORD_CLIENT_ID"] = os.getenv("DISCORD_CLIENT_ID")
app.config["DISCORD_CLIENT_SECRET"] = os.getenv("DISCORD_CLIENT_SECRET")
app.config["DISCORD_BOT_TOKEN"] = os.getenv("DISCORD_API_KEY")
app.config["DISCORD_REDIRECT_URI"] = os.getenv("DISCORD_REDIRECT_URI")

discord = DiscordOAuth2Session(app)

Base.metadata.create_all(engine)
session = Session()

HYPERLINK = '<a href="{}">{}</a>'


@app.route("/")
def index():
    if not discord.authorized:
        return f"""
        {HYPERLINK.format(url_for(".login"), "Login")} <br />
        {HYPERLINK.format(url_for(".login_with_data"), "Login with custom data")} <br />
        {HYPERLINK.format(url_for(".invite_bot"), "Invite Bot with permissions 3072 (Read & Send Messages)")} <br />
        {HYPERLINK.format(url_for(".invite_oauth"), "Authorize with oauth and bot invite")}
        """

    return f"""
    {HYPERLINK.format(url_for(".me"), "@ME")}<br />
    {HYPERLINK.format(url_for(".invite_bot"), "Invite Bot with permissions 3072 (Read & Send Messages)")} <br />
    {HYPERLINK.format(url_for(".logout"), "Logout")}<br />
    """


@app.route("/login/")
def login():
    return discord.create_session()


@app.route("/login-data/")
def login_with_data():
    return discord.create_session(data=dict(redirect="/me/", coupon="15off", number=15, zero=0, status=False))


@app.route("/invite-bot/")
def invite_bot():
    return discord.create_session(scope=["bot"], permissions=3072)


@app.route("/invite-oauth/")
def invite_oauth():
    return discord.create_session(scope=["bot", "identify"], permissions=3072)


@app.route("/callback/")
def callback():
    data = discord.callback()

    return redirect(data.get("redirect", "/"))


@app.route("/me/")
def me():
    user = discord.fetch_user()
    return f"""
<html>
<head>
<title>{user.name}</title>
</head>
<body><img src='{user.avatar_url or user.default_avatar_url}' />
<p>Is avatar animated: {str(user.is_avatar_animated)}</p>
</body>
</html>

"""


@app.route('/games/')
def games():
    return render_template('server_table.html')


@app.route('/api/data')
def api_data():
    visual_novels = session.query(VisualNovel)

    # search filter
    search = request.args.get('search')
    if search:
        visual_novels = visual_novels.filter(VisualNovel.name.like(f'%{search}%'))
    total = visual_novels.count()

    # sorting
    sort = request.args.get('sort') or '+name'
    if sort:
        order = []
        for s in sort.split(','):
            direction = s[0]
            name = s[1:]
            if name not in ['name', 'updated_at']:
                name = 'name'
            col = getattr(VisualNovel, name)
            if direction == '-':
                col = col.desc()
            order.append(col)
        if order:
            visual_novels = visual_novels.order_by(*order)

    # pagination
    start = request.args.get('start', type=int, default=-1)
    length = request.args.get('length', type=int, default=-1)
    if start != -1 and length != -1:
        visual_novels = visual_novels.offset(start).limit(length)

    # response
    return {
        'data': [visual_novel.to_dict() for visual_novel in visual_novels],
        'total': total,
    }


@app.route("/logout/")
def logout():
    discord.revoke()
    return redirect(url_for(".index"))


@app.route("/secret/")
@requires_authorization
def secret():
    return os.urandom(16)


if __name__ == "__main__":
    from waitress import serve

    serve(app, host='0.0.0.0', port=80)
