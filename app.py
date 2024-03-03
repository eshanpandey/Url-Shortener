from flask import Flask, render_template, request, redirect, url_for
import random
import string
import json
import os

app = Flask(__name__)
SHORTENED_URLS_FILE = 'shortened_urls.json'

def generate_shortened_url(shortened_urls, length=6):
    characters = string.ascii_letters + string.digits
    while True:
        url = ''.join(random.choice(characters) for _ in range(length))
        if url not in shortened_urls:
            return url

def save_shortened_urls(shortened_urls):
    with open(SHORTENED_URLS_FILE, 'w') as file:
        json.dump(shortened_urls, file)

def load_shortened_urls():
    if os.path.exists(SHORTENED_URLS_FILE):
        with open(SHORTENED_URLS_FILE, 'r') as file:
            return json.load(file)
    return {}

@app.route('/', methods=['GET', 'POST'])
def index():
    shortened_urls = load_shortened_urls()  # Load shortened URLs at the beginning
    if request.method == 'POST':
        long_url = request.form['long_url']
        custom_short_url = request.form.get('custom_short_url')
        if custom_short_url:
            short_url = custom_short_url
            if short_url in shortened_urls:
                return render_template('index.html', error="Custom short URL already exists. Please choose a different one.")
        else:
            short_url = generate_shortened_url(shortened_urls)
        shortened_urls[short_url] = long_url
        save_shortened_urls(shortened_urls)
        return render_template('success.html', short_url=f"{request.host_url}{short_url}")
    return render_template('index.html')

@app.route('/<short_url>')
def redirect_url(short_url):
    shortened_urls = load_shortened_urls()  # Load shortened URLs on every request
    long_url = shortened_urls.get(short_url)
    if long_url:
        return redirect(long_url)
    else:
        return f"URL for {short_url} not found", 404

if __name__ == '__main__':
    app.run(debug=False)
