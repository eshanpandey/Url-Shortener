from flask import Flask, render_template, request, redirect, url_for
import random
import string
import json
import os

app = Flask(__name__)
shortened_urls = {}

def generate_shortened_url(length=6):
    characters = string.ascii_letters + string.digits
    while True:
        url = ''.join(random.choice(characters) for _ in range(length))
        if url not in shortened_urls:
            return url

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        long_url = request.form['long_url']
        custom_short_url = request.form.get('custom_short_url')
        if custom_short_url:
            short_url = custom_short_url
            if short_url in shortened_urls:
                return render_template('index.html', error="Custom short URL already exists. Please choose a different one.")
        else:
            short_url = generate_shortened_url()
        shortened_urls[short_url] = long_url
        save_shortened_urls()
        return render_template('success.html', short_url=f"{request.host_url}{short_url}")
    return render_template('index.html')

@app.route('/<short_url>')
def redirect_url(short_url):
    long_url = shortened_urls.get(short_url)
    if long_url:
        return redirect(long_url)
    else:
        return f"URL for {short_url} not found", 404

def save_shortened_urls():
    with open('shortened_urls.json', 'w') as file:
        json.dump(shortened_urls, file)

def load_shortened_urls():
    if os.path.exists('shortened_urls.json'):
        with open('shortened_urls.json', 'r') as file:
            return json.load(file)
    return {}

if __name__ == '__main__':
    shortened_urls = load_shortened_urls()
    app.run(debug=False)
