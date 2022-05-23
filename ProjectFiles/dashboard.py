from cmath import nan
from enum import auto
from msilib.schema import CheckBox
from tempfile import SpooledTemporaryFile
from tkinter import Checkbutton
from tkinter.tix import CheckList
import dash
from dash import Dash, html, dcc, Output, Input, dash_table
from matplotlib.pyplot import draw
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import utilities as ut
import numpy as np
import os
import re

app = Dash(__name__)

colors = {
    'background': '#b0b4b5',
    'text': '#1c92b0'
}

list_of_subjects = []
subj_numbers = []
number_of_subjects = 0

folder_current = os.path.dirname(__file__) 
print(folder_current)
folder_input_data = os.path.join(folder_current, "input_data")
for file in os.listdir(folder_input_data):
    
    if file.endswith(".csv"):
        number_of_subjects += 1
        file_name = os.path.join(folder_input_data, file)
        print(file_name)
        list_of_subjects.append(ut.Subject(file_name))


df = list_of_subjects[0].subject_data


for i in range(number_of_subjects):
    subj_numbers.append(list_of_subjects[i].subject_id)

data_names = ["SpO2 (%)", "Blood Flow (ml/s)","Temp (C)"]
algorithm_names = ['min','max']
blood_flow_functions = ['CMA','SMA','Show Limits']

fig0= go.Figure()
fig1= go.Figure()
fig2= go.Figure()
fig3= go.Figure()

fig0 = px.line(df, x="Time (s)", y = "SpO2 (%)")
fig1 = px.line(df, x="Time (s)", y = "Blood Flow (ml/s)")
fig2 = px.line(df, x="Time (s)", y = "Temp (C)")
fig3 = px.line(df, x="Time (s)", y = "Blood Flow (ml/s)")

app.layout = html.Div(style={'backgroundColor': colors['background']}, children=[
    html.H1(children='Cardiopulmonary Bypass Dashboard'),

    html.Div(children='''
        Bitte wählen Sie zwischen Ihren Patienten aus. 
        Mit der Aktivierung der 'min' und 'max' werden Ihnen die Extremwerte direkt im Graphen angezeigt...
    '''),


    dcc.Checklist(
    id= 'checklist-algo',
    options=algorithm_names,
    inline=False
    ),

    html.Div([
        dcc.Dropdown(options = subj_numbers, placeholder='Select a subject', value='1', id='subject-dropdown'),
    html.Div(id='dd-output-container')
    ],
        style={"width": "15%"}
    ),

    dcc.Graph(
        id='dash-graph0',
        figure=fig0
    ),

    dcc.Graph(
        id='dash-graph1',
        figure=fig1
    ),
    dcc.Graph(
        id='dash-graph2',
        figure=fig2
    ),

    dcc.Checklist(
        id= 'checklist-bloodflow',
        options=blood_flow_functions,
        inline=False
    ),
    dcc.Graph(
        id='dash-graph3',
        figure=fig3
    ),
    dcc.Textarea(
        id='text-area',
        disabled=True, #disabled --> User cannot interact with textarea
        style={"width": "100%", 'height': 'auto'}
    ),
    dcc.ConfirmDialog(
        id='confirm-oddities',
        message="Oddities! Blood flow was too high or low!"#Message to user
    ),
    dcc.Dropdown(['Oddities'], id='dropdown-oddities'), #Select Oddities
    html.Div(id='output-oddities')
])
### Callback Functions ###
## Graph Update Callback
@app.callback(
    # left: html element, right: element property
    Output('dash-graph0', 'figure'),
    Output('dash-graph1', 'figure'),
    Output('dash-graph2', 'figure'),
    Input('subject-dropdown', 'value'),
    Input('checklist-algo','value')
)
def update_figure(value, algorithm_checkmarks):
    #print("Current Subject: ",value)
    #print("current checked checkmarks are: ", algorithm_checkmarks)
    ts = list_of_subjects[int(value)-1].subject_data
    #SpO2
    fig0 = px.line(ts, x="Time (s)", y = data_names[0])
    # Blood Flow
    fig1 = px.line(ts, x="Time (s)", y = data_names[1])
    # Blood Temperature
    fig2 = px.line(ts, x="Time (s)", y = data_names[2])

    fig0.update_layout(
    plot_bgcolor=colors['background'],
    paper_bgcolor=colors['background'],
    font_color=colors['text']
    )

    fig1.update_layout(
    plot_bgcolor=colors['background'],
    paper_bgcolor=colors['background'],
    font_color=colors['text']
    )

    fig2.update_layout(
    plot_bgcolor=colors['background'],
    paper_bgcolor=colors['background'],
    font_color=colors['text']
    )

    
    #Wenn max oder min angeklickt werden, dann werden Traces mit den jeweiligen Werten eingefügt.
   
    grp = ts.agg(['max', 'min', 'idxmax', 'idxmin'])
    #print(grp)
   
    if algorithm_checkmarks is not None:
        if 'max' in algorithm_checkmarks:
            fig0.add_trace(go.Scatter(x= [grp.loc['idxmax', data_names[0]]], y= [grp.loc['max', data_names[0]]],
                    mode='markers', name='max', marker_color= 'green'))
            fig1.add_trace(go.Scatter(x= [grp.loc['idxmax', data_names[1]]], y= [grp.loc['max', data_names[1]]],
                    mode='markers', name='max', marker_color= 'green'))
            fig2.add_trace(go.Scatter(x= [grp.loc['idxmax', data_names[2]]], y= [grp.loc['max', data_names[2]]],
                    mode='markers', name='max', marker_color= 'green'))
    
        if 'min' in algorithm_checkmarks:
            fig0.add_trace(go.Scatter(x= [grp.loc['idxmin', data_names[0]]], y= [grp.loc['min', data_names[0]]],
                    mode='markers', name='min', marker_color= 'red'))
            fig1.add_trace(go.Scatter(x= [grp.loc['idxmin', data_names[1]]], y= [grp.loc['min', data_names[1]]],
                    mode='markers', name='min', marker_color= 'red'))
            fig2.add_trace(go.Scatter(x= [grp.loc['idxmin', data_names[2]]], y= [grp.loc['min', data_names[2]]],
                    mode='markers', name='min', marker_color= 'red'))
    

    return fig0, fig1, fig2
 

