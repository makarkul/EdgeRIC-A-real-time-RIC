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
        self.last_message_time = time.time()
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
            html.H1("EdgeRIC Metrics Dashboard", 
                   style={'textAlign': 'center', 'marginBottom': 30, 'fontFamily': 'DejaVu Sans Mono, monospace'}),

            # Graphs in a 2x3 grid
            html.Div([
                html.Div([
                    dcc.Graph(id='latency-graph', style={'height': '300px', 'fontFamily': 'DejaVu Sans Mono, monospace'})
                ], className='four columns'),

                html.Div([
                    dcc.Graph(id='backlog-graph', style={'height': '300px', 'fontFamily': 'DejaVu Sans Mono, monospace'})
                ], className='four columns'),

                html.Div([
                    dcc.Graph(id='throughput-graph', style={'height': '300px', 'fontFamily': 'DejaVu Sans Mono, monospace'})
                ], className='four columns'),
            ], className='row'),

            html.Div([
                html.Div([
                    dcc.Graph(id='cqi-graph', style={'height': '300px', 'fontFamily': 'DejaVu Sans Mono, monospace'})
                ], className='four columns'),

                html.Div([
                    dcc.Graph(id='snr-graph', style={'height': '300px', 'fontFamily': 'DejaVu Sans Mono, monospace'})
                ], className='four columns'),

                html.Div([
                    # Control panel centered in the column
                    html.Div([
                        html.Div([
                            html.Label("Plot Samples:", style={'fontFamily': 'DejaVu Sans Mono, monospace', 'marginRight': 10, 'width': '140px', 'display': 'inline-block', 'textAlign': 'left', 'lineHeight': '36px'}),
                            dcc.Dropdown(
                                id='points-dropdown',
                                options=[
                                    {'label': '100', 'value': 100},
                                    {'label': '500', 'value': 500},
                                    {'label': '1000', 'value': 1000},
                                    {'label': '2000', 'value': 2000},
                                    {'label': '5000', 'value': 5000}
                                ],
                                value=5000,
                                placeholder="Select...",
                                style={'fontFamily': 'DejaVu Sans Mono, monospace', 'width': '120px', 'display': 'inline-block'}
                            ),
                        ], style={'marginBottom': 15, 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'flex-start'}),

                        html.Div([
                            html.Label("Avg. Window:", style={'fontFamily': 'DejaVu Sans Mono, monospace', 'marginRight': 10, 'width': '140px', 'display': 'inline-block', 'textAlign': 'left', 'lineHeight': '36px'}),
                            dcc.Dropdown(
                                id='averaging-dropdown',
                                options=[
                                    {'label': '10', 'value': 10},
                                    {'label': '30', 'value': 30},
                                    {'label': '50', 'value': 50},
                                    {'label': '100', 'value': 100}
                                ],
                                value=50,
                                placeholder="Select...",
                                style={'fontFamily': 'DejaVu Sans Mono, monospace', 'width': '120px', 'display': 'inline-block'}
                            ),
                        ], style={'marginBottom': 15, 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'flex-start'}),

                        html.Div([
                            html.Label("RNTI Selection:", style={'fontFamily': 'DejaVu Sans Mono, monospace', 'marginRight': 10, 'width': '140px', 'display': 'inline-block', 'textAlign': 'left', 'lineHeight': '36px'}),
                            dcc.Dropdown(
                                id='rnti-dropdown',
                                options=[],  # Will be populated dynamically
                                value=[],
                                multi=True,
                                placeholder="Select RNTIs...",
                                style={'fontFamily': 'DejaVu Sans Mono, monospace', 'width': '120px', 'display': 'inline-block'},
                                maxHeight=200,
                                optionHeight=35
                            ),
                        ], style={'marginBottom': 15, 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'flex-start'}),
                    ], style={'padding': 20, 'backgroundColor': 'transparent', 'borderRadius': 5, 'height': '300px', 'display': 'flex', 'flexDirection': 'column', 'justifyContent': 'center', 'margin': '0 auto', 'width': '280px'})
                ], className='four columns', style={'display': 'flex', 'justifyContent': 'center'}),
            ], className='row'),

            # Bottom status bar (thinner gutter)
            html.Div([
                html.Div([
                    html.Span(id='status-led', style={'fontSize': '20px', 'marginRight': '10px', 'fontFamily': 'DejaVu Sans Mono, monospace'})
                ], style={'display': 'inline-block', 'float': 'left'}),

                html.Div([
                    html.Span(id='connection-status', style={'fontFamily': 'DejaVu Sans Mono, monospace'})
                ], style={'display': 'inline-block', 'float': 'left', 'marginLeft': '5px'}),

                html.Div([
                    html.Span(id='message-count', style={'fontFamily': 'DejaVu Sans Mono, monospace'})
                ], style={'display': 'inline-block', 'float': 'right'})
            ], style={'position': 'fixed', 'bottom': 0, 'left': 0, 'right': 0, 'height': '28px', 
                     'backgroundColor': '#f0f0f0', 'padding': '4px 12px', 'borderTop': '1px solid #ddd'}),

            # Auto-refresh interval
            dcc.Interval(
                id='interval-component',
                interval=1000,  # Update every second
                n_intervals=0
            ),

            # Store for data
            dcc.Store(id='data-store')
        ], style={'fontFamily': 'DejaVu Sans Mono, monospace', 'paddingBottom': '40px'})
    
    def setup_callbacks(self):
        """Setup Dash callbacks for interactivity"""
        
        @self.app.callback(
            [Output('latency-graph', 'figure'),
             Output('backlog-graph', 'figure'),
             Output('throughput-graph', 'figure'),
             Output('cqi-graph', 'figure'),
             Output('snr-graph', 'figure'),
             Output('status-led', 'children'),
             Output('connection-status', 'children'),
             Output('message-count', 'children'),
             Output('rnti-dropdown', 'options'),
             Output('rnti-dropdown', 'value')],
            [Input('interval-component', 'n_intervals'),
             Input('points-dropdown', 'value'),
             Input('averaging-dropdown', 'value'),
             Input('rnti-dropdown', 'value')]
        )
        def update_graphs(n_intervals, points_to_plot, averaging_window, selected_rntis):
            return self.create_all_graphs(points_to_plot, averaging_window, selected_rntis)
    
    def create_all_graphs(self, points_to_plot=None, averaging_window=50, selected_rntis=None):
        """Create all graphs with current data using sequence-based plotting"""
        if points_to_plot is None:
            points_to_plot = self.max_points
        
        with self.data_lock:
            # Get available RNTIs
            available_rntis = sorted(self.ue_data.keys())
            
            # Create RNTI dropdown options
            rnti_options = [{'label': 'All', 'value': 'all'}]
            rnti_options.extend([{'label': f'UE {rnti}', 'value': rnti} for rnti in available_rntis])
            # Handle RNTI selection
            if selected_rntis is None or not selected_rntis or 'all' in selected_rntis:
                selected_rntis = available_rntis
            
            # Status indicators with connection timeout check
            current_time = time.time()
            connection_timeout = 3.0  # Reduced to 3 seconds for faster detection
            
            # Check if data collection thread is still running and if we've received recent messages
            if (self.connection_status == "Connected" and 
                ((current_time - self.last_message_time) > connection_timeout or 
                 not self.running or 
                 (self.data_thread and not self.data_thread.is_alive()))):
                self.connection_status = "Disconnected"
            
            status_led = "🔴" if self.connection_status != "Connected" else "🟢"
            connection_text = f"Connected" if self.connection_status == "Connected" else "Disconnected"
            message_text = f"{self.message_count} samples"
            
            # Create graphs with sequence-based x-axis
            latency_fig = self.create_metric_graph('latency', 'Latency', points_to_plot, averaging_window, selected_rntis)
            backlog_fig = self.create_metric_graph('backlog', 'Backlog', points_to_plot, averaging_window, selected_rntis)
            throughput_fig = self.create_metric_graph('throughput', 'TX Bytes', points_to_plot, averaging_window, selected_rntis)
            cqi_fig = self.create_metric_graph('cqi', 'CQI', points_to_plot, averaging_window, selected_rntis)
            snr_fig = self.create_metric_graph('snr', 'SNR', points_to_plot, averaging_window, selected_rntis)
            
            # Set default selected RNTIs if none selected
            if not selected_rntis:
                selected_rntis = available_rntis
            
            return (latency_fig, backlog_fig, throughput_fig, cqi_fig, snr_fig,
                   status_led, connection_text, message_text, rnti_options, selected_rntis)
    
    def create_metric_graph(self, metric, y_label, max_points, averaging_window=50, selected_rntis=None):
        """Create a graph for a specific metric with sequence-based x-axis"""
        fig = go.Figure()
        
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9']
        color_idx = 0
        
        if selected_rntis is None:
            selected_rntis = sorted(self.ue_data.keys())
        
        max_data_points = 0
        for rnti in selected_rntis:
            if rnti in self.ue_data:
                ue_data = self.ue_data[rnti]
                values = list(ue_data[metric])
                # Only consider the last max_points for plotting
                values = values[-max_points:]
                max_data_points = max(max_data_points, len(values))
            
        for rnti in selected_rntis:
            if rnti not in self.ue_data:
                continue
            ue_data = self.ue_data[rnti]
            values = list(ue_data[metric])
            # Only consider the last max_points for plotting
            values = values[-max_points:]
            if not values:
                continue
            # Apply running average for all metrics except latency
            if metric != 'latency':
                values = self.calculate_running_average(values, averaging_window)
            # Create x-axis as sample indices (1, 2, 3, ...)
            x_vals = list(range(1, len(values) + 1))
            color = colors[color_idx % len(colors)]
            fig.add_trace(go.Scatter(
                x=x_vals,
                y=values,
                mode='lines+markers',
                showlegend=False,  # Remove legend from each plot
                line=dict(color=color, width=2),
                marker=dict(size=4)
            ))
            color_idx += 1
        # Configure layout for sequence-based plotting
        x_max = max(max_data_points, 10) if max_data_points > 0 else max_points
        
        # Set appropriate y-axis labels with units
        y_axis_labels = {
            'Latency': 'Latency (μs)',
            'Backlog': 'Backlog (bytes)', 
            'TX Bytes': 'TX Bytes',
            'CQI': 'CQI',
            'SNR': 'SNR (dB)'
        }
        y_axis_title = y_axis_labels.get(y_label, y_label)
        
        fig.update_layout(
            title=f'{y_label}',
            xaxis_title='',  # Remove x-axis title
            yaxis_title=y_axis_title,
            xaxis=dict(
                range=[1, x_max],
                type='linear'
            ),
            showlegend=False,
            margin=dict(l=50, r=50, t=50, b=50),
            height=300,
            font=dict(family="DejaVu Sans Mono, monospace")
        )
        return fig
    
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
        consecutive_failures = 0
        max_failures = 3  # Reduced for faster detection
        
        while self.running:
            try:
                message = self.subscriber.recv(zmq.NOBLOCK)
                self.process_message(message)
                consecutive_failures = 0  # Reset failure count on successful receive
                
            except zmq.Again:
                continue
            except Exception as e:
                consecutive_failures += 1
                print(f"Error in data collection: {e}")
                
                if consecutive_failures >= max_failures:
                    print(f"Too many consecutive failures ({consecutive_failures}), marking as disconnected")
                    with self.data_lock:
                        self.connection_status = "Disconnected"
                    break  # Exit the loop on persistent failures
                    
                time.sleep(0.1)  # Brief pause before retrying
        
        # Ensure disconnected status when loop exits
        with self.data_lock:
            self.connection_status = "Disconnected"
        print("Data collection loop ended")
    
    def process_message(self, message):
        """Process a received metrics message"""
        try:
            metrics = metrics_pb2.Metrics()
            metrics.ParseFromString(message)
            
            current_time = time.time()
            
            with self.data_lock:
                self.message_count += 1
                self.last_message_time = current_time  # Update last message time
                
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
        
        # Set running to False first
        self.running = False
        
        # Update connection status immediately
        with self.data_lock:
            self.connection_status = "Disconnected"
        
        # Wait for data thread to finish
        if self.data_thread:
            self.data_thread.join(timeout=2)
        
        # Close ZMQ resources
        if self.subscriber:
            self.subscriber.close()
        
        if self.context:
            self.context.term()
        
        print("Dashboard stopped")
    
    def calculate_running_average(self, data, window_size=50):
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
