#!/usr/bin/env python3
"""
EdgeRIC Web Dashboard - Real-time metrics visualization using Plotly Dash
This provides a proper web-based interface with native sliding window support
"""

import os
# Fix protobuf compatibility issue
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'

import dash
from dash import dcc, html, Input, Output, callback
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import zmq
import time
import threading
import json
from collections import deque, defaultdict
import signal
import sys
from datetime import datetime, timedelta

# Add the edgeric directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'edgeric'))

try:
    import metrics_pb2
    print("✓ Successfully imported metrics_pb2")
except ImportError as e:
    print(f"✗ Failed to import metrics_pb2: {e}")
    print("Make sure you're running this from the EdgeRIC root directory")
    sys.exit(1)

class EdgeRICWebDashboard:
    def __init__(self, tcp_host="localhost", tcp_port=5555, max_points=5000):
        self.tcp_host = tcp_host
        self.tcp_port = tcp_port
        self.max_points = max_points  # number of points to show in rolling window
        self.context = zmq.Context()
        self.subscriber = None
        self.running = False
        
        # Data storage - using sequence-based approach
        self.ue_data = defaultdict(lambda: {
            'timestamps': deque(maxlen=self.max_points),
            'latency': deque(maxlen=self.max_points),
            'backlog': deque(maxlen=self.max_points),
            'throughput': deque(maxlen=self.max_points),
            'cqi': deque(maxlen=self.max_points),
            'snr': deque(maxlen=self.max_points)
        })
        
        # Statistics
        self.message_count = 0
        self.last_update = time.time()
        self.connection_status = "Disconnected"
        
        # Threading
        self.data_thread = None
        self.data_lock = threading.Lock()
        
        # Initialize Dash app
        self.app = dash.Dash(__name__, external_stylesheets=[
            'https://codepen.io/chriddyp/pen/bWLwgP.css'
        ])
        
        self.setup_layout()
        self.setup_callbacks()
        
    def setup_layout(self):
        """Setup the web dashboard layout"""
        self.app.layout = html.Div([
            html.H1("EdgeRIC Real-Time Metrics Dashboard", 
                   style={'textAlign': 'center', 'marginBottom': 30}),
            
            # Status bar
            html.Div([
                html.Div(id='status-indicator', style={'display': 'inline-block', 'marginRight': 20}),
                html.Div(id='message-count', style={'display': 'inline-block', 'marginRight': 20}),
            ], style={'textAlign': 'center', 'marginBottom': 20, 'padding': 10, 'backgroundColor': '#f0f0f0'}),
            
            # Graphs in a 2x3 grid
            html.Div([
                html.Div([
                    dcc.Graph(id='latency-graph', style={'height': '300px'})
                ], className='four columns'),
                
                html.Div([
                    dcc.Graph(id='backlog-graph', style={'height': '300px'})
                ], className='four columns'),
                
                html.Div([
                    dcc.Graph(id='throughput-graph', style={'height': '300px'})
                ], className='four columns'),
            ], className='row'),
            
            html.Div([
                html.Div([
                    dcc.Graph(id='cqi-graph', style={'height': '300px'})
                ], className='four columns'),
                
                html.Div([
                    dcc.Graph(id='snr-graph', style={'height': '300px'})
                ], className='four columns'),
                
                html.Div([
                    # Legend and controls
                    html.Div(id='legend-area', style={'height': '300px', 'padding': 20})
                ], className='four columns'),
            ], className='row'),
            
            # Auto-refresh interval
            dcc.Interval(
                id='interval-component',
                interval=1000,  # Update every second
                n_intervals=0
            ),
            
            # Store for data
            dcc.Store(id='data-store')
        ])
    
    def setup_callbacks(self):
        """Setup Dash callbacks for interactivity"""
        
        @self.app.callback(
            [Output('latency-graph', 'figure'),
             Output('backlog-graph', 'figure'),
             Output('throughput-graph', 'figure'),
             Output('cqi-graph', 'figure'),
             Output('snr-graph', 'figure'),
             Output('status-indicator', 'children'),
             Output('message-count', 'children'),
             Output('legend-area', 'children')],
            [Input('interval-component', 'n_intervals')]
        )
        def update_graphs(n_intervals):
            return self.create_all_graphs(self.max_points)
    
    def create_all_graphs(self, max_points=None):
        """Create all graphs with current data using sequence-based plotting"""
        if max_points is None:
            max_points = self.max_points
        with self.data_lock:
            # Status indicators
            status_color = "green" if self.connection_status == "Connected" else "red"
            status_div = html.Div([
                html.Span("●", style={'color': status_color, 'fontSize': '20px', 'marginRight': '5px'}),
                html.Span(f"Status: {self.connection_status}")
            ])
            
            message_div = html.Div(f"Messages: {self.message_count}")
            
            # Create graphs with sequence-based x-axis
            latency_fig = self.create_metric_graph('latency', 'Latency (μs)', max_points)
            backlog_fig = self.create_metric_graph('backlog', 'Backlog (bytes)', max_points)
            throughput_fig = self.create_metric_graph('throughput', 'TX Bytes', max_points)
            cqi_fig = self.create_metric_graph('cqi', 'CQI', max_points)
            snr_fig = self.create_metric_graph('snr', 'SNR (dB)', max_points)
            
            # Legend
            legend_content = self.create_legend()
            
            return (latency_fig, backlog_fig, throughput_fig, cqi_fig, snr_fig,
                   status_div, message_div, legend_content)
    
    def create_metric_graph(self, metric, y_label, max_points):
        """Create a graph for a specific metric with sequence-based x-axis"""
        fig = go.Figure()
        
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9']
        color_idx = 0
        
        max_data_points = 0
        for rnti in sorted(self.ue_data.keys()):
            ue_data = self.ue_data[rnti]
            values = list(ue_data[metric])
            max_data_points = max(max_data_points, len(values))
            
        for rnti in sorted(self.ue_data.keys()):
            ue_data = self.ue_data[rnti]
            values = list(ue_data[metric])
            
            if not values:
                continue
                
            # Apply running average for all metrics except latency
            if metric != 'latency':
                values = self.calculate_running_average(values, 50)
                
            # Create x-axis as sample indices (1, 2, 3, ...)
            x_vals = list(range(1, len(values) + 1))
            
            color = colors[color_idx % len(colors)]
            fig.add_trace(go.Scatter(
                x=x_vals,
                y=values,
                mode='lines+markers',
                name=f'UE {rnti}',
                line=dict(color=color, width=2),
                marker=dict(size=4)
            ))
            color_idx += 1
        
        # Configure layout for sequence-based plotting
        x_max = max(max_data_points, 10) if max_data_points > 0 else max_points
        fig.update_layout(
            title=f'UE {y_label}',
            xaxis_title='Sample Index',
            yaxis_title=y_label,
            xaxis=dict(
                range=[1, x_max],
                type='linear'
            ),
            showlegend=True,
            legend=dict(x=1.02, y=1),
            margin=dict(l=50, r=50, t=50, b=50),
            height=300
        )
        
        return fig
    
    def create_legend(self):
        """Create legend/info area"""
        legend_items = []
        
        # Just show a simple status
        legend_items.append(html.P("Dashboard Status: Active"))
        
        return html.Div(legend_items)
    
    def connect_to_bridge(self):
        """Connect to the TCP bridge"""
        try:
            self.subscriber = self.context.socket(zmq.SUB)
            self.subscriber.setsockopt_string(zmq.SUBSCRIBE, "")
            self.subscriber.setsockopt(zmq.CONFLATE, 1)
            self.subscriber.setsockopt(zmq.RCVTIMEO, 1000)
            
            tcp_address = f"tcp://{self.tcp_host}:{self.tcp_port}"
            self.subscriber.connect(tcp_address)
            
            print(f"✓ Connected to TCP bridge at {tcp_address}")
            self.connection_status = "Connected"
            return True
            
        except Exception as e:
            print(f"✗ Failed to connect to TCP bridge: {e}")
            self.connection_status = f"Failed: {str(e)[:30]}..."
            return False
    
    def start_data_collection(self):
        """Start the data collection thread"""
        if not self.connect_to_bridge():
            return False
            
        self.running = True
        self.data_thread = threading.Thread(target=self.data_collection_loop)
        self.data_thread.daemon = True
        self.data_thread.start()
        
        print("✓ Data collection started")
        return True
    
    def data_collection_loop(self):
        """Main data collection loop"""
        while self.running:
            try:
                message = self.subscriber.recv(zmq.NOBLOCK)
                self.process_message(message)
                
            except zmq.Again:
                continue
            except Exception as e:
                print(f"Error in data collection: {e}")
                break
    
    def process_message(self, message):
        """Process a received metrics message"""
        try:
            metrics = metrics_pb2.Metrics()
            metrics.ParseFromString(message)
            
            current_time = time.time()
            
            with self.data_lock:
                self.message_count += 1
                
                for ue_metrics in metrics.ue_metrics:
                    rnti = ue_metrics.rnti
                    
                    # Store all metrics with timestamp
                    self.ue_data[rnti]['timestamps'].append(current_time)
                    self.ue_data[rnti]['latency'].append(ue_metrics.latency)
                    self.ue_data[rnti]['backlog'].append(ue_metrics.backlog)
                    self.ue_data[rnti]['throughput'].append(ue_metrics.tx_bytes)
                    self.ue_data[rnti]['cqi'].append(ue_metrics.cqi)
                    self.ue_data[rnti]['snr'].append(ue_metrics.snr)
                    
        except Exception as e:
            print(f"Error processing message: {e}")
    
    def run(self, host='0.0.0.0', port=8050):
        """Run the web dashboard"""
        print(f"Starting EdgeRIC Web Dashboard...")
        print(f"Dashboard will be available at: http://localhost:{port}")
        
        # Start data collection
        if not self.start_data_collection():
            print("Failed to start data collection")
            return
        
        # Run the web server
        self.app.run(host=host, port=port, debug=False)
    
    def stop(self):
        """Stop the dashboard"""
        print("Stopping dashboard...")
        self.running = False
        
        if self.data_thread:
            self.data_thread.join(timeout=1)
        
        if self.subscriber:
            self.subscriber.close()
        
        if self.context:
            self.context.term()
        
        print("Dashboard stopped")
    
    def calculate_running_average(self, data, window_size=30):
        """Calculate running average of the last window_size points"""
        if len(data) < window_size:
            return data
        
        averaged_data = []
        for i in range(len(data)):
            if i < window_size - 1:
                # For early points, use all available data
                averaged_data.append(sum(data[:i+1]) / (i+1))
            else:
                # For points with enough history, use window_size
                averaged_data.append(sum(data[i-window_size+1:i+1]) / window_size)
        
        return averaged_data

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    print("\nReceived interrupt signal, stopping dashboard...")
    if 'dashboard' in globals():
        dashboard.stop()
    sys.exit(0)

if __name__ == "__main__":
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and run web dashboard with 5000 points max
    dashboard = EdgeRICWebDashboard(max_points=5000)
    dashboard.run()
