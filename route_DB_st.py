import pandas as pd
import numpy as np
import gpxpy
import gpxpy.gpx
import matplotlib.pyplot as plt
import folium
from IPython.display import display
import plotly.express as px
import haversine as hs
import plotly.graph_objects as go
import tqdm
import math
import os
import requests
import datetime as datetime
import streamlit as st
from stqdm import stqdm
from streamlit_folium import st_folium


st.set_page_config(
    page_title="Route_DB",
    page_icon="🧊",
    layout="wide",)

def elevationprof(date):
    gpx = gpx_loader(date)
    route_df = attribute_calc(gpx)
# Create figure
    fig_elev_s = go.Figure()

    fig_elev_s.add_trace(
        go.Scatter(x=list(route_df.cum_distance), y=list(route_df.elevation),text=route_df.gradient,
                        hoverinfo="text",
                        line_shape='spline'))

    # Set title
    fig_elev_s.update_layout(
        title_text="Elevation profile"
    )

    # Add range slider
    fig_elev_s.update_layout(
        xaxis=dict(
            title = 'Distance in km', 
            rangeselector=dict(
                buttons=list([
                    dict(step="all")
                ])
            ),
            rangeslider=dict(
                visible=True
            ),
            type="linear"
        ),
        yaxis = dict(
            title = "Elevation"
        )
    )

    return(fig_elev_s)
    
def haversine_distance(lat1, lon1, lat2, lon2) -> float:
    distance = hs.haversine(
        point1=(lat1, lon1),
        point2=(lat2, lon2),
        unit=hs.Unit.METERS
    )
    return np.round(distance, 2)

def attribute_calc(gpx):
    route_info = []

    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                route_info.append({
                    'latitude': point.latitude,
                    'longitude': point.longitude,
                    'elevation': point.elevation
                })
    route_df = pd.DataFrame(route_info)
    
    
    haversine_distance(
        lat1=route_df.iloc[0]['latitude'],
        lon1=route_df.iloc[0]['longitude'],
        lat2=route_df.iloc[1]['latitude'],
        lon2=route_df.iloc[1]['longitude']
    )    
    print(route_df.shape)
    distances = [np.nan]
    for i in range(0,route_df.shape[0]):
        if i == 0:
            continue
        else:
            distances.append(haversine_distance(
                lat1=route_df.iloc[i - 1]['latitude'],
                lon1=route_df.iloc[i - 1]['longitude'],
                lat2=route_df.iloc[i]['latitude'],
                lon2=route_df.iloc[i]['longitude']
            ))
            
    route_df['distance'] = distances
    
    route_df['elevation_diff'] = route_df['elevation'].diff()

    route_df[route_df['elevation_diff'] >= 0]['elevation_diff'].sum()
    route_df['distance'].sum()
    route_df['cum_elevation'] = route_df['elevation_diff'].cumsum()
    route_df['cum_distance'] = route_df['distance'].cumsum()
    
    gradients = [np.nan]

    for ind, row in route_df.iterrows(): 
        if ind == 0:
            continue
            
        grade = (row['elevation_diff'] / row['distance']) * 100
        
        if grade > 30:
            gradients.append(np.nan)
        else:
            gradients.append(np.round(grade, 1))
            
    route_df['gradient'] = gradients
    
    route_df = route_df.fillna(0)
    
    
    return(route_df)

def map_show(date):
    gpx = gpx_loader(date)
    route_df = attribute_calc(gpx)

    lat_center = route_df.iloc[0][0]
    lon_center = route_df.iloc[0][1]
    route_map = folium.Map(
        location=[lat_center, lon_center],
        zoom_start=11,
        tiles='OpenStreetMap',
        
    )

    coordinates = [tuple(x) for x in route_df[['latitude', 'longitude']].to_numpy()]
    folium.PolyLine(coordinates, weight=4).add_to(route_map)

    return(route_map)

def gpx_loader(date):
    #nice date
    format_data = "%d.%m.20%y"
    nice_date = date.strftime(format_data)
    
    #download gpx
   
    url = fr"https://raw.githubusercontent.com/MannuelTe/weekdayDB/files/{nice_date}.gpx" # Make sure the url is the raw version of the file on GitHub
    download = requests.get(url).content.decode("UTF-8")
    #parse gpx
    gpx  = gpxpy.parse(download)
    return(gpx)




st.title("All gathered Weekday rides")
st.subheader("In List form")

col_1, col_2, col1, col2, = st.columns(4)

