# -*- coding: utf-8 -*-
"""
Run-out calculator

Author : Jiwoo Ahn

16/07/2022

"""
import math
import numpy as np

import dash
from dash import dcc, html
from dash.dependencies import Input, Output , State
import dash_bootstrap_components as dbc

from shapely.ops import split, linemerge
from shapely.geometry import LineString, Polygon, Point

import plotly.graph_objects as go
import plotly.io as pio
pio.renderers.default='browser'

# Colors
bmao = '#f7923a'
bmar = '#ee3b34'
bmab = '#004890'
bkgr = '#f8f5f0'

# Text area delimiter
def textarea_to_list(textarea_string):
    list0 = textarea_string.replace('\t',',').replace('\n',',').split(',')
    list0_float = [round(float(x),1) for x in list0]
    spx = list0_float[::2]
    spy = list0_float[1::2]
    return spx, spy

# Returns index of point on slope profile that is closest to the defined point
def minimum_distance(x0, y0, xl, yl):
    dis = [((x0-x)**2+(y0-y)**2)**0.5 for x, y in zip(xl, yl)]
    return dis.index(min(dis))
    
def header_colors():
    return {
        'bg_color': '#0C4142',
        'font_color': 'white',
    }

# Converts two lists into tuple pairs
def merge(list1, list2):
    merged_list = tuple(zip(list1, list2)) 
    return merged_list

# Convert shapely polygon into 2D numpy array for plotting purposes
def polygon_to_patch(polygon):
    x, y = polygon.exterior.xy
    xn, yn = np.array(x), np.array(y)
    return xn, yn

