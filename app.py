import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
from flask_caching import Cache

from csv import DictReader
from toolz import compose, pluck, groupby, valmap, first, unique, get, countby
import datetime as dt
from dotenv import find_dotenv,load_dotenv

import os

load_dotenv(find_dotenv())

################################################################################
# HELPERS
################################################################################
listpluck = compose(list, pluck)
listfilter = compose(list, filter)
listmap = compose(list, map)
listunique = compose(list, unique)

TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

# Datetime helpers.
def sighting_year(sighting):
    return dt.datetime.strptime(sighting['timestamp'], TIMESTAMP_FORMAT).year

def sighting_dow(sighting):
    return dt.datetime.strptime(sighting['timestamp'], TIMESTAMP_FORMAT)\
                      .strftime("%a")

################################################################################
# PLOTS
################################################################################
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

################################################################################
# APP INITIALIZATION
################################################################################
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
# Don't understand this one bit, but apparently it's needed.
server.secret_key = os.environ.get("SECRET_KEY", "secret")

app.title = "Bigfoot Sightings"
cache = Cache(app.server, config={"CACHE_TYPE": "simple"})


# This function can be memoized because it's called for each graph, so it will
# only get called once per filter text.
@cache.memoize(10)
def filter_sightings(filter_text):
    return listfilter(
            lambda x: filter_text.lower() in x['title'].lower(),
            BFRO_LOCATION_DATA
        )

################################################################################
# LAYOUT
################################################################################
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
    # Row: Title
    html.Div([
        # Column: Title
        html.Div([
            html.H1("Bigfoot Sightings", className="text-center")
        ], className="col-md-12")
    ], className="row"),
    # Row: Filter + References
    html.Div([
        # Column: Filter
        html.Div([
            html.P([
                html.B("Filter the titles:  "),
                dcc.Input(
                    placeholder="Try 'heard'",
                    id="bigfoot-text-filter",
                    value="")
            ]),
        ], className="col-md-6"),
        # Column: References.
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
    # Row: Map + Bar Chart
    html.Div([
        # Column: Map
        html.Div([
            dcc.Graph(id="bigfoot-map")
        ], className="col-md-8"),
        # Column: Bar Chart
        html.Div([
            dcc.Graph(id="bigfoot-dow")
        ], className="col-md-4")
    ], className="row"),
    # Row: Line Chart + Donut Chart
    html.Div([
        # Column: Line Chart
        html.Div([
            dcc.Graph(id="bigfoot-by-year")
        ], className="col-md-8"),
        # Column: Donut Chart
        html.Div([
            dcc.Graph(id="bigfoot-class")
        ], className="col-md-4")
    ], className="row"),
    # Row: Footer
    html.Div([
        html.Hr(),
        html.P([
            "Built with ",
            html.A("Dash", href="https://plot.ly/products/dash/"),
            ". Check out the code on ",
            html.A("GitHub", href="https://github.com/timothyrenner/bigfoot-dash-app"),
            "."
        ])      
    ], className="row",
        style={
            "textAlign": "center",
            "color": "Gray"
        })
], className="container-fluid")

################################################################################
# INTERACTION CALLBACKS
################################################################################
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