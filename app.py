from flask import Flask, render_template, request, redirect
import random
import string

app = Flask(__name__)
shortened_urls={}

def generate_shortened_url(length=6):
    characters = string.ascii_letters + string.digits
    url = ''.join(random.choice(characters)for _ in range(length))
    return url

@app.route('/', methods=['GET', 'POST'])
 
def index():
 if request.method == 'POST':
    long_url = request.form['long_url']
    short_url=generate_shortened_url()
    while short_url in shortened_urls:
        short_url=generate_shortened_url()
        
    shortened_urls[short_url]=long_url
    return f"Shortened URL: {request.host_url}{short_url}"
 return render_template('index.html')

@app.route('/<short_url>')
def redirect_url(short_url):
    long_url=shortened_urls.get(short_url)
    if long_url:
        return redirect(long_url)
    else:
        return f"URL for {short_url} not found", 404

if __name__ == '__main__':
   app.run(debug=True)

   