# Main function
def plot_runout(standoff, swell_factor, bund_height, runout_angle, spxy, fsxy, direction, project):
    
    # Initiate plotly figure
    fig = go.Figure()
    fig.update_layout(template='simple_white', paper_bgcolor=bkgr)
    
    # Round all co-ordinates to 1 decimal place for simplification
    try:
        sp_x, sp_y = textarea_to_list(spxy)
        # Plot Slope profile
        fig.add_trace(go.Scatter(x=sp_x, y=sp_y, name = 'Slope', mode='lines', line=dict(color='black'), opacity=1.0, marker_size=0))
        
        # Calculated Parameters
        bund_width = 2*bund_height/math.tan(math.radians(37))
        
        # bund co-ordinates
        if direction == 'left':
            b_x = [-standoff+sp_x[0]]
        else:
            b_x = [standoff+sp_x[0]]
        b_y = [sp_y[0]]
        
        # Start of run-out
        if bund_height > 0:
            if direction == 'left':
                b_x.extend([b_x[0]+0.5*bund_width,
                       b_x[0]+1.0*bund_width])
            else:
                b_x.extend([b_x[0]-0.5*bund_width,
                       b_x[0]-1.0*bund_width])
                
            b_y.extend([b_y[0]+bund_height, b_y[0]])
            
            bt_x, bt_y = b_x[1], b_y[1]
    
        else:
            bt_x, bt_y = b_x[0], b_y[0]
        
    except:
        print('No slope profile entered')
        
    try:
        fs_x, fs_y = textarea_to_list(fsxy)
        # Plot Failure surface
        fig.add_trace(go.Scatter(x=fs_x, y=fs_y, name = 'Failure', mode='lines', line=dict(color='red'), opacity=1.0, marker_size=0))
    except:
        print('No failure surface entered')

    # Plot bund if bund height is greater than 0
    if bund_height > 0:
        fig.add_trace(go.Scatter(x=b_x, y=b_y, name = "Bund", mode='lines', line=dict(color=bmao), opacity=0.2, marker_size=0, fillcolor=bmao, fill='toself', hoverinfo='skip'))
        titletext = "{0:.1f}m Bund at {1:.0f}m Standoff".format(bund_height, standoff)
    else:
        titletext = "Unbunded {0:.0f}m Standoff".format(standoff)
            
    
    # FAILURE VOLUME calculations
    try:
        # Intersection point 1
        i_start = minimum_distance(fs_x[0], fs_y[0], sp_x, sp_y)
        ix1, iy1 = sp_x[i_start], sp_y[i_start]
        fs_x[0], fs_y[0] = ix1, iy1
        i1 = Point(ix1, iy1)
        
        # Interseciton point 2
        i_end = minimum_distance(fs_x[-1], fs_y[-1], sp_x, sp_y)
        ix2, iy2 = sp_x[i_end], sp_y[i_end]
        fs_x[-1], fs_y[-1] = ix2, iy2
        i2 = Point(ix2, iy2)
        
        # Failure surface as LineString
        fs_ls = LineString(merge(fs_x, fs_y))
        
        # Slope profile as line string
        sp_ls = LineString(merge(sp_x, sp_y))
        
        # Line strings to combine
        linestrings = []
        
        # Check if first point of failure surface co-incides with first point of slope profile
        bool1 = (ix1 == sp_x[0] and iy1 == sp_y[0]) 
        bool2 = (ix2 == sp_x[-1] and iy2 == sp_y[-1])
        if bool1 and bool2: 
            sp_lsf = sp_ls
            linestrings = [fs_ls]
        elif bool1:
            sp_lsf, sp_lsc = split(sp_ls, i2)
            linestrings = [fs_ls, sp_lsc]
        elif bool2:
            sp_lsc, sp_lsf = split(sp_ls, i1)
            linestrings = [sp_lsc, fs_ls]
        else:
            sp_ls1, sp_ls2 = split(sp_ls, i1)
            sp_lsf, sp_ls3 = split(sp_ls2, i2)
            linestrings = [sp_ls1, fs_ls, sp_ls3]
        
        # Linestring with slope profile and failure surface combined
        if project == 'yes':
            line_combined = LineString(linemerge(linestrings))
        else:
            line_combined = LineString(merge(sp_x, sp_y))
            
        # Add failed volume to plotly figure
        failure_volume = Polygon(linemerge([sp_lsf, fs_ls]))
        fv_x_p, fv_y_p = polygon_to_patch(failure_volume)
        fig.add_trace(go.Scatter(x=fv_x_p, y=fv_y_p, name = "Failure volume = {0:.1f} m³/m".format(failure_volume.area*swell_factor), mode='lines', line=dict(color=bmar), opacity=0.2, marker_size=0, fillcolor=bmar, fill='toself', hoverinfo='skip'))
    
    except:
        print('Intersection error')
        # Create slope profile as shapely linestring, as combined surface with failure surface didn't work out
        line_combined = LineString(merge(sp_x, sp_y))

    # CATCH CAPACITY calculations
    try:
        #  Find intersection point between run-out line and combined surface
        runout_length = 1000
        if direction == 'right': runout_angle = 180-runout_angle
        ro_x = [bt_x, bt_x+runout_length*math.cos(math.radians(runout_angle))]
        ro_y = [bt_y, bt_y+runout_length*math.sin(math.radians(runout_angle))]
        line_runout = LineString(merge(ro_x, ro_y))
        
        # line_combined will be just the slope profile if FAILURE VOLUME calculations run successfully
        intersect = line_runout.intersection(line_combined)
        
        # Try except to filter out cases where runout line encountered more than one intersection point
        try:
            intersect = intersect[0]
        except:
            intersect = intersect    
        ix, iy = intersect.x, intersect.y
        
        # Calculate catch capacity
        line_profile = split(line_combined,line_runout)[0]
        if bund_height > 0:
            line_profile2 = LineString([(b_x[2], b_y[2]), (bt_x, bt_y), (ix, iy)])
        else:
            line_profile2 = LineString([(bt_x, bt_y), (ix, iy)])
        catch_capacity = Polygon(linemerge([line_profile, line_profile2]))
        cc_x, cc_y = polygon_to_patch(catch_capacity)
        fig.add_trace(go.Scatter(x=cc_x, y=cc_y, name = "Catch capacity = {0:.1f} m³/m".format(catch_capacity.area), mode='lines', line=dict(color=bmab), opacity=0.2, marker_size=0, fillcolor=bmab, fill='toself', hoverinfo='skip'))
        
    except:
        print('Catch capacity error')
    
    # # plot extents
    # fig.update_yaxes(range=[min(sp_y), max(sp_y)], fixedrange=True)
    # fig.update_xaxes(range=[min(b_x), max(sp_x)])

    fig.update_xaxes(scaleanchor = "y", scaleratio = 1)
    fig.update_layout(font={'size':16})
    
    fig.update_layout(
    title=dict(text=titletext,x=0.5,y=0.95,
               font=dict(family="Arial",size=20,color='#000000')
               )
    )
    
    fig.update_layout(margin=dict(l=20, r=20, t=60, b=20))
    
    return fig

# Initiate the app
external_stylesheets = [dbc.themes.SANDSTONE]
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server
app.title = 'Runout Calculator'

# App HTML layout
styledict = {'display':'inline-block','vertical-align':'left', 'margin-top':'10px','margin-left':'20px','font-size':10,'font-family':'Verdana','textAlign':'center'}

htmlcent = {'text-align':'center'}

# Dropdown and input fields, saved as variables
standoff = dcc.Input(id='standoff-state', type='number', value=18, min=5, max=50, step=1, style={'height' : '20px', 'width': '50px', 'display':'inline-block', 'margin-left':'5px','vertical-align':'middle'})

swellfactor = dcc.Input(id='swellfactor-state', type='number', value=1.3, min=0.8, max=2, step=0.05, style={'height' : '20px', 'width': '50px', 'display':'inline-block', 'margin-left':'5px','vertical-align':'left', 'textAlign' : 'center'})

bundheight = dcc.Input(id='bundheight-state', type='number', value=2, min=0, max=5, step=0.1, style={'height' : '20px', 'width': '50px', 'display':'inline-block', 'margin-left':'5px','vertical-align':'middle'})

runoutangle = dcc.Input(id='runoutangle-state', type='number', value=37, min=1, max=89, style={'height' : '20px', 'width': '50px', 'display':'inline-block', 'margin-left':'5px','vertical-align':'left', 'textAlign':'center',})

