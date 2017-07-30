# Bigfoot Sightings Dash App

This is an example of an app built with Plotly's [Dash](https://plot.ly/products/dash/) framework.
It's an exploratory app based on the [Bigfoot Sightings](https://data.world/timothyrenner/bfro-sightings-data) dataset I hosted on data.world.
It demonstrates several plots (including a map), a grid layout built with [Bootstrap](http://getbootstrap.com/), interactions with an input field, and caching.

There's also a Procfile for deploying on to Heroku.
That does require a little special sauce in the code - I've tried to be clear in the comments where that is so you can ignore it if you want.

## Quickstart

Create an environment with virtualenv or conda.
For conda,

```
conda create --name bigfoot-sightings-dash python=3.6
source activate bigfoot-sightings-dash
```

Install the stuff in `requirements.txt`.

```
pip install -r requirements.txt
```

Launch the app.

```
python app.py
```