import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
from flask_caching import Cache
import plotly.graph_objs as go

from csv import DictReader
from toolz import compose, pluck, groupby, valmap, first, unique, get, countby
import datetime as dt
from dotenv import find_dotenv,load_dotenv

import os

load_dotenv(find_dotenv())

# Helpers.
listpluck = compose(list, pluck)
listfilter = compose(list, filter)
listmap = compose(list, map)
listunique = compose(list, unique)

def extract_year(sighting_ts):
    return dt.datetime.strptime(sighting_ts, "%Y-%m-%dT%H:%M:%SZ").year

def extract_dow(sighting_ts):
    return dt.datetime.strptime(sighting_ts, "%Y-%m-%dT%H:%M:%SZ")\
                      .strftime("%a")

def sighting_year(sighting):
    return extract_year(sighting['timestamp'])

def sighting_dow(sighting):
    return extract_dow(sighting['timestamp'])

def bigfoot_map(sightings):
    classifications = groupby('classification', sightings)
    return {
        "data": [
                {
                    "type": "scattermapbox",
                    "lat": listpluck("latitude", class_sightings),
                    "lon": listpluck("longitude", class_sightings),
                    "text": listpluck("title", class_sightings),
                    "mode": "markers",
                    "name": classification,
                    "marker": {
                        "size": 3,
                        "opacity": 1.0
                    }
                }
                for classification, class_sightings in classifications.items()
            ],
        "layout": {
            "autosize": True,
            "hovermode": "closest",
            "mapbox": {
                "accesstoken": os.environ.get("MAPBOX_KEY"),
                "bearing": 0,
                "center": {
                    "lat": 40,
                    "lon": -98.5
                },
                "pitch": 0,
                "zoom": 2,
                "style": "outdoors"
            }
        },
        "config": {
            "displayModeBar": False
        }
    }

def bigfoot_by_year(sightings):
    # Create a dict mapping the 
    # classification -> [(year, count), (year, count) ... ]
    sightings_by_year = {
        classification: 
            sorted(
                list(
                    # Group by year -> count.
                    countby(sighting_year, class_sightings).items()
                ),
                # Sort by year.
                key=first
            )
        for classification, class_sightings 
        in groupby('classification', sightings).items()
    }

    # Build the plot with a dictionary.
    return {
        "data": [
            {
                "type": "scatter",
                "mode": "lines+markers",
                "name": classification,
                "x": listpluck(0, class_sightings_by_year),
                "y": listpluck(1, class_sightings_by_year)
            }
            for classification, class_sightings_by_year 
            in sightings_by_year.items()
        ],
        "layout": {
            "title": "Sightings by Year",
            "showlegend": False
        },
        "config": {
            "displayModeBar": False
        }
    }

def bigfoot_dow(sightings):
    
    # Produces a dict (year, dow) => count.
    sightings_dow = countby("dow",
        [
            {
                "dow": sighting_dow(sighting)
            } 
            for sighting in sightings
        ]
    )

    dows =  ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

    return {
        "data": [
            {
                "type": "bar",
                "x": dows,
                "y": [get(d, sightings_dow, 0) for d in dows]
            }
        ],
        "layout": {
            "title": "Sightings by Day of Week",
        },
        "config": {
            "displayModeBar": False
        }
    }

def bigfoot_class(sightings):
    sightings_by_class = countby("classification", sightings)

    return {
        "data": [
            {
                "type": "pie",
                "labels": list(sightings_by_class.keys()),
                "values": list(sightings_by_class.values()),
                "hole": 0.4
            }
        ],
        "layout": {
            "title": "Sightings by Class"
        }
    }

# Read the data.
fin = open('data/bfro_report_locations.csv','r')
reader = DictReader(fin)
BFRO_LOCATION_DATA = \
[
    line for line in reader 
    if (sighting_year(line) <= 2017) and (sighting_year(line) >= 1900)
]
fin.close()

app = dash.Dash()
# For Heroku deployment.
server = app.server
app.title = "Bigfoot Sightings"
cache = Cache(app.server, config={"CACHE_TYPE": "simple"})

# This function can be memoized because it's called for each graph, so it will
# only get called once per filter text.
@cache.memoize(50)
def filter_sightings(filter_text):
    return listfilter(
            lambda x: filter_text.lower() in x['title'].lower(),
            BFRO_LOCATION_DATA
        )

app.css.append_css({
    "external_url": "https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css"
})

app.css.append_css({
    "external_url": 'https://codepen.io/chriddyp/pen/bWLwgP.css'
})

app.scripts.append_script({
    "external_url": "https://code.jquery.com/jquery-3.2.1.min.js"
})

app.scripts.append_script({
    "external_url": "https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/js/bootstrap.min.js"
})

app.layout = html.Div([
    html.Div([
        html.Div([
            html.H1("Bigfoot Sightings", className="text-center")
        ], className="row"),
        html.Div([
            html.Div([
                html.P([
                    html.B("Filter the titles:  "),
                    dcc.Input(
                        placeholder="Try 'heard'",
                        id="bigfoot-text-filter",
                        value="")
                ]),
            ], className="col-md-6"),
            html.Div([
                html.P([
                    "Data pulled from ",
                    html.A("bfro.net", href="http://www.bfro.net/"),
                    ". Grab it at ",
                    html.A("data.world", href="https://data.world/timothyrenner/bfro-sightings-data"),
                    "."
                ], style={"text-align": "right"})
            ], className="col-md-6")
        ], className="row"),
    ], className="col-md-12"),
    html.Div([
        html.Div([
            html.Div([
                dcc.Graph(id="bigfoot-map")
            ], className="row")
        ], className="col-md-8"),
        html.Div([
            dcc.Graph(id="bigfoot-dow")
        ], className="col-md-4")
    ], className="row"),
    html.Div([
        html.Div([
            dcc.Graph(id="bigfoot-by-year")
        ], className="col-md-8"),
        html.Div([
            dcc.Graph(id="bigfoot-class")
        ], className="col-md-4")
    ], className="row")
], className="container-fluid")

@app.callback(
    Output('bigfoot-map', 'figure'),
    [
        Input('bigfoot-text-filter', 'value')
    ]
)
def filter_bigfoot_map(filter_text):
    return bigfoot_map(filter_sightings(filter_text))

@app.callback(
    Output('bigfoot-by-year', 'figure'),
    [
        Input('bigfoot-text-filter', 'value')
    ]
)
def filter_bigfoot_by_year(filter_text):
    return bigfoot_by_year(filter_sightings(filter_text))

@app.callback(
    Output('bigfoot-dow', 'figure'),
    [
        Input('bigfoot-text-filter', 'value')
    ]
)
def filter_bigfoot_dow(filter_text):
    return bigfoot_dow(filter_sightings(filter_text))

@app.callback(
    Output('bigfoot-class', 'figure'),
    [
        Input('bigfoot-text-filter', 'value')
    ]
)
def filter_bigfoot_class(filter_text):
    return bigfoot_class(filter_sightings(filter_text))

if __name__ == "__main__":
    app.run_server(debug=True)