import subprocess

from flask import Flask, Response, render_template, request


app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/clock')
def clock():
    tz = request.args.get('tz')
    if tz is None:
        return Response('', 400)
    try:
        date = subprocess.check_output(f'TZ={tz} date', shell=True, encoding='utf8')
    except:
        return Response('', 500)
    else:
        return render_template('clock.html', date=date)


def main():
    app.run()


if __name__ == '__main__':
    main()