directions = ['left', 'right']
direction = dbc.RadioItems(
                id="direction-state",
                options=[{"label": x, "value": x} for x in directions],
                value="left",
                inline=True
            )

project = dbc.Checklist(
    id="project-state",
    options=[{"label": "Project to backscarp", "value": "yes"}],
    value=["yes"],
    switch=True,
    inline=True
    
)

spxy = dcc.Textarea(
        id='spxy-state',
        value = "0.0	0.0\n3.5	5.2\n6.4	11.6\n7.1	16.5\n9.0	21.6\n12.4	27.7\n16.5	32.3\n22.1	35.6\n28.8	36.0",
        style={'width': '90%', 'height': 293, 'resize' : 'none'})

fsxy = dcc.Textarea(
        id='fsxy-state',
        value = "6.4	11.6\n14.3	17.7\n18.6	22.9\n22.1	35.6",
        style={'width': '90%', 'height': 293, 'resize' :  'none'})

# Header
header = dbc.Navbar(
    dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(
                        html.Img(
                            id="logo",
                            src="https://raw.githubusercontent.com/j-ahn/misc/main/favicon.png",
                            height="65px",
                        ),
                        md="auto",
                    ),
                    dbc.Col(
                        [
                            html.Div(
                                [
                                    html.H3([
                                        html.Span("Slope ", style={'color':bmao}),
                                        html.Span("Runout ", style={'color':bmar}),
                                        html.Span("Calculator ", style={'color':bmab})
                                        ]),
                                    html.P("Jiwoo Ahn"),
                                ],
                                id="app-title"
                            )
                        ],
                        md=True,
                        align="center",
                    ),
                ],
                align="center",
            ),
        ],
        fluid=True,
    ),
    dark=False,
    sticky="top",
)

inputscard = dbc.Card(color='light',children=[
                          dbc.CardHeader("Inputs", style={'font-weight':'bold'}),
                          dbc.CardBody([html.Div([
                              
                              html.Div(html.H6("Geometry", style={'font-style':'italic', 'text-align':'center'})),
                                  dbc.Row([
                                      dbc.Col(html.Div([html.P("Slope (x,y)"),spxy]), style=htmlcent),
                                      dbc.Col(html.Div([html.P("Failure (x,y)"),fsxy], style=htmlcent))
                                      ])
                                  ]),
                          
                              html.Hr(),
                          
                              html.Div([
                                  html.Div(html.H6("Parameters", style={'font-style':'italic', 'text-align':'center'})),
                                  html.Div([html.Label(["Standoff (m):",standoff])], style=htmlcent),
                                  html.Div([html.Label(["Swell factor:",swellfactor])], style=htmlcent),
                                  html.Div([html.Label(["Bund height (m):",bundheight])], style=htmlcent),
                                  html.Div([html.Label(["Runout Angle (°):",runoutangle])], style=htmlcent),
                                  html.Div([html.Label(["Slope direction:"])], style=htmlcent),
                                  html.Div([direction], style=htmlcent),
                                  html.Div([html.Label([project])], style=htmlcent),
                                  html.Div([dbc.Button('Update Graph', id='update_button', n_clicks=0, color="primary", style={"margin": "5px"})], style=htmlcent)
                                  ])
                              ])
                          ])
                  
runoutgraph = dbc.Card(color='light',children=[dbc.CardHeader("Output", style={'font-weight':'bold'}),
                        dcc.Graph('dashboard',style={'height': '72vh'},
                                  config={'displayModeBar': True, 
                                          'displaylogo':False,
                                          'toImageButtonOptions': {'format': 'svg','filename': 'runout_calculator'},
                                          'modeBarButtonsToRemove':['hoverClosestPie']})])

markdowncard = html.Div(dcc.Markdown("Enter slope and failure co-ordinates from bottom to top (1 decimal place) as tab delimited strings (recommend copy and pasting out of excel). Start and finish points of failure surface must co-incide with points on the slope profile (app will snap to nearest node)."), style = {'font-size':12,'font-family':'Verdana','textAlign':'center'})

app.layout = dbc.Container(
    [
        header,
        
        html.Hr(),
        
        dbc.Row([
            dbc.Col(inputscard, md=3),
            
            dbc.Col(runoutgraph, md=9)
        ]),
        
        html.Hr(),
        
        markdowncard
    ],
    fluid=True
)


@app.callback(
    Output('dashboard', 'figure'),
    Input('update_button', 'n_clicks'),
    State('standoff-state', 'value'),
    State('swellfactor-state', 'value'),
    State('bundheight-state', 'value'),
    State('runoutangle-state', 'value'),
    State('spxy-state', 'value'),
    State('fsxy-state', 'value'),
    State('direction-state','value'),
    State('project-state','value')
)

def update_graph(n_clicks, standoff, swellfactor, bundheight, runoutangle, spxy, fsxy, direction, project):
    if n_clicks >= 0:
        if project:
            prj = 'yes'
        else:
            prj= 'no'
        fig = plot_runout(standoff, swellfactor, bundheight, runoutangle, spxy, fsxy, direction, prj)
    return fig

if __name__ == '__main__':
    app.run_server()
