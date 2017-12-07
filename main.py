from flask import Flask, render_template
app = Flask(__name__)
app.config['DEBUG'] = True

@app.route("/")
def main():
	return render_template('index.html')

@app.route("/table")
def table():
	return render_template('table.html')

if __name__ == "__main__":
	app.run(host="0.0.0.0")

