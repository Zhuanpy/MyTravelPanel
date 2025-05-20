from flask import Flask, render_template
from jinja2 import Environment, FileSystemLoader, TemplateSyntaxError

app = Flask(__name__)

# Create a Jinja environment
env = Environment(loader=FileSystemLoader('App/templates'))

try:
    # Try to load and parse the template
    template = env.get_template('flights/order_create.html')
    print("Template loaded successfully!")
except TemplateSyntaxError as e:
    print(f"Syntax error in template: {e}")
    print(f"Error on line {e.lineno}: {e.message}")
    print(f"In file: {e.filename}")
except Exception as e:
    print(f"Error loading template: {e}") 