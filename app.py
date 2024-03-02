from flask import Flask, render_template, request, redirect, url_for
import string
import random

app = Flask(__name__)
shortened_urls={}

def generate_shortened_url(length=6):
    characters = string.ascii_letters + string.digits
    url = ''.join(random.choice(characters)for _ in range(length))
    return url