with col_1: 
    len = st.slider(
        'Length of the route',
        30.0, 100.0, (30.0, 100.0))
    
with col1: 
    elev = st.slider(
        'Select a range of values',
        0.0, 2000.0, (0.0, 2000.0))
    

routes_sans = pd.read_csv(r"https://raw.githubusercontent.com/MannuelTe/weekdayDB/main/routes_DB.csv" ,index_col=0, encoding = 'unicode_escape')
routes_sans = routes_sans.reset_index()
routes_sans["Date"] = pd.to_datetime(routes_sans["Date"]).dt.date

desc = pd.read_csv(r"https://raw.githubusercontent.com/MannuelTe/weekdayDB/main/routes_DB_only_Desc.csv", index_col=0, encoding = 'unicode_escape')
desc = desc.reset_index().drop(columns = ["Column1"])
desc["Date"] = pd.to_datetime(desc["Date"], dayfirst= True).dt.date

routes = pd.merge(routes_sans, desc, "left", on="Date")
routes = routes[(routes["Elevation Gain"] > elev[0]) & (routes["Elevation Gain"] < elev[1])]
routes = routes[(routes["Length"] > len[0]) & (routes["Length"] < len[1])]

with col_2:
    st.metric("Average lenght",str(routes.Length.mean().round(2))+ " km")
with col2:
    st.metric("Average elevation gain", str(routes["Elevation Gain"].mean().round(2))+ " m")

st.dataframe(routes, use_container_width= True)

    

##add visual of the route
st.subheader("Visually depicted")
st.write("A general overview over the stored routes")
fig_general = px.scatter(routes, x="Length", y="Elevation Gain", hover_data=['Date', "Start"],color= "Start" )
st.plotly_chart(fig_general, use_container_width = True)

with st.expander("Analyzed by Start Point"):
    selected_start = st.radio("Select a starting point", ["Frohburg", "Triemli", "Fork"])
    routes_sp = routes[routes["Start"]== selected_start]
    st.write("Analysis of the length and elevation gain of the routes starting at " + selected_start + ".")
    fig_scat = px.scatter(routes_sp, x="Length", y="Elevation Gain", hover_data=['Date'],color= "Heading" , )
    st.plotly_chart(fig_scat,  use_container_width= True)
with st.expander("Histograms"):
    tab_l, tab_e, tab_s, tab_h= st.tabs(["Length", "Elevation", "Startpoint", "Heading"])
    with tab_l:
        st.write("Distribution of the length per route")
        fig_hist_len = px.histogram(routes, x = "Length", color="Start")
        st.plotly_chart(fig_hist_len, use_container_width= True)
    with tab_e:
        st.write("Distribution of the elevation gain per route")
        fig_hist_el = px.histogram(routes, x = "Elevation Gain", color="Start")
        st.plotly_chart(fig_hist_el,  use_container_width= True)
    with tab_s:
        st.write("Distribution of the start points of the routes")
        fig_hist_s = px.histogram(routes, x = "Start", )
        st.plotly_chart(fig_hist_s,  use_container_width= True)
    with tab_h:
        st.write("Distribution of the headings of the routes")
        fig_hist_h = px.histogram(routes, x = "Heading", color= "Start")
        st.plotly_chart(fig_hist_h,  use_container_width= True)

st.subheader("View select routes")
with st.form("routeviewer"):
    Date_of_ride = st.date_input(   "What day was the ride?",    datetime.date(2022, 7, 17))
    format_data = "%d.%m.20%y"
    nice_date = Date_of_ride.strftime(format_data)
    ride_map = st.form_submit_button("Show ride")
    if ride_map:
        st.write('Displaying the route of the ', nice_date)
        try:
            st.dataframe(routes[routes["Date"]== Date_of_ride],  use_container_width= True)
            st_folium(map_show(Date_of_ride), width = 1400)
            st.plotly_chart(elevationprof(Date_of_ride),  use_container_width= True)
            st.info("Access the gpx file under:   \n" +  fr"https://raw.githubusercontent.com/MannuelTe/weekdayDB/files/{nice_date}.gpx" )
        except:
    ###add context to why not working 
    
    #download gpx
   
            url = fr"https://raw.githubusercontent.com/MannuelTe/weekdayDB/files/{nice_date}.gpx" 
    
            if requests.head(url).status_code== 404:
                st.warning("No ride on the seleced date :-( ")
            else:
                st.warning("There was an error loading the ride file")
        