## Blod flow Simple Moving Average Update
@app.callback(
    Output('dash-graph3', 'figure'),
    Output('text-area', 'value'),
    Input('subject-dropdown', 'value'),
    Input('checklist-bloodflow','value'),
)

def bloodflow_figure(value, bloodflow_checkmarks):
    
    ## Calculate Moving Average: Aufgabe 2
    print(bloodflow_checkmarks)
    bf = list_of_subjects[int(value)-1].subject_data
    fig3 = px.line(bf, x="Time (s)", y="Blood Flow (ml/s)")

    ## Calculate Simple Moving Average: Aufagbe 2
    if bloodflow_checkmarks is not None: #behebt Fehler: Nonetype object not iterable
        if bloodflow_checkmarks == ["SMA"]:
            bf["Blood Flow (ml/s) - SMA"] = ut.calculate_SMA(bf["Blood Flow (ml/s)"],4) 
            fig3 = px.line(bf, x="Time (s)", y="Blood Flow (ml/s) - SMA")

        if bloodflow_checkmarks == ["CMA"]:

            bf["Blood Flow (ml/s) - CMA"] = ut.calculate_CMA(bf["Blood Flow (ml/s)"],2) 
            fig3 = px.line(bf, x="Time (s)", y="Blood Flow (ml/s) - CMA")

    #Durchschnitt
    avg = bf.mean()
    x = [0, 480]
    y = avg.loc['Blood Flow (ml/s)']
    bf["Blood Flow (ml/s) - SMA"] = ut.calculate_SMA(bf[data_names[1]],4) 
    bf_SMA =  bf["Blood Flow (ml/s) - SMA"]

    fig3.add_trace(go.Scatter(x = x, y= [y,y], mode = 'lines', name = 'Mittelwert'))

    #Intervalle
    y_oben = (avg.loc['Blood Flow (ml/s)'])*1.15
    y_unten = (avg.loc['Blood Flow (ml/s)'])*0.85
    

    def show_limits(fig):

        fig.add_trace(go.Scatter(x = x, y = [y_oben, y_oben], mode = 'lines', name = 'Upper Limit', line_color='blue')) #adding trace of upper limit to fig3
        fig.add_trace(go.Scatter(x = x, y = [y_unten, y_unten], mode = 'lines', name = 'Lower Limit', line_color='blue')) #adding trace of lower limit to fig3
    

        return fig

    ## Update fig3 via checkboxes
    if bloodflow_checkmarks is not None:

        if 'CMA' in bloodflow_checkmarks and 'SMA' not in bloodflow_checkmarks: #only if CMA is checked
            
            bf["Blood Flow (ml/s) - CMA"] = ut.calculate_CMA(bf[data_names[1]],2)
            fig_CMA = px.line(bf, x="Time (s)", y="Blood Flow (ml/s) - CMA") #update fig3 to show Cumulative moving Average

            if 'Show Limits' in bloodflow_checkmarks: #Check if Limits is checked
                fig3 = show_limits(fig_CMA) #call show_limits to add traces to current figure
            
            fig3 = fig_CMA #save edited figure with or without traces to fig3


        if 'SMA' in bloodflow_checkmarks and 'CMA' not in bloodflow_checkmarks: #only if SMA is checked

            fig_SMA = px.line(bf, x="Time (s)", y=bf_SMA) #save plot of edited figure

            if 'Show Limits' in bloodflow_checkmarks:
                fig3 = show_limits(fig_SMA) #call show_limits to add traces to current figure
            
            fig3 = fig_SMA #save edited figure with or without traces to fig3


        if bloodflow_checkmarks == ['Show Limits']: #check if Show Limits is the only checked box

            fig3 = show_limits(fig3) #save figure with added limit traces
    
    fig3.update_layout(
        plot_bgcolor=colors['background'],
        paper_bgcolor=colors['background'],
        font_color=colors['text']
    )   
    
        ## Aufgabe 3.3
    alert_count = [] # 
    alert_sum = 0 #int, holds count of invalid values

    for i in bf_SMA:
        if i > y_oben or i < y_unten: # Value of SMA over oder under limit
            alert_count.append(bf.index[bf_SMA==i].tolist()) # append list of invalid values to list
            alert_sum += 1 #for each invalid value, alert_sum is going up by 1

    #print('Alert count: ' + str(alert_count))
    #print(str(alert_sum))

    # message
    info_msg = 'Blood flow was not between intervals for' + str(alert_sum) + ' seconds!'

    
    return fig3, info_msg

@app.callback(
Output('confirm-oddities', 'displayed'),
Input('dropdown-oddities', 'value'))
def display_confirm(value):
    if value == 'Oddities': #If Oddities selected
        return True
    return False
# dcc.ConfirmDialogProvider for an easier way to display an alert when clicking on an item.

if __name__ == '__main__':
    app.run_server(debug=True)