from flask import Flask, request, render_template_string
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
index_html = '''
<!doctype html>
<title>Simple Crawler</title>
<h1>Enter a URL to fetch its title</h1>
<form method=post>
  <input type=text name=url style="width:400px">
  <input type=submit value=Fetch>
</form>
{% if title %}
  <h2>Page Title:</h2>
  <p>{{ title }}</p>
{% endif %}
'''

@app.route('/', methods=['GET', 'POST'])
def index():
    title = None
    if request.method == 'POST':
        url = request.form['url']
        try:
            resp = requests.get(url)
            soup = BeautifulSoup(resp.text, 'html.parser')
            title = soup.title.string.strip() if soup.title else 'No title found'
        except Exception as e:
            title = f'Error: {e}'
    return render_template_string(index_html, title=title)

if __name__ == '__main__':
    app.run(debug=True)